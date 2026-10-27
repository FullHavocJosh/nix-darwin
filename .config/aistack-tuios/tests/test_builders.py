"""Tests for aidev's builder kinds and workspace maps (aidev_tuios.py): kind aliases, pane names, reset commands and
the workspace of a builder pane in an old saved run. Needs no tuios daemon, no model and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_builders.py
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    for var in ("AIDEV_TUIOS_SESSION", "AIDEV_TUIOS_RUN", "AIDEV_TUIOS_PROJECT", "AIDEV_TUIOS_BUILDER"):
        os.environ.pop(var, None)
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

    print("builder kinds")
    check("canonical kinds map to themselves",
          [a.norm_kind(k) for k in ("local", "free", "billed")] == ["local", "free", "billed"])
    check("aliases map to kinds", [a.norm_kind(k) for k in ("30b", "pickle", "claude")] == ["local", "free", "billed"])
    check("upper case and spaces are accepted", a.norm_kind(" Billed ") == "billed" and a.norm_kind("30B") == "local")
    check("an unknown word is None", a.norm_kind("x") is None)
    check("builder pane names", a.BUILDERS == {"local": "build-local", "free": "build-free", "billed": "build-billed"},
          a.BUILDERS)
    check("reset commands cover every kind", set(a.RESET_CMD) == set(a.BUILDERS), a.RESET_CMD)

    print("workspaces")
    names = list(a.BUILDERS.values())
    check("WS_OWN has the builder panes on 2", all(a.WS_OWN.get(n) == 2 for n in names), a.WS_OWN)
    check("WS_OWN has no key build", "build" not in a.WS_OWN)
    check("WS_NAMES names the builder panes", all(a.WS_NAMES.get(n) == "ai" for n in names), a.WS_NAMES)
    p = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-"))
    run = a.Run(p, "20260101-000001")
    run.data["ws"] = {a.PLAN: 3, a.RESEARCH: 4, "build": 4}
    check("assign_workspaces accepts a saved map", a.assign_workspaces(run, "s", own=False) is None)
    check("a saved map lacking build-local gets the research workspace",
          all(run.data["ws"].get(n) == 4 for n in names) and a.WS["build-local"] == 4, run.data["ws"])

    print("builder command")
    calls, closed, asked = [], [], []
    real = (a.tuios, a.tuios_json, a.window_named, a.agent_state, a.start_builder, a.ask_human)
    a.tuios = lambda *args, **kw: (closed.append(args[1]) if args[0] == "close-window" else None) or (0, "", "")
    a.tuios_json = lambda *args, **kw: None
    a.window_named = lambda s, n: None
    a.agent_state = lambda s, n: "idle"
    a.start_builder = lambda r, kind, name, ws, cwd: (calls.append((kind, name)) or (True, "ok"))
    a.ask_human = lambda s, q, o: (asked.append(q) or "no")
    try:
        run.data["work_dir"] = p
        check("builder x returns 2", a.cmd_builder(run, ["x"]) == 2 and not calls)
        check("builder 30b opens build-local", a.cmd_builder(run, ["30b"]) == 0 and calls == [("local", "build-local")],
              calls)
        del calls[:]
        check("builder CLAUDE asks the human, a no returns 1",
              a.cmd_builder(run, ["CLAUDE"]) == 1 and len(asked) == 1 and not calls, (asked, calls))
        check("no_builder_why(local) names the model file", a.CODER_FILE in a.no_builder_why("local"))
        a.window_named = lambda s, n: {"custom_name": n} if n in ("build-local", "build") else None
        a.finish_work(run)
        check("finish_work closes the new and the legacy pane", sorted(closed) == ["build", "build-local"], closed)
    finally:
        a.tuios, a.tuios_json, a.window_named, a.agent_state, a.start_builder, a.ask_human = real

    print("task size")
    def story(desc):
        return {"userStories": [{"id": "T1", "title": "t", "description": desc, "acceptanceCriteria": ["ok"]}]}
    check("500 characters naming 2 files is fine", a.size_problems(story("a.py b.md " + "x" * 480)) == [])
    big = a.size_problems(story("x" * 3000))
    check("3000 characters is flagged", len(big) == 1 and "characters" in big[0], big)
    many = a.size_problems(story("edit a.py b.py c.py d.py"))
    check("4 files is flagged", len(many) == 1 and "files" in many[0], many)
    os.environ["AIDEV_TUIOS_TASK_MAX_CHARS"] = "100"
    try:
        small = load("aidev_small", os.path.join(ROOT, "aidev_tuios.py"))
    finally:
        del os.environ["AIDEV_TUIOS_TASK_MAX_CHARS"]
    check("AIDEV_TUIOS_TASK_MAX_CHARS is read at load time",
          small.TASK_MAX_CHARS == 100 and any("characters" in x for x in small.size_problems(story("x" * 150))))
    check("task_prompt tells the builder to read by region",
          "Never read a whole large file" in a.task_prompt({"name": "p"}, story("d")["userStories"][0], "true", []))

    print("free builder agent")
    with open(os.path.join(ROOT, "aidev_tuios.py")) as f:
        src = f.read()
    check("the free body runs opencode mini with --agent build", "opencode mini --agent build --model" in src)

    print("no old kind literals")
    bad = [f"{i}: {ln.strip()}" for i, ln in enumerate(src.splitlines(), 1)
           if any(f'"{w}"' in ln for w in ("30b", "pickle", "claude"))
           and not (ln.startswith("KIND_ALIASES") or '["claude"' in ln or '"claude", "--settings"' in ln
                    or "CODER_FILE" in ln or 'prompt_text("claude"' in ln or 'os.path.join(d, "claude")' in ln
                    or '("tuios", "claude", "pi"' in ln)]
    check("30b, pickle and claude appear as kinds only in KIND_ALIASES", not bad, "; ".join(bad))

    print("builder permissions")
    fixed = a.builder_permissions(None)
    check("no verify gives acceptEdits and the fixed deny rules",
          fixed["defaultMode"] == "acceptEdits" and "Bash(git push *)" in fixed["deny"] and "Bash(gh *)" in fixed["deny"])
    perms = a.builder_permissions({"T1": ["python3 t.py"], "T2": "make check"})
    check("verify commands are added exactly",
          sorted(set(perms["allow"]) - set(fixed["allow"])) == ["Bash(make check)", "Bash(python3 t.py)"])
    check("builder_permissions is deterministic",
          perms == a.builder_permissions({"T1": ["python3 t.py"], "T2": "make check"}))
    tmp = tempfile.mkdtemp(prefix="aidev-test-settings-")
    src_settings = os.path.join(tmp, "settings.json")
    a.wj(src_settings, {"permissions": {"allow": ["Bash(x)"]}})
    cfg = {"claude_settings": src_settings}
    out = a.rj(a.write_working_settings(cfg, os.path.join(tmp, "o1.json"), ["Bash(y)"], ["Bash(z)"], "acceptEdits"), {})
    check("write_working_settings writes deny and mode and keeps allow",
          out["permissions"]["deny"] == ["Bash(z)"] and out["permissions"]["defaultMode"] == "acceptEdits"
          and out["permissions"]["allow"] == ["Bash(x)", "Bash(y)"])
    out = a.rj(a.write_working_settings(cfg, os.path.join(tmp, "o2.json"), ["Bash(y)"]), {})
    check("allow only writes no defaultMode and no deny",
          "defaultMode" not in out["permissions"] and "deny" not in out["permissions"])
    print("billed builder settings")
    bdir = os.path.join(tmp, "bb")
    os.makedirs(bdir)
    bcfg = {"claude_settings": src_settings, "claude_mcp": os.path.join(tmp, "mcp.json"),
            "claude_backbone": os.path.join(bdir, "backbone.json")}
    brun = a.Run(p, "20260101-000002")
    real_ld, real_gg = a.load_ralph, a.write_git_guard
    a.load_ralph = lambda project=None: type("R", (), {"load_plan": lambda self, proj: (None, {"T1": ["python3 t.py"]}, "h")})()
    a.write_git_guard = lambda r: a.write_text(os.path.join(r.dir, "bin", "guard", "git"), "")
    try:
        a.build_body(brun, bcfg, "billed")
    finally:
        a.load_ralph, a.write_git_guard = real_ld, real_gg
    bperms = a.rj(os.path.join(bdir, "builder.json"), {}).get("permissions", {})
    check("billed builder.json carries the generated policy",
          bperms.get("defaultMode") == "acceptEdits" and "Bash(python3 t.py)" in bperms.get("allow", [])
          and "Bash(git push *)" in bperms.get("deny", []), bperms)
    check("billed builder.json denies Edit on the plan directory of run.state",
          f"Edit(//{brun.state.lstrip('/')}/plan/**)" in bperms.get("deny", []), bperms)
    sp = a.builder_permissions(None, "/s/st")
    check("state_dir denies Edit and MultiEdit on plan, state.json and events.jsonl",
          "Edit(//s/st/plan/**)" in sp["deny"] and "MultiEdit(//s/st/runs/*/state.json)" in sp["deny"]
          and "Edit(//s/st/runs/*/events.jsonl)" in sp["deny"], sp["deny"])
    check("no state_dir adds no Edit rule", not [r for r in a.builder_permissions(None)["deny"] if r.startswith("Edit(")])

    print("approvals")
    ev = os.path.join(brun.dir, "events.jsonl")
    peek = {"found": False, "reason": "idle"}
    sent, resp = [], [(0, "ok", "")]
    real = (a.tuios, a.tuios_json, a.window_named)
    a.window_named = lambda s, n: {"custom_name": n}
    a.tuios_json = lambda *args, **kw: peek
    a.tuios = lambda *args, **kw: (sent.append(args) or resp[0])
    try:
        brun.data.pop("builder", None)
        check("approvals without a builder returns 1", a.cmd_approvals(brun, []) == 1)
        brun.data["builder"] = "build-billed"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = a.cmd_approvals(brun, [])
        check("approvals found false prints the reason", rc == 0 and "idle" in out.getvalue(), out.getvalue())
        peek = {"found": True, "prompt_id": "p7", "message": "Run rm?", "lines": ["l1"], "options": ["1"],
                "actions": ["approve"]}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = a.cmd_approvals(brun, [])
        text = out.getvalue()
        check("approvals prints id, message and both markers",
              rc == 0 and "p7" in text and "Run rm?" in text and "--- prompt of build-billed" in text
              and "--- end ---" in text, text)
        with contextlib.redirect_stdout(io.StringIO()):
            rc = a.cmd_approvals(brun, ["approve"])
        check("approve calls respond with the prompt id and returns 0",
              rc == 0 and sent and sent[-1][0] == "respond" and "--prompt-id" in sent[-1] and "p7" in sent[-1]
              and "approve" in sent[-1], sent)
        check("approve writes an approval event", os.path.exists(ev) and '"approval"' in open(ev).read())
        del sent[:]
        with contextlib.redirect_stdout(io.StringIO()):
            rc = a.cmd_approvals(brun, ["deny"])
        check("deny without that action returns 1 and does not call respond", rc == 1 and not sent, sent)
        resp[0] = (1, "", "error: forbidden")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = a.cmd_approvals(brun, ["approve"])
        check("forbidden prints the set-pane-grants command",
              rc == 1 and "tuios set-pane-grants -w plan" in out.getvalue() and "respond" in out.getvalue(),
              out.getvalue())
    finally:
        a.tuios, a.tuios_json, a.window_named = real

    print("approval prompts in wait-task and watch")
    listing = {"agents": [{"name": "build-billed", "blocked_by": "approval", "message": "Run rm?"}]}
    state = ["needs_input"]
    real = (a.tuios, a.tuios_json, a.window_named, a.agent_state, a.thread_replies)
    a.tuios = lambda *args, **kw: (0, "", "")
    a.tuios_json = lambda *args, **kw: listing
    a.window_named = lambda s, n: {"custom_name": n}
    a.agent_state = lambda s, n: state[0]
    a.thread_replies = lambda *args, **kw: []
    try:
        check("agent_info finds by name", a.agent_info("s", "build-billed").get("message") == "Run rm?")
        check("agent_info returns {} when absent", a.agent_info("s", "nobody") == {})
        check("wait_reply returns blocked for an approval",
              a.wait_reply("s", "plan", "t1", "build-billed", 5) == ("blocked", "Run rm?"))
        listing["agents"][0]["blocked_by"] = "question"
        check("wait_reply does not return blocked for a question",
              a.wait_reply("s", "plan", "t1", "build-billed", 0)[0] != "blocked")
        listing["agents"][0]["blocked_by"] = "approval"
        brun.data["builder"] = "build-billed"
        brun.data["tasks"] = {"T1": {"thread": "t1"}}
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = a.cmd_wait_task(brun, ["T1", "5"])
        check("wait-task prints the approval wait and returns 3", rc == 3 and "waits on an approval" in out.getvalue(),
              out.getvalue())
        brun.data.pop("blocked_seen", None)
        first = a.watch_blocked(brun)
        check("watch_blocked gives one block", len(first) == 1 and "Run rm?" in first[0], first)
        check("watch_blocked is quiet for the same message", a.watch_blocked(brun) == [])
        listing["agents"][0]["message"] = "Run ls?"
        check("watch_blocked gives a block for a new message", len(a.watch_blocked(brun)) == 1)
        state[0] = "idle"
        check("watch_blocked clears blocked_seen when unblocked",
              a.watch_blocked(brun) == [] and "blocked_seen" not in brun.data)
    finally:
        a.tuios, a.tuios_json, a.window_named, a.agent_state, a.thread_replies = real

    print("zen status")
    real = (a.subprocess.run, a.tuios, a.tuios_json, a.window_named, a.agent_state, a.start_builder)
    zrun = a.Run(p, "zen-test")
    out = [""]
    a.subprocess.run = lambda *args, **kw: type("R", (), {"stdout": out[0], "stderr": "", "returncode": 0})()
    a.tuios = lambda *args, **kw: (0, "", "")
    a.tuios_json = lambda *args, **kw: None
    a.window_named = lambda s, n: None
    a.agent_state = lambda s, n: "idle"
    started = []
    a.start_builder = lambda r, kind, name, ws, cwd: (started.append(kind) or (True, "ok"))
    try:
        def zs(doc):
            out[0] = doc if isinstance(doc, str) else json.dumps(doc)
            return a.zen_status(zrun)
        rec = lambda m, st: {"model": m, "state": st, "detail": ""}
        check("zen none", zs({"models": [], "best": None})["state"] == "none")
        check("zen exhausted", zs({"models": [rec("m1", "exhausted")], "best": None, "all_exhausted": True})["state"]
              == "exhausted")
        s = zs({"models": [rec("m1", "exhausted"), rec("m2", "available")], "best": "m2", "all_exhausted": False})
        check("zen available stores zen_model", s["state"] == "available" and s["model"] == "m2"
              and zrun.data.get("zen_model") == "m2" and s["detail"] == "m1: exhausted, m2: available", s)
        check("zen unknown", zs({"models": [rec("m1", "unknown")], "best": "m1", "all_exhausted": False})["state"]
              == "unknown")
        check("zen bad json is unknown", zs("not json")["state"] == "unknown")
        check("zen_usable", a.zen_usable({"state": "available"}) and a.zen_usable({"state": "unknown"})
              and not a.zen_usable({"state": "none"}) and not a.zen_usable({"state": "exhausted"}))
        codes = {}
        for label, doc in (("available", {"models": [rec("m2", "available")], "best": "m2"}),
                           ("unknown", {"models": [rec("m1", "unknown")], "best": "m1"}),
                           ("exhausted", {"models": [rec("m1", "exhausted")], "best": None, "all_exhausted": True}),
                           ("none", {"models": [], "best": None})):
            out[0] = json.dumps(doc)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                codes[label] = (a.cmd_zen_check(zrun, []), buf.getvalue())
        check("zen-check exit codes", [codes[k][0] for k in ("available", "unknown", "exhausted", "none")]
              == [0, 3, 1, 1], codes)
        check("zen-check lines", codes["available"][1].splitlines()[0] == "zen: available best=m2"
              and "  m2: available" in codes["available"][1] and "best=none" in codes["none"][1], codes)
        run.data["work_dir"] = p
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = a.cmd_builder(run, ["free"])
        check("builder free refuses when none usable", code == 1 and "not usable" in buf.getvalue() and not started,
              (code, buf.getvalue(), started))
    finally:
        a.subprocess.run, a.tuios, a.tuios_json, a.window_named, a.agent_state, a.start_builder = real

    print("escalation")
    tt = {}
    a.count_attempt(tt, "build-local")
    a.count_attempt(tt, "build-local")
    a.count_attempt(tt, "build-free")
    check("count_attempt per builder", tt.get("by") == {"build-local": 2, "build-free": 1}, tt)
    check("tier_of", [a.tier_of(n) for n in ("build-local", "build-free", "build-billed", "x", None)]
          == ["local", "free", "billed", None, None])
    check("next_tier table", [a.next_tier(*c) for c in (("local", "available"), ("local", "exhausted"),
                                                       ("local", "none"), ("free", "available"),
                                                       ("billed", "available"), ("x", "available"))]
          == ["free", "billed", "billed", "billed", None, None])
    erun = a.Run(p, "20260101-000002")
    ecalls, eclosed, ezen = [], [], ["available"]
    ereal = (a.zen_status, a.cmd_builder, a.tuios)
    a.zen_status = lambda r, refresh=False: {"state": ezen[0], "detail": ""}
    a.cmd_builder = lambda r, argv: (ecalls.append(argv), ecode[0])[1]
    a.tuios = lambda *args, **kw: (eclosed.append(args[1]) if args[0] == "close-window" else None) or (0, "", "")
    ecode = [0]

    def esc(status, by, builder="build-local"):
        erun.data.update(builder=builder, tasks={"T1": {"status": status, "attempts": sum(by.values()), "by": by}})
        ecalls.clear()
        eclosed.clear()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = a.cmd_escalate(erun, ["T1"])
        return code, buf.getvalue()

    try:
        code, out = esc("sent", {"build-local": 2})
        check("escalate refuses a pending task", code == 1 and not ecalls, (code, out))
        code, out = esc("failed", {"build-local": 1})
        check("escalate refuses after one failure", code == 1 and not ecalls, (code, out))
        code, out = esc("failed", {"build-local": 2})
        check("escalate local to free", code == 0 and ecalls == [["free"]] and eclosed == ["build-local"]
              and "build-local -> build-free" in out, (code, ecalls, eclosed, out))
        ezen[0] = "exhausted"
        code, out = esc("failed", {"build-local": 2})
        check("escalate local to billed when free is exhausted", code == 0 and ecalls == [["billed"]]
              and "not usable" in out, (code, ecalls, out))
        ezen[0] = "available"
        code, out = esc("failed", {"build-billed": 2}, "build-billed")
        check("escalate from billed returns 2", code == 2 and not ecalls, (code, ecalls, out))
        ecode[0] = 1
        code, out = esc("failed", {"build-local": 2})
        check("escalate with cmd_builder failing closes nothing", code == 1 and not eclosed, (code, eclosed, out))
    finally:
        a.zen_status, a.cmd_builder, a.tuios = ereal

    print("lumo confirmation")
    link = "See https://example.com/doc for details.\n"
    good = link + "SEARCH-CONFIRMATION: searched=yes; queries=nix flake lock | darwin-rebuild; sources=1"
    check("lumo valid reply", a.lumo_confirmation(good) == (True, "", "nix flake lock | darwin-rebuild"),
          a.lumo_confirmation(good))
    check("lumo no line", a.lumo_confirmation(link) == (False, "no SEARCH-CONFIRMATION line", ""))
    no = link + "SEARCH-CONFIRMATION: searched=no; reason=no tool"
    check("lumo searched=no", a.lumo_confirmation(no) == (False, "Lumo says it did not search", ""))
    for q in ("<none>", ""):
        r = link + f"SEARCH-CONFIRMATION: searched=yes; queries={q}; sources=0"
        check(f"lumo queries {q!r}", a.lumo_confirmation(r) == (False, "no queries listed", ""), a.lumo_confirmation(r))
    nolink = "No links here.\nSEARCH-CONFIRMATION: searched=yes; queries=nix flakes; sources=0"
    check("lumo no link", a.lumo_confirmation(nolink) == (False, "no source links", "nix flakes"),
          a.lumo_confirmation(nolink))
    two = good + "\nSEARCH-CONFIRMATION: searched=no; reason=x"
    check("lumo last line wins", a.lumo_confirmation(two)[1] == "Lumo says it did not search")
    bold = link + "> **SEARCH-CONFIRMATION: searched=yes; queries=`nix store gc`; sources=1**"
    check("lumo bold or quoted line", a.lumo_confirmation(bold)[0] is True, a.lumo_confirmation(bold))
    check("lumo preamble", "SEARCH-CONFIRMATION" in a.LUMO_PREAMBLE and "web search tool" in a.LUMO_PREAMBLE)

    print("ask-lumo")

    class FakeRun:
        def __init__(self):
            self.dir = tempfile.mkdtemp(prefix="aidev-test-lumo-")
            self.session = "s"
            self.data = {"panes": {a.RESEARCH: {"session_id": "l1"}}}
            self.events = []

        def event(self, kind, **kw):
            self.events.append((kind, kw))

    def ask(replies):
        fr = FakeRun()
        sent = []

        def once(_run, text):
            sent.append(text)
            return replies[len(sent) - 1], ""

        a.ask_lumo_once = once
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = a.cmd_ask_lumo(fr, ["which", "X?"])
        return rc, buf.getvalue(), sent, fr

    link = "Use X 2.0, see https://example.org\n"
    okr = link + "SEARCH-CONFIRMATION: searched=yes; queries=x release notes; sources=1"
    badr = "SECRET BODY from memory\nSEARCH-CONFIRMATION: searched=no; reason=no tool"
    rc, out, sent, fr = ask([okr])
    check("ask-lumo confirmed first reply returns 0", rc == 0 and len(sent) == 1, (rc, out))
    check("ask-lumo prints the queries", "x release notes" in out and "Use X 2.0" in out, out)
    check("ask-lumo sends the preamble first", sent[0].startswith(a.LUMO_PREAMBLE) and sent[0].endswith("which X?"),
          sent)
    check("ask-lumo logs searched=True", fr.events and fr.events[-1][1].get("searched") is True, fr.events)
    rc, out, sent, fr = ask([badr, okr])
    check("ask-lumo unconfirmed then confirmed returns 0", rc == 0 and len(sent) == 2, (rc, len(sent)))
    check("ask-lumo re-asks with the reason", "did not confirm" in sent[1] and sent[1].endswith("which X?"), sent)
    rc, out, sent, fr = ask([badr, badr, badr])
    check("ask-lumo rejects after three tries with exit 4", rc == 4 and len(sent) == 3, (rc, len(sent)))
    check("ask-lumo prints REJECTED, not the reply", "REJECTED" in out and "SECRET BODY" not in out, out)
    files = [f for f in os.listdir(fr.dir) if f.startswith("lumo-rejected-")]
    check("ask-lumo writes the rejected reply to a file",
          len(files) == 1 and "SECRET BODY" in open(os.path.join(fr.dir, files[0])).read(), files)
    check("ask-lumo logs searched=False", fr.events and fr.events[-1][1].get("searched") is False, fr.events)

    print("watch-lumo labels")

    class WatchRun:
        def __init__(self):
            self.session = "s"
            self.data = {"panes": {a.RESEARCH: {"session_id": "l1"}}}

        def save(self):
            pass

    def watch(reply):
        wr = WatchRun()
        a.lumo_messages = lambda _run: [("m1", "user", "which X?"), ("m2", "assistant", reply)]
        a.agent_state = lambda _s, _n: "idle"
        first = a.watch_lumo(wr)
        return first, a.watch_lumo(wr)

    first, again = watch(okr)
    check("watch_lumo labels a confirmed reply",
          len(first) == 1 and "Lumo (web search confirmed: x release notes)" in first[0] and "Asked: which X?" in first[0],
          first)
    check("watch_lumo reports an exchange once", again == [], again)
    first, _again = watch(badr)
    check("watch_lumo labels an unconfirmed reply", len(first) == 1 and "NOT confirmed" in first[0], first)

    print("find and close failures")
    fperm = a.builder_permissions(None)
    check("find not allowed", not any(r.startswith("Bash(find") for r in fperm["allow"]), fperm["allow"])
    check("find -delete and -exec denied", "Bash(find * -delete*)" in fperm["deny"]
          and "Bash(find * -exec*)" in fperm["deny"], fperm["deny"])
    frun = a.Run(p, "20260101-000003")
    freal = (a.tuios, a.tuios_json, a.window_named, a.agent_state, a.cmd_builder, a.zen_status)
    a.tuios = lambda *args, **kw: (1, "", "forbidden") if args[0] == "close-window" else (0, "", "")
    a.tuios_json = lambda *args, **kw: None
    a.agent_state = lambda *args, **kw: None
    a.cmd_builder = lambda r, argv: 0
    a.zen_status = lambda r, refresh=False: {"state": "available", "detail": ""}
    try:
        frun.data.update(builder="build-local", tasks={"T1": {"status": "failed", "attempts": 2,
                                                              "by": {"build-local": 2}}})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = a.cmd_escalate(frun, ["T1"])
        check("escalate says the pane could not be closed", code == 0 and "close that pane by hand" in buf.getvalue(),
              (code, buf.getvalue()))
        a.tuios = lambda *args, **kw: (0, "", "")
        a.window_named = lambda session, name: {"name": name} if name == "build-local" else None
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            a.cmd_finish(frun, [])
        check("finish lists builder panes still open", "still open" in buf.getvalue() and "build-local" in buf.getvalue(),
              buf.getvalue())
        a.window_named = lambda session, name: None
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            a.cmd_finish(frun, [])
        check("finish prints nothing when no builder pane is open", "still open" not in buf.getvalue(), buf.getvalue())
    finally:
        a.tuios, a.tuios_json, a.window_named, a.agent_state, a.cmd_builder, a.zen_status = freal

    if FAILS:
        print("FAILED: " + ", ".join(FAILS))
        return 1
    print("all passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
