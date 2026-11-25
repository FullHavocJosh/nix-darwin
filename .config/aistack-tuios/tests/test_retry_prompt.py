import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
os.environ["AIDEV_TUIOS_WORKTREE_MODE"] = "none"; os.environ["AISTACK_WORKTREE_MODE"] = "none"
os.environ["AISTACK_DIR"] = os.path.realpath(os.path.join(ROOT, "..", "aistack"))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(ROOT, "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec); spec.loader.exec_module(a)


def check(name, cond):
    if not cond:
        print(f"FAIL: {name}")
        return 1
    print(f"PASS: {name}")
    return 0

story = {"id": "T1", "title": "a task", "description": "UNIQUE-STORY-DESCRIPTION", "acceptanceCriteria": ["GOAL-CRITERION"]}
prd = {"name": "p", "description": "PLAN-DESC"}
notes = ["- Attempt 1: the checks failed; FAIL-LINE"]

# Test full prompt
full = a.task_prompt(prd, story, ["true"], notes, wd="/w")
# Test retry prompt
retry = a.task_prompt(prd, story, ["true"], notes, wd="/w", retry_files=["CHANGED-FILE-A"])

failures = 0
failures += check("UNIQUE-STORY-DESCRIPTION in full", "UNIQUE-STORY-DESCRIPTION" in full)
failures += check("PLAN-DESC in full", "PLAN-DESC" in full)
failures += check("fix only not in full", "fix only" not in full)
failures += check("CHANGED-FILE-A not in full", "CHANGED-FILE-A" not in full)
failures += check("`true` in full", "`true`" in full)

failures += check("fix only in retry", "fix only" in retry)
failures += check("CHANGED-FILE-A in retry", "CHANGED-FILE-A" in retry)
failures += check("FAIL-LINE in retry", "FAIL-LINE" in retry)
failures += check("GOAL-CRITERION in retry", "GOAL-CRITERION" in retry)
failures += check("`true` in retry", "`true`" in retry)
failures += check("UNIQUE-STORY-DESCRIPTION not in retry", "UNIQUE-STORY-DESCRIPTION" not in retry)
failures += check("PLAN-DESC not in retry", "PLAN-DESC" not in retry)

# Test the new retry functionality
import types

p = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-"))
prd2 = {"name": "retry", "description": "x", "userStories": [{"id": "T1", "title": "t", "description": "UNIQUE-STORY-DESCRIPTION", "acceptanceCriteria": ["GOAL-CRITERION"]}]}
verify2 = {"T1": ["true"]}
a.load_lib = lambda project=None, run=None: types.SimpleNamespace(load_plan=lambda project: (prd2, verify2, None))
a.window_named = lambda session, name: True
a.prepare_builder = lambda run, builder: True
a.mail_task = lambda run, builder, subject, mail_text, prompt: "7"
a.snapshot_work = lambda run, label: None
a.compaction_count = lambda session, builder: 0
a.overflow_count = lambda session, builder: 0
a.git_out = lambda wd, *args: "CHANGED-FILE-A\n" if args[:2] == ("diff", "--name-only") else ""
written = []
orig_write = a.write_text
a.write_text = lambda path, text: (written.append(text) if path.endswith(".md") else None) or orig_write(path, text)
run = a.Run(p, "20260101-000001")
run.data["session"] = "test"; run.data["builder"] = "build-local"; run.data["work_dir"] = p

# Send T1 --to tier-3: the file has UNIQUE-STORY-DESCRIPTION
a.scope_fingerprint = lambda wd: {}
a.cmd_send_task(run, ["T1", "--to", "tier-3"])
failures += check("first attempt sends the full task", "UNIQUE-STORY-DESCRIPTION" in written[-1])
a.scope_fingerprint = lambda wd: {"CHANGED-FILE-A": "1"}

# Send again: the file has "fix only" and CHANGED-FILE-A
a.cmd_send_task(run, ["T1", "--to", "tier-3"])
failures += check("retry with edits sends fix only", "fix only" in written[-1] and "CHANGED-FILE-A" in written[-1])
failures += check("retry names the edited files without other tasks", "Earlier attempts left uncommitted edits" in written[-1] and "earlier tasks'" not in written[-1])

# Set run.data["tasks"]["T1"]["handoff"] = True and send again: the file has UNIQUE-STORY-DESCRIPTION and 'handoff' is gone from the task
run.data["tasks"]["T1"]["handoff"] = True
a.cmd_send_task(run, ["T1", "--to", "tier-3"])
failures += check("retry after a context handoff sends the full task", "UNIQUE-STORY-DESCRIPTION" in written[-1] and "handoff" not in run.data["tasks"]["T1"])

print(f"Summary: {failures} failures")
sys.exit(1 if failures else 0)