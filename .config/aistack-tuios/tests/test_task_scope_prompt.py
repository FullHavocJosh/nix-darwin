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

failures = 0

# Test with files parameter
story = {"id": "T1", "title": "a task", "description": "UNIQUE-STORY-DESCRIPTION", "acceptanceCriteria": ["GOAL-CRITERION"]}
prd = {"name": "p", "description": "PLAN-DESC"}
files = ["a/b.txt"]

prompt = a.task_prompt(prd, story, ["true"], [], wd="/w", files=files)
failures += check("prompt contains ## Files you may change", "## Files you may change" in prompt)
failures += check("prompt contains - a/b.txt", "- a/b.txt" in prompt)
failures += check("prompt contains blocked: need", "blocked: need" in prompt)

# Test with retry_files and files
retry_prompt = a.task_prompt(prd, story, ["true"], ["- fix x"], wd="/w", retry_files=["a/b.txt"], files=files)
failures += check("retry prompt contains ## Files you may change", "## Files you may change" in retry_prompt)

# Test without files parameter
prompt_no_files = a.task_prompt(prd, story, ["true"], [], wd="/w")
failures += check("prompt without files does not contain ## Files you may change", "## Files you may change" not in prompt_no_files)

sys.exit(failures)