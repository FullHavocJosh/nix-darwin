"""Tests for hosts_workspace.py: one read-only tuios window per host on workspace 2
of the session, skipping windows that already exist. Uses fake tuios/tuios_json
callables that record their calls; needs no tuios daemon, no model and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_hosts_workspace.py
"""

import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
FAILS = []

HOSTS = [
    {"name": "top-trashcan"},
    {"name": "top-josh-g14"},
    {"name": "top-cait-g14"},
    {"name": "top-macmini"},
]
SESSION = "hw-test"
SCRIPT = "/does/not/exist/host-pane.sh"
CWD = "/does/not/exist"
FORBIDDEN = ("admin", "write", "fan", "respond")


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_fakes(result=(0, "", ""), windows=None):
    """tuios/tuios_json fakes that record every call. tuios returns `result`;
    tuios_json answers 'list-windows' with {"windows": windows}."""
    calls = []

    def fake_tuios(*args):
        calls.append(("tuios",) + tuple(args))
        return result

    def fake_tuios_json(*args):
        calls.append(("tuios_json",) + tuple(args))
        if args and args[0] == "list-windows":
            return {"windows": [dict(w) for w in (windows or [])]}
        return {}

    return fake_tuios, fake_tuios_json, calls


def new_window_calls(calls):
    return [c for c in calls if c[0] == "tuios" and len(c) > 1 and c[1] == "new-window"]


def after_flag(call, flag):
    """The argument right after `flag` in a recorded call, or None."""
    args = list(call[1:])
    if flag in args:
        i = args.index(flag)
        if i + 1 < len(args):
            return args[i + 1]
    return None


def write_table(path, hosts):
    with open(path, "w") as f:
        json.dump({"hosts": hosts}, f)


def inject_aidev_tuios(tuios, tuios_json):
    """Stand in for the real aidev_tuios module that hosts_workspace.main imports lazily."""
    mod = types.ModuleType("aidev_tuios")
    mod.tuios = tuios
    mod.tuios_json = tuios_json
    sys.modules["aidev_tuios"] = mod


def run_main(hw, table, tuios, tuios_json):
    inject_aidev_tuios(tuios, tuios_json)
    return hw.main(["--table", table, "--session", SESSION])


def main():
    hw = load("hosts_workspace", os.path.join(ROOT, "hosts_workspace.py"))
    saved_mod = sys.modules.get("aidev_tuios")
    saved_path = list(sys.path)
    all_calls = []
    try:
        with tempfile.TemporaryDirectory() as d:
            table = os.path.join(d, "hosts.json")
            write_table(table, HOSTS)

            print("load_hosts")
            check("accepts a valid table", hw.load_hosts(table) == HOSTS)
            for label, hosts in (
                ("rejects a missing path", None),
                (
                    "rejects a name without the top- prefix",
                    [{"name": "top-trashcan"}, {"name": "josh-g14"}],
                ),
                ("rejects an empty name", [{"name": "top-trashcan"}, {"name": ""}]),
            ):
                path = os.path.join(d, "missing.json" if hosts is None else "bad.json")
                if hosts is not None:
                    write_table(path, hosts)
                try:
                    hw.load_hosts(path)
                    check(label, False, "no ValueError")
                except ValueError:
                    check(label, True)

            print("open_hosts with no existing windows")
            tuios, tuios_json, calls = make_fakes(windows=[])
            results = hw.open_hosts(SESSION, HOSTS, 2, tuios, tuios_json, SCRIPT, CWD)
            all_calls.extend(calls)
            nw = new_window_calls(calls)
            check("4 hosts and no windows give 4 new-window calls", len(nw) == 4, calls)
            check(
                "every host reports ok",
                [ok for _, ok in results] == [True] * 4,
                results,
            )
            check(
                "each call holds '--grants' followed by exactly 'read'",
                all(after_flag(c, "--grants") == "read" for c in nw),
                nw,
            )
            check(
                "each call holds '--workspace' followed by '2'",
                all(after_flag(c, "--workspace") == "2" for c in nw),
                nw,
            )
            check(
                "each call holds '--no-focus'", all("--no-focus" in c for c in nw), nw
            )

            print("open_hosts when tuios fails")
            tuios, tuios_json, calls = make_fakes(result=(1, "", "boom"))
            results = hw.open_hosts(SESSION, HOSTS, 2, tuios, tuios_json, SCRIPT, CWD)
            all_calls.extend(calls)
            check(
                "ok is False for every host tried",
                len(results) == 4 and all(ok is False for _, ok in results),
                results,
            )

            print("main: first run, no windows yet")
            tuios, tuios_json, calls = make_fakes(windows=[])
            rc = run_main(hw, table, tuios, tuios_json)
            all_calls.extend(calls)
            check("returns 0 on the first run", rc == 0, rc)
            check(
                "opens 4 windows on the first run",
                len(new_window_calls(calls)) == 4,
                calls,
            )

            print("main: second run, all four windows exist")
            windows = [{"custom_name": h["name"]} for h in HOSTS]
            tuios, tuios_json, calls = make_fakes(windows=windows)
            rc = run_main(hw, table, tuios, tuios_json)
            all_calls.extend(calls)
            check("returns 0 on the second run", rc == 0, rc)
            check(
                "a second run with all four windows present opens none",
                new_window_calls(calls) == [],
                calls,
            )

            print("main: one existing window")
            tuios, tuios_json, calls = make_fakes(
                windows=[{"custom_name": "top-macmini"}]
            )
            rc = run_main(hw, table, tuios, tuios_json)
            all_calls.extend(calls)
            check("returns 0 with one existing window", rc == 0, rc)
            check(
                "one existing window gives 3 calls",
                len(new_window_calls(calls)) == 3,
                calls,
            )

            print("main: every window fails")
            tuios, tuios_json, calls = make_fakes(result=(1, "", "boom"))
            rc = run_main(hw, table, tuios, tuios_json)
            all_calls.extend(calls)
            check("returns 1 when every window fails", rc == 1, rc)

            print("main: missing table is a no-op")
            missing = os.path.join(d, "no-table.json")
            sys.modules.pop("aidev_tuios", None)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = hw.main(["--table", missing, "--session", "x"])
            check("returns 0 with a missing table", rc == 0, rc)
            check(
                "prints 'no host table: skipping'",
                buf.getvalue().strip() == "no host table: skipping",
                buf.getvalue(),
            )
            check(
                "does not import aidev_tuios with a missing table",
                "aidev_tuios" not in sys.modules,
                sys.modules.get("aidev_tuios"),
            )

            print("read-only guarantee")

            def scrub(s):
                # the temp dir leaks into script/cwd args via the table path; it is not part of the command
                return s.replace(d + os.sep, "").replace(d, "")

            hits = [
                w
                for c in all_calls
                for w in FORBIDDEN
                if any(w in scrub(str(arg)) for arg in c)
            ]
            check(
                "no recorded call contains 'admin', 'write', 'fan' or 'respond'",
                hits == [],
                hits,
            )
    finally:
        if saved_mod is None:
            sys.modules.pop("aidev_tuios", None)
        else:
            sys.modules["aidev_tuios"] = saved_mod
        sys.path[:] = saved_path

    print(
        "\n"
        + ("all passed" if not FAILS else f"{len(FAILS)} failed: " + ", ".join(FAILS))
    )
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
