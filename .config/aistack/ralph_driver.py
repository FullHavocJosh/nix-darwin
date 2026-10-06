#!/usr/bin/env python3
"""Detached driver for one aistack run: works a plan task by task through Ralph TUI.

Why a driver instead of one `ralph-tui run` over the whole PRD:
  * Ralph decides a task is done when the agent prints its completion marker, and that has false positives
    (an agent that explains it could not finish can quote the marker). Here a task only counts as done
    when the plan's own verify commands pass.
  * Ralph runs headless agents, which cannot ask the user anything. Agents write a question file; the driver
    pauses, surfaces it, and resumes with the answer.
  * Escalation (worker -> fallback agent), a read-only review pass, and "wait for the user" all live here.

Everything is file based under <state>/runs/<run_id>/ so the MCP bridge (and a restarted chat session) can read
state, and write control messages, without talking to this process. <state> is ~/.aistack/<project key> (never the
repository): plan files, runs, questions, reviews, progress, Ralph's own .ralph-tui and its iteration logs all live
there. Only the agents' code changes land in the work dir (the git worktree, or the project itself).
"""
import json, os, re, shlex, signal, subprocess, sys, time

TAIL_CHARS = 2500
POLL = 2.0


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def write_json(path, obj):
    tmp = f"{path}.tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, path)


def tail(text, n=TAIL_CHARS):
    text = text or ""
    return text if len(text) <= n else "...\n" + text[-n:]


