"""Tests for the research call log: log_research in ralph_mcp.py appends one JSON line per repo_tree / repo_read /
repo_grep call to <state_dir>/research-calls.jsonl, including calls the budget refuses. The log holds the arguments
only, never a file's contents, and a log that cannot be written never breaks the tool.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_research_log.py
"""

import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FAILS = []


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


T = os.path.realpath(tempfile.mkdtemp(prefix="research-log-"))
PROJECT, STATE = T + "/proj", T + "/state"
os.makedirs(PROJECT + "/lib")
SECRET = "SMALL_FILE_CONTENT_8271"
open(PROJECT + "/lib/small.py", "w").write("def small():\n    return %r\n" % SECRET)
os.environ.update(RALPH_MCP_ROOTS=PROJECT, AISTACK_STATE_DIR=STATE)
spec = importlib.util.spec_from_file_location(
    "ralph_mcp", os.path.join(HERE, "..", "ralph_mcp.py")
)
mcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mcp)

LOG = os.path.join(mcp.state_dir(PROJECT), "research-calls.jsonl")
REQ = {"ts", "tool", "args", "calls_left", "ok", "bytes"}


def read_log():
    """The log's raw lines and the ones that are valid JSON objects (a broken line is not parsed)."""
    if not os.path.exists(LOG):
        return [], []
    raw = [ln for ln in open(LOG).read().splitlines() if ln]
    recs = []
    for ln in raw:
        try:
            recs.append(json.loads(ln))
        except ValueError:
            pass
    return raw, recs


print("research log: one line per call")
mcp.RESEARCH_CALLS = 0
A = {"project_dir": PROJECT}
r1 = mcp.tool_repo_tree(dict(A))
r2 = mcp.tool_repo_read(dict(A, path="lib/small.py"))
r3 = mcp.tool_repo_grep(dict(A, pattern="def small"))
raw, recs = read_log()
raw_text = "\n".join(raw)
check("one line per call", len(raw) == 3, str(len(raw)))
check(
    "every line is valid JSON with the required keys, and nothing else is required",
    len(recs) == 3 and all(REQ <= set(x) for x in recs),
    str([sorted(x) for x in recs])[:300],
)
check(
    "tool names are the tool function names without the tool_ prefix",
    [x["tool"] for x in recs] == ["repo_tree", "repo_read", "repo_grep"],
    str([x.get("tool") for x in recs]),
)
check(
    "calls_left counts down across the calls",
    [x["calls_left"] for x in recs]
    == [mcp.RESEARCH_BUDGET - 1, mcp.RESEARCH_BUDGET - 2, mcp.RESEARCH_BUDGET - 3],
    str([x["calls_left"] for x in recs]),
)
check(
    "args holds the call's arguments and never project_dir",
    all("project_dir" not in x["args"] for x in recs)
    and recs[1]["args"] == {"path": "lib/small.py"}
    and recs[2]["args"] == {"pattern": "def small"},
    str([x["args"] for x in recs])[:300],
)
check(
    "each line has a UTC ISO-8601 timestamp",
    all(
        isinstance(x["ts"], str) and x["ts"].endswith("Z") and "T" in x["ts"]
        for x in recs
    ),
    str([x["ts"] for x in recs]),
)
check(
    "a call that worked is ok true and its bytes measure the result",
    all(
        x["ok"] is True and isinstance(x["bytes"], int) and x["bytes"] > 0 for x in recs
    ),
    str([(x["ok"], x["bytes"]) for x in recs])[:200],
)
check("no line contains the file's text", SECRET not in raw_text)
check(
    "nothing was written into the project",
    sorted(os.listdir(PROJECT)) == ["lib"],
    str(os.listdir(PROJECT)),
)

print("research log: a call the budget refuses is logged")
mcp.RESEARCH_CALLS = mcp.RESEARCH_BUDGET
r = mcp.tool_repo_tree(dict(A))
raw, recs = read_log()
last = recs[-1]
check(
    "the tool refuses as before",
    r.get("ok") is False and "calls_left" in r and r["calls_left"] == 0,
    str(r)[:200],
)
check("the refused call still gets one line", len(recs) == 4, str(len(recs)))
check(
    "that line has ok false and calls_left 0",
    last["ok"] is False and last["calls_left"] == 0,
    str(last)[:200],
)
check(
    "the refused line names the tool and holds no file text",
    last["tool"] == "repo_tree" and SECRET not in "\n".join(raw),
)
check(
    "project_dir is still absent from the logged arguments",
    "project_dir" not in last["args"],
)

print("research log: an unwritable state dir does not break the tool")
open(T + "/afile", "w").write("x")
os.environ["AISTACK_STATE_DIR"] = (
    T + "/afile/state"
)  # a state dir under a regular file: makedirs cannot work
mcp.RESEARCH_CALLS = 0
r = mcp.tool_repo_read(dict(A, path="lib/small.py"))
check(
    "the call still returns its result",
    r.get("ok") is True and "def small():" in r.get("text", ""),
    str(r)[:200],
)
check(
    "no stray file was created where the log would go",
    not os.path.exists(T + "/afile/state"),
)
os.environ["AISTACK_STATE_DIR"] = STATE

print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
