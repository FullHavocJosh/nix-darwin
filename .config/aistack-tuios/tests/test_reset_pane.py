#!/usr/bin/env python3
"""Test that reset_pane confirms a reset by the pi and OpenCode markers or by a new agent session id."""

import importlib.util
import os
import sys
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def reset(ids, screen):
    """reset_pane with a fake tuios showing `screen` and agent session ids taken from `ids` (the last one repeats)."""
    calls = []

    def fake_tuios(*args, **_kw):
        return (0, screen, "") if args and args[0] == "capture-pane" else (0, "", "")

    def fake_id(_session, _name):
        calls.append(1)
        return ids[min(len(calls), len(ids)) - 1]

    a.tuios = fake_tuios
    a.agent_session_id = fake_id
    return a.reset_pane(types.SimpleNamespace(session="s"), "build", "/clear")


def main():
    real_tuios, real_id = a.tuios, a.agent_session_id
    a.time = types.SimpleNamespace(sleep=lambda s: None, time=time.time)
    check("new session id confirms", reset(["old", "old", "new"], "") is True)
    check("unchanged id does not confirm", reset(["old"], "") is False)
    check("missing id does not confirm", reset([""], "") is False)
    check("new session marker confirms", reset(["old"], "Started a new session") is True)

    a.tuios, a.agent_session_id = real_tuios, real_id
    a.tuios_json = lambda *args, **kw: {"agent_session_id": "abc"}
    check("agent_session_id reads the id", a.agent_session_id("s", "build") == "abc")
    a.tuios_json = lambda *args, **kw: {}
    check("agent_session_id without id is empty", a.agent_session_id("s", "build") == "")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