class Run:
    def __init__(self, state_dir, run_id):
        self.state_dir = os.path.realpath(state_dir)
        self.id = run_id
        self.dir = os.path.join(self.state_dir, "runs", run_id)
        self.cfg = read_json(os.path.join(self.dir, "config.json"), {})
        # where the agents change code and where verify commands run: the git worktree, or the project itself
        self.project = os.path.realpath(self.cfg["work_dir"])
        self.ralph = self.cfg.get("ralph_bin") or os.path.expanduser("~/.bun/bin/ralph-tui")
        self.prd_path = self.cfg.get("prd") or os.path.join(self.state_dir, "plan", "prd.json")
        self.verify_path = self.cfg.get("verify") or os.path.join(self.state_dir, "plan", "verify.json")
        self.q_dir = os.path.join(self.state_dir, "questions")
        self.rev_dir = os.path.join(self.state_dir, "reviews")
        self.progress_path = os.path.join(self.state_dir, "progress.md")
        # ralph-tui keeps session state, lock, config and reports in <cwd>/.ralph-tui, so it runs from a directory
        # under the state dir; the agent wrappers cd to AISTACK_WORKDIR before starting the real agent
        self.ralph_cwd = os.path.join(self.state_dir, "ralph")
        for d in (self.dir, os.path.join(self.dir, "tasks"), os.path.join(self.dir, "logs"), self.q_dir, self.rev_dir,
                  self.ralph_cwd, os.path.join(self.state_dir, "iterations")):
            os.makedirs(d, exist_ok=True)
        self.work_template = self.render_template(self.cfg["work_template"])
        self.review_template = self.render_template(self.cfg["review_template"])
        self.events_path = os.path.join(self.dir, "events.jsonl")
        self.control_path = os.path.join(self.dir, "control.jsonl")
        self.state_path = os.path.join(self.dir, "state.json")
        self.seq = 0
        self.control_off = 0
        self.child = None
        self.cancelled = False
        self.billed_agents = set(self.cfg.get("billed_agents") or [])
        self.billed = {"work": 0, "review": 0}   # calls to billed agents (Claude): the cost the user cares about
        self.reports = {}        # task id -> the review report that judged it
        self.batch_n = 0
        self.tasks = {}          # id -> dict(title, status, attempts, ...)
        self.skipped = set()
        self.extra_notes = {}    # id -> list[str] guidance accumulated across attempts / user answers
        self.state = {"state": "starting", "phase": "work", "current_task": None, "waiting_for": None}
        self.env = dict(os.environ)
        self.env["PATH"] = os.path.expanduser("~/.bun/bin") + os.pathsep + self.env.get("PATH", "")
        self.env.update(AISTACK_WORKDIR=self.project, AISTACK_STATE_DIR=self.state_dir, AISTACK_REVIEWS_DIR=self.rev_dir)

    def render_template(self, src):
        """Per-run copy of a prompt template with the state-dir paths filled in (agents write questions, reports and
        progress notes there, outside the repository)."""
        text = open(src).read()
        for token, value in {"@@QUESTIONS_DIR@@": self.q_dir, "@@PROGRESS_FILE@@": self.progress_path,
                             "@@REVIEWS_DIR@@": self.rev_dir, "@@PRD_FILE@@": self.prd_path,
                             "@@VERIFY_FILE@@": self.verify_path}.items():
            text = text.replace(token, value)
        out = os.path.join(self.dir, os.path.basename(src))
        with open(out, "w") as f:
            f.write(text)
        return out

    # ---- state / events -------------------------------------------------
    def event(self, kind, task=None, message="", **extra):
        self.seq += 1
        rec = {"seq": self.seq, "ts": now(), "type": kind, "task": task, "message": message}
        rec.update(extra)
        with open(self.events_path, "a") as f:
            f.write(json.dumps(rec) + "\n")
        self.save()

    def save(self, **kw):
        self.state.update(kw)
        out = dict(self.state)
        out.update({"run_id": self.id, "pid": os.getpid(), "updated": now(), "last_seq": self.seq,
                    "tasks": self.tasks})
        write_json(self.state_path, out)

    # ---- plan -----------------------------------------------------------
    def load_plan(self):
        prd = read_json(self.prd_path)
        verify = read_json(self.verify_path, {})
        self.prd, self.verify = prd, verify
        for i, s in enumerate(prd["userStories"]):
            self.tasks.setdefault(s["id"], {"title": s.get("title", ""), "status": "verified" if s.get("passes") else "pending",
                                            "attempts": 0, "agent": None, "review": None, "order": i})

    def set_passes(self, tid, value):
        prd = read_json(self.prd_path)
        for s in prd["userStories"]:
            if s["id"] == tid:
                s["passes"] = value
        write_json(self.prd_path, prd)

    def story(self, tid):
        for s in read_json(self.prd_path)["userStories"]:
            if s["id"] == tid:
                return s

    def next_task(self):
        prd = read_json(self.prd_path)
        done = {s["id"] for s in prd["userStories"] if s.get("passes")}
        cands = []
        for i, s in enumerate(prd["userStories"]):
            if s.get("passes") or s["id"] in self.skipped:
                continue
            if all(d in done for d in s.get("dependsOn", [])):
                cands.append((s.get("priority", 99), i, s["id"]))
        return min(cands)[2] if cands else None

    # ---- control channel ------------------------------------------------
    def poll_control(self):
        try:
            with open(self.control_path) as f:
                f.seek(self.control_off)
                data = f.read()
                self.control_off = f.tell()
        except OSError:
            return []
        out = []
        for line in data.splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
        return out

    def wait_for_user(self, reason, options, task=None, **extra):
        """Block until a control message arrives. Returns the message dict."""
        self.save(state="waiting_user", waiting_for={"reason": reason, "options": options, "task": task, **extra})
        self.event("waiting_user", task, reason, options=options, **extra)
        while True:
            if self.cancelled:
                return {"action": "abort", "text": "cancelled"}
            for msg in self.poll_control():
                act = msg.get("action")
                if act == "abort":
                    return msg
                if act in options:
                    self.save(state="running", waiting_for=None)
                    return msg
                self.event("control_ignored", task, f"action {act!r} is not valid now; valid: {options}")
            time.sleep(POLL)

    # ---- running Ralph --------------------------------------------------
    def run_ralph(self, agent, prd_file, label, template):
        log = os.path.join(self.dir, "logs", f"{label}.log")
        argv = [self.ralph, "run", "--headless", "--no-setup", "--agent", agent, "--prd", prd_file,
                "--iterations", "1", "--prompt", template,
                "--progress-file", self.progress_path, "--output-dir", os.path.join(self.state_dir, "iterations")]
        timeout = int(self.cfg.get("attempt_timeout_s", 1500))
        with open(log, "w") as lf:
            self.child = subprocess.Popen(argv, cwd=self.ralph_cwd, env=self.env, stdin=subprocess.DEVNULL,
                                          stdout=lf, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = self.child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.kill_child()
                code = -9
            self.child = None
        try:
            text = open(log, errors="replace").read()
        except OSError:
            text = ""
        lines = [l for l in text.splitlines() if "[agent]" not in l]
        return code, "\n".join(lines[-25:]), log

    def kill_child(self):
        if self.child and self.child.poll() is None:
            try:
                os.killpg(self.child.pid, signal.SIGTERM)
                self.child.wait(timeout=10)
            except Exception:
                try:
                    os.killpg(self.child.pid, signal.SIGKILL)
                except Exception:
                    pass

    # ---- verification -----------------------------------------------------
    def verify_task(self, tid):
        cmds = self.verify.get(tid)
        if not cmds:
            return False, "no verify command for this task in verify.json"
        if isinstance(cmds, str):
            cmds = [cmds]
        out = []
        for c in cmds:
            if re.search(r"[;&|<>`]|\$\(", c):
                return False, f"verify command contains shell syntax, not allowed: {c}"
            try:
                p = subprocess.run(shlex.split(c), cwd=self.project, env=self.env, capture_output=True, text=True,
                                   timeout=int(self.cfg.get("verify_timeout_s", 300)))
            except subprocess.TimeoutExpired:
                return False, f"$ {c}\nTIMED OUT"
            except OSError as e:
                return False, f"$ {c}\n{e}"
            out.append(f"$ {c}\n{tail(p.stdout + p.stderr, 1200)}")
            if p.returncode != 0:
                return False, "\n".join(out) + f"\n(exit {p.returncode})"
        return True, "\n".join(out)

    # ---- one task ---------------------------------------------------------
    def compose_notes(self, tid, story):
        parts = [story.get("notes") or ""]
        v = self.verify.get(tid)
        v = [v] if isinstance(v, str) else (v or [])
        if v:
            parts.append("Verification (run by the harness after you finish; your work only counts when these pass):\n"
                         + "\n".join(f"  {c}" for c in v))
        if self.extra_notes.get(tid):
            parts.append("Guidance and results of earlier attempts:\n" + "\n---\n".join(self.extra_notes[tid]))
        return "\n\n".join(p for p in parts if p.strip())

    def single_prd(self, tid, story, notes, prefix=""):
        path = os.path.join(self.dir, "tasks", f"{prefix}{tid}.prd.json")
        one = {"name": self.prd.get("name", "plan"), "description": self.prd.get("description", ""),
               "userStories": [{"id": f"{prefix}{tid}", "title": story.get("title", ""),
                                "description": story.get("description", ""),
                                "acceptanceCriteria": story.get("acceptanceCriteria", []),
                                "priority": 1, "passes": False, "notes": notes}]}
        write_json(path, one)
        return path

    def question_file(self, tid):
        return os.path.join(self.q_dir, f"{tid}.md")

    def work_task(self, tid):
        story = self.story(tid)
        t = self.tasks[tid]
        plan = ([self.cfg["worker_agent"]] * int(self.cfg.get("worker_attempts", 2)) +
                [self.cfg["fallback_agent"]] * int(self.cfg.get("fallback_attempts", 1)))
        i = 0
        while i < len(plan):
            agent = plan[i]
            t.update(status="working", agent=agent)
            self.save(current_task=tid, phase="work")
            t["attempts"] += 1
            n = t["attempts"]
            billed = agent in self.billed_agents
            self.billed["work"] += 1 if billed else 0
            self.event("task_started", tid, f"{tid} attempt {n} with {agent}{' [billed]' if billed else ''}: {t['title']}",
                       agent=agent, attempt=n, billed=billed)
            qf = self.question_file(tid)
            if os.path.exists(qf):
                os.replace(qf, qf + ".stale")
            prd_file = self.single_prd(tid, story, self.compose_notes(tid, story))
            code, summary, log = self.run_ralph(agent, prd_file, f"{tid}-{n}", self.work_template)
            if self.cancelled:
                return "cancelled"
            self.event("agent_finished", tid, f"{agent} exited {code}", log=log, tail=tail(summary, 600))
            if os.path.exists(qf) and os.path.getsize(qf) > 0:
                question = open(qf).read().strip()
                os.replace(qf, os.path.join(self.q_dir, f"{tid}-{n}.asked.md"))
                self.event("question", tid, question, agent=agent)
                msg = self.wait_for_user(f"{agent} needs a decision on {tid}", ["answer"], tid, question=question)
                if msg.get("action") == "abort":
                    return "cancelled"
                self.extra_notes.setdefault(tid, []).append(f"You asked: {question}\nUser answer: {msg.get('text','')}")
                self.event("answer_recorded", tid, "answer passed to the agent; re-running the task")
                t["attempts"] -= 1   # a question is not a failed attempt
                continue
            ok, out = self.verify_task(tid)
            if ok:
                self.set_passes(tid, True)
                t.update(status="verified")
                self.event("verify_passed", tid, f"{tid} verified (attempt {n}, {agent})", output=tail(out, 800))
                return "ok"
            self.event("verify_failed", tid, f"{tid} failed verification after {agent} attempt {n}", output=tail(out, 1500))
            self.extra_notes.setdefault(tid, []).append(f"Attempt {n} ({agent}) failed verification:\n{tail(out, 1500)}")
            i += 1
            if i < len(plan) and plan[i] != agent:
                self.event("escalating", tid, f"escalating {tid} from {agent} to {plan[i]}"
                           + (" (billed)" if plan[i] in self.billed_agents else ""), billed=plan[i] in self.billed_agents)
        t.update(status="blocked")
        return "blocked"

    # ---- review -----------------------------------------------------------
    def review_task(self, tid):
        story = self.story(tid)
        rf = os.path.join(self.rev_dir, f"{tid}.md")
        if os.path.exists(rf):
            os.replace(rf, rf + ".prev")
        report = rf
        brief = (f"Review the work done for task {tid} ({story.get('title','')}) in this repository. The task spec is in "
                 f"{self.prd_path} and its checks are in {self.verify_path}. Read the files the task created or "
                 f"changed. Do NOT modify source or test files. Check: (1) security: injection, unsafe file/shell/network "
                 f"use, secrets, unvalidated input, dangerous defaults; (2) accuracy: does the code do what the description "
                 f"and acceptance criteria say, including edge cases; (3) completeness: every acceptance criterion met, "
                 f"tests present and meaningful, nothing half-done. Run the verify commands if safe. Write the report to "
                 f"{report}. Its FIRST line must be exactly 'Verdict: PASS' or 'Verdict: FAIL', then findings "
                 f"with file and line references, most serious first.")
        rs = {"id": f"R-{tid}", "title": f"Review {tid}: {story.get('title','')}", "description": brief,
              "acceptanceCriteria": [f"{report} exists and its first line is 'Verdict: PASS' or 'Verdict: FAIL'"],
              "priority": 1, "passes": False}
        path = os.path.join(self.dir, "tasks", f"review-{tid}.prd.json")
        write_json(path, {"name": "review", "description": "read-only review", "userStories": [rs]})
        for attempt in (1, 2):
            if self.cfg["reviewer_agent"] in self.billed_agents:
                self.billed["review"] += 1
            self.event("review_started", tid, f"reviewing {tid} with {self.cfg['reviewer_agent']}", billed=self.cfg["reviewer_agent"] in self.billed_agents)
            code, summary, log = self.run_ralph(self.cfg["reviewer_agent"], path, f"review-{tid}-{attempt}",
                                                self.review_template)
            if self.cancelled:
                return None
            if os.path.exists(rf):
                text = open(rf).read()
                first = text.splitlines()[0].strip() if text.strip() else ""
                m = re.match(r"(?i)^\**\s*verdict:\s*(pass|fail)", first)
                if m:
                    verdict = m.group(1).upper()
                    self.tasks[tid]["review"] = verdict
                    self.reports[tid] = rf
                    body = "\n".join(text.splitlines()[1:14])
                    self.event("review_result", tid, f"{tid} review: {verdict}", verdict=verdict, report=rf, excerpt=body)
                    return verdict
            self.event("review_error", tid, f"review of {tid} produced no valid report (attempt {attempt})", tail=tail(summary, 600))
        self.tasks[tid]["review"] = "MISSING"
        return "MISSING"

    def review_batch(self, tids):
        """ONE review call for all the given tasks (one billed Claude call instead of one per task). The report starts
        with an overall verdict, then one 'Task <id>: PASS|FAIL' line per task. Returns {task id: verdict}, or None when
        the run was cancelled."""
        self.batch_n += 1
        rf = os.path.join(self.rev_dir, f"batch-{self.batch_n}.md")
        listing = "\n".join(
            f"- {t}: {self.story(t).get('title', '')} | done when: " + "; ".join(self.story(t).get("acceptanceCriteria", []))
            for t in tids)
        brief = (f"Review the work done for tasks {', '.join(tids)} in this repository, in ONE pass. The task specs are in "
                 f"{self.prd_path} and their checks in {self.verify_path}. Tasks:\n{listing}\n"
                 f"Use `git status` and `git diff` to see what changed instead of reading every file, and read only what you "
                 f"need. Do NOT modify source or test files. Judge (1) security: injection, unsafe file/shell/network use, "
                 f"secrets, unvalidated input, dangerous defaults; (2) accuracy: does the code do what each description and its "
                 f"acceptance criteria say, edge cases included; (3) completeness: every criterion met, tests present and "
                 f"meaningful, nothing half-done. Write the report to {rf}. Its FIRST line must be exactly 'Verdict: PASS' or "
                 f"'Verdict: FAIL' (FAIL if any task fails). Then one line per task, exactly 'Task <id>: PASS' or "
                 f"'Task <id>: FAIL - <reason>'. Then findings with file and line references, most serious first. Be concise.")
        rs = {"id": "R-batch", "title": f"Review {len(tids)} task(s)", "description": brief,
              "acceptanceCriteria": [f"{rf} exists and its first line is 'Verdict: PASS' or 'Verdict: FAIL'"],
              "priority": 1, "passes": False}
        path = os.path.join(self.dir, "tasks", f"review-batch-{self.batch_n}.prd.json")
        write_json(path, {"name": "review", "description": "read-only review of the whole run", "userStories": [rs]})
        agent = self.cfg["reviewer_agent"]
        for attempt in (1, 2):
            if agent in self.billed_agents:
                self.billed["review"] += 1
            self.event("review_started", None, f"reviewing {', '.join(tids)} in one pass with {agent}"
                       + (" [billed]" if agent in self.billed_agents else ""), billed=agent in self.billed_agents)
            code, summary, log = self.run_ralph(agent, path, f"review-batch-{self.batch_n}-{attempt}", self.review_template)
            if self.cancelled:
                return None
            if os.path.exists(rf):
                text = open(rf).read()
                first = text.splitlines()[0].strip() if text.strip() else ""
                m = re.match(r"(?i)^\**\s*verdict:\s*(pass|fail)", first)
                if m:
                    overall = m.group(1).upper()
                    per = {t.group(1): t.group(2).upper() for t in
                           re.finditer(r"(?im)^\**\s*task\s+([A-Za-z0-9_-]+)\**\s*:\s*\**\s*(pass|fail)", text)}
                    verdicts = {t: per.get(t, overall) for t in tids}
                    if overall == "FAIL" and "FAIL" not in verdicts.values():
                        verdicts = {t: "FAIL" for t in tids}      # a FAIL verdict never turns into all-PASS
                    for t, v in verdicts.items():
                        self.tasks[t]["review"] = v
                        self.reports[t] = rf
                        self.event("review_result", t, f"{t} review: {v}", verdict=v, report=rf,
                                   excerpt="\n".join(text.splitlines()[1:14]))
                    return verdicts
            self.event("review_error", None, f"review of {', '.join(tids)} produced no valid report (attempt {attempt})", tail=tail(summary, 600))
        for t in tids:
            self.tasks[t]["review"] = "MISSING"
        return {t: "MISSING" for t in tids}

    def report_path(self, tid):
        return self.reports.get(tid) or os.path.join(self.rev_dir, f"{tid}.md")

    # ---- main loop --------------------------------------------------------
    def main(self):
        self.load_plan()
        self.save(state="running")
        self.event("run_started", None, f"{len(self.tasks)} tasks; worker={self.cfg['worker_agent']} "
                   f"fallback={self.cfg['fallback_agent']} reviewer={self.cfg['reviewer_agent']}")
        while True:
            # ---- work phase
            while True:
                tid = self.next_task()
                if not tid:
                    break
                res = self.work_task(tid)
                if res == "cancelled":
                    return self.finish("cancelled")
                if res == "blocked":
                    opts = ["retry", "skip", "abort"]
                    msg = self.wait_for_user(f"{tid} is blocked: it failed verification with every agent. Retry with guidance, skip it, or abort?",
                                             opts, tid, last_output=tail(self.extra_notes.get(tid, [""])[-1], 800))
                    act = msg.get("action")
                    if act == "abort":
                        return self.finish("cancelled")
                    if act == "skip":
                        self.skipped.add(tid)
                        self.tasks[tid]["status"] = "skipped"
                        self.event("task_skipped", tid, f"{tid} skipped by the user")
                    else:
                        self.tasks[tid]["attempts"] = 0
                        self.extra_notes.setdefault(tid, []).append(f"User guidance for the retry: {msg.get('text','')}")
                        self.event("task_retry", tid, f"{tid} retried with user guidance")
            left = [t for t, v in self.tasks.items() if v["status"] not in ("verified", "skipped")]
            if left:
                msg = self.wait_for_user(f"tasks {left} cannot start (a dependency was skipped or failed). Abort the run?",
                                         ["abort"], None)
                return self.finish("cancelled")
            # ---- review phase
            self.save(phase="review", current_task=None)
            failed = []
            pending = [t for t, v in sorted(self.tasks.items(), key=lambda kv: kv[1]["order"])
                       if v["status"] == "verified" and v["review"] not in ("PASS", "ACCEPTED", "SKIPPED")]
            mode = self.cfg.get("review_mode", "batch")      # batch: one call per review round; each: one per task; off
            if mode == "off":
                for t in pending:
                    self.tasks[t]["review"] = "SKIPPED"
                self.event("review_skipped", None, "review is switched off (AISTACK_REVIEW_MODE=off)")
            elif mode == "each":
                for tid in pending:
                    verdict = self.review_task(tid)
                    if verdict is None:
                        return self.finish("cancelled")
                    if verdict != "PASS":
                        failed.append(tid)
            elif pending:
                verdicts = self.review_batch(pending)
                if verdicts is None:
                    return self.finish("cancelled")
                failed = [t for t in pending if verdicts.get(t) != "PASS"]
            if not failed:
                break
            self.save(phase="review_decision")
            msg = self.wait_for_user("review did not pass for " + ", ".join(failed) +
                                     ". Per task: rework (re-run it with the findings), or accept as is.",
                                     ["rework", "accept"], None, tasks=failed,
                                     reports={t: self.report_path(t) for t in failed})
            if msg.get("action") == "abort":
                return self.finish("cancelled")
            targets = msg.get("tasks") or failed
            if msg.get("action") == "accept":
                for t in targets:
                    self.tasks[t]["review"] = "ACCEPTED"
                if all(self.tasks[t]["review"] in ("PASS", "ACCEPTED") for t in self.tasks if self.tasks[t]["status"] == "verified"):
                    break
                continue
            for t in targets:
                rep = open(self.report_path(t)).read() if os.path.exists(self.report_path(t)) else ""
                self.extra_notes.setdefault(t, []).append(f"The reviewer found problems. Fix them.\n{tail(rep, 2000)}\nUser note: {msg.get('text','')}")
                self.set_passes(t, False)
                self.tasks[t].update(status="pending", attempts=0, review=None)
            self.event("rework_started", None, "re-running " + ", ".join(targets))
        return self.finish("done")

    def finish(self, outcome):
        summary = {t: {"status": v["status"], "review": v["review"], "attempts": v["attempts"]} for t, v in self.tasks.items()}
        if outcome == "done":
            self.save(state="done", phase="finished", current_task=None, waiting_for=None)
            self.event("run_complete", None, "all tasks verified and reviewed; billed calls: "
                       f"{self.billed['work']} work + {self.billed['review']} review", summary=summary, billed_calls=dict(self.billed))
        else:
            self.save(state="cancelled", current_task=None, waiting_for=None)
            self.event("run_cancelled", None, f"run stopped; billed calls so far: {self.billed['work']} work + {self.billed['review']} review",
                       summary=summary, billed_calls=dict(self.billed))
        return 0


def main():
    state_dir, run_id = sys.argv[1], sys.argv[2]
    run = Run(state_dir, run_id)

    def on_term(signum, frame):
        run.cancelled = True
        run.kill_child()
    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    try:
        return run.main()
    except Exception as e:  # the chat agent must learn about it instead of waiting forever
        import traceback
        run.save(state="failed")
        run.event("run_failed", None, f"{type(e).__name__}: {e}", trace=traceback.format_exc()[-1500:])
        return 1


if __name__ == "__main__":
    sys.exit(main())
