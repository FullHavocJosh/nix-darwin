#!/usr/bin/env python3
"""Test that new panes are minimized after creation and the zsh window never is."""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def fake(calls, fail=()):
    def fake_tuios(*args, **_kw):
        calls.append(args)
        return (1, "", "boom") if args and args[0] in fail else (0, "", "")
    return fake_tuios


def minimized(calls):
    return [c[c.index("-w") + 1] for c in calls if c and c[0] == "set-window" and "--minimize" in c]


class FakeRun:
    def __init__(self):
        self.data = {"panes": {}}

    def save(self):
        pass


def main():
    a.grantable = lambda session, name, grants: grants
    a.WS.setdefault("build", 2)

    calls = []
    a.tuios = fake(calls)
    check("minimize_window returns True", a.minimize_window("S", "N") is True)
    check("minimize_window args", calls == [("set-window", "-s", "S", "-w", "N", "--minimize")], str(calls))

    a.tuios = fake([], fail=("set-window",))
    check("minimize_window returns False on failure", a.minimize_window("S", "N") is False)

    def boom(*_a, **_kw):
        raise OSError("x")
    a.tuios = boom
    check("minimize_window never raises", a.minimize_window("S", "N") is False)

    name = next(iter(a.WS))
    calls = []
    a.tuios = fake(calls)
    a.window_named = lambda session, n: None
    check("open_pane opens", a.open_pane(FakeRun(), "S", name, "/s.sh", "/w", "read") is True)
    check("open_pane minimizes the new window", minimized(calls) == [name], str(calls))

    calls = []
    a.tuios = fake(calls, fail=("new-window",))
    check("open_pane fails when new-window fails", a.open_pane(FakeRun(), "S", name, "/s.sh", "/w", "read") is False)
    check("open_pane does not minimize on failure", minimized(calls) == [], str(calls))

    calls = []
    a.tuios = fake(calls)
    a.window_named = lambda session, n: {"custom_name": n}
    check("open_pane skips an existing window", a.open_pane(FakeRun(), "S", name, "/s.sh", "/w", "read") is False)
    check("open_pane does not minimize an existing window", calls == [], str(calls))

    calls = []
    a.tuios = fake(calls)
    a.window_named = lambda session, n: None
    a.start_dev_workspace(FakeRun(), "S", "/w")
    check("start_dev_workspace minimizes nvim only", minimized(calls) == ["nvim"], str(calls))
    check("start_dev_workspace opens zsh", any(c[:2] == ("new-window", "zsh") for c in calls), str(calls))

    calls = []
    a.tuios = fake(calls)
    a.ensure_zsh_window("S", "/w")
    check("ensure_zsh_window never minimizes", minimized(calls) == [] and calls, str(calls))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
