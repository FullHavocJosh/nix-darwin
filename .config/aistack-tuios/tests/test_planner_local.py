"""Tests for planner_local: probe, planner choice, models, events, gate and research cache."""

import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "planner_local", os.path.join(HERE, "..", "planner_local.py")
)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

FAILS = []

CLAUDE_CMD = [
    "claude",
    "-p",
    "Reply with the single word ok.",
    "--model",
    "haiku",
    "--no-session-persistence",
    "--output-format",
    "text",
]


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


class Result:
    """Stand-in for subprocess.CompletedProcess."""

    def __init__(self, returncode, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def fake_runner(result=None, exc=None):
    """Return a runner that records its call and returns result or raises exc."""
    seen = []

    def runner(cmd, **kwargs):
        seen.append((cmd, kwargs))
        if exc is not None:
            raise exc
        return result

    runner.seen = seen
    return runner


# claude_available: the runner is passed as an argument; subprocess.run is never
# patched because the default argument is bound at definition time.
r = fake_runner(result=Result(0, stdout="ok\n"))
ok, why = p.claude_available(runner=r)
check("claude_available success", ok and why == "")
check("claude_available command", bool(r.seen) and r.seen[0][0] == CLAUDE_CMD)
kwargs = r.seen[0][1] if r.seen else {}
check(
    "claude_available runner kwargs",
    kwargs.get("capture_output") is True
    and kwargs.get("text") is True
    and kwargs.get("check") is False
    and kwargs.get("stdin") == subprocess.DEVNULL
    and kwargs.get("timeout") == 20,
)

r = fake_runner(result=Result(1, stdout="error\n", stderr="boom"))
ok, why = p.claude_available(runner=r)
check(
    "claude_available failure",
    not ok and "claude exited 1" in why and "boom" in why,
)

r = fake_runner(result=Result(0, stdout="", stderr=""))
ok, why = p.claude_available(runner=r)
check("claude_available empty output", not ok and "claude exited 0" in why)

r = fake_runner(result=Result(0, stdout="   \n"))
ok, why = p.claude_available(runner=r)
check("claude_available whitespace output", not ok)

r = fake_runner(result=Result(2, stdout="x" * 300))
ok, why = p.claude_available(runner=r)
check(
    "claude_available last 200 chars",
    not ok and why == "claude exited 2: " + "x" * 200,
)

r = fake_runner(exc=subprocess.TimeoutExpired("claude", 1))
ok, why = p.claude_available(timeout=5, runner=r)
check("claude_available timeout", not ok and why == "claude did not answer in 5 s")
check(
    "claude_available timeout forwarded",
    bool(r.seen) and r.seen[0][1].get("timeout") == 5,
)

r = fake_runner(exc=FileNotFoundError())
ok, why = p.claude_available(runner=r)
check("claude_available not installed", not ok and why == "claude is not installed")


# choose_planner: the probe is passed as an argument, for the same reason.
def refusing_probe():
    raise AssertionError("probe must not run when AIDEV_TUIOS_PLANNER forces a planner")


planner, reason = p.choose_planner(
    {"AIDEV_TUIOS_PLANNER": "claude"}, probe=refusing_probe
)
check(
    "choose_planner forced claude",
    planner == "claude" and reason == "forced by AIDEV_TUIOS_PLANNER",
)

planner, reason = p.choose_planner(
    {"AIDEV_TUIOS_PLANNER": "local"}, probe=refusing_probe
)
check(
    "choose_planner forced local",
    planner == "local" and reason == "forced by AIDEV_TUIOS_PLANNER",
)

planner, reason = p.choose_planner({}, probe=lambda: (True, ""))
check("choose_planner probe ok", planner == "claude" and reason == "")

planner, reason = p.choose_planner({}, probe=lambda: (False, "claude is not installed"))
check(
    "choose_planner probe not ok",
    planner == "local" and reason == "claude is not installed",
)

planner, reason = p.choose_planner(
    {"AIDEV_TUIOS_PLANNER": "bogus"},
    probe=lambda: (False, "claude is not installed"),
)
check(
    "choose_planner unknown value uses probe",
    planner == "local" and reason == "claude is not installed",
)


# planner_models
config = p.planner_models("http://localhost:1234/", "lumo-max", 8192)
expected = {
    "providers": {
        "planner": {
            "baseUrl": "http://localhost:1234/v1",
            "api": "openai-completions",
            "apiKey": "sk-local",
            "models": [
                {
                    "id": "lumo-max",
                    "reasoning": False,
                    "contextWindow": 8192,
                    "maxTokens": 4096,
                }
            ],
        }
    }
}
check("planner_models", config == expected)


# read_events
with tempfile.TemporaryDirectory() as tmpdir:
    check("read_events missing dir", p.read_events(os.path.join(tmpdir, "nope")) == [])
    check("read_events empty dir", p.read_events(tmpdir) == [])
    with open(os.path.join(tmpdir, "events.jsonl"), "w") as f:
        f.write('{"kind": "one"}\n')
        f.write("not json at all\n")
        f.write('{"kind": "two"}\n')
    events = p.read_events(tmpdir)
    check(
        "read_events skips bad lines",
        events == [{"kind": "one"}, {"kind": "two"}],
    )


# gate_message: every branch.
check(
    "gate_message not local",
    p.gate_message([{"kind": "ask_lumo", "searched": True}], "claude", True, {}) == "",
)
check("gate_message no research", p.gate_message([], "local", False, {}) == "")
check(
    "gate_message gate off",
    p.gate_message([], "local", True, {"AIDEV_TUIOS_PLANNER_GATE": "off"}) == "",
)
check(
    "gate_message ask_lumo searched",
    p.gate_message([{"kind": "ask_lumo", "searched": True}], "local", True, {}) == "",
)
check(
    "gate_message ask_lumo unsearched still gates",
    p.gate_message(
        [{"kind": "ask_lumo", "searched": False}], "local", True, {}
    ).startswith("RESEARCH REQUIRED:"),
)
check(
    "gate_message lumo_waiver",
    p.gate_message([{"kind": "lumo_waiver"}], "local", True, {}) == "",
)
msg = p.gate_message([], "local", True, {})
check("gate_message requires research", msg.startswith("RESEARCH REQUIRED:"))
check("gate_message mentions ask-lumo", "ask-lumo" in msg)
check("gate_message mentions --none-needed", "--none-needed" in msg)


# cache_path / cache_lookup / cache_store round trip.
with tempfile.TemporaryDirectory() as tmpdir:
    research_dir = os.path.join(tmpdir, "research")
    path = p.cache_path(research_dir, "Test Question")
    check("cache_path", path == os.path.join(research_dir, "cfbb1874a53c.md"))
    check(
        "cache_path normalizes question",
        p.cache_path(research_dir, "  TEST   question  ") == path,
    )
    check("cache_lookup miss", p.cache_lookup(research_dir, "Test Question") is None)
    stored = p.cache_store(research_dir, "Test Question", "the reply", "q1, q2")
    check("cache_store makes directory", os.path.isdir(research_dir))
    check("cache_store returns path", stored == path and os.path.exists(stored))
    text = p.cache_lookup(research_dir, "Test Question")
    check(
        "cache round trip",
        text == "QUESTION: Test Question\nQUERIES: q1, q2\n\nthe reply",
    )
    check(
        "cache_lookup via normalized question",
        p.cache_lookup(research_dir, "TEST QUESTION") == text,
    )

sys.exit(1 if FAILS else 0)
