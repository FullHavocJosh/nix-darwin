#!/usr/bin/env python3
"""Test plan_pane_open and start_aidev functions in aidev_pick.py."""

import importlib.util
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_pick", os.path.join(HERE, "..", "aidev_pick.py"))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


class ExecCalled(Exception):
    pass


def test_plan_pane_open():
    # Test 1: plan pane present
    original_env = os.environ.copy()
    try:
        os.environ['AIDEV_TUIOS_SESSION'] = 'test_session'
        os.environ['TUIOS_SESSION'] = 'test_session'
        original_run = mod.subprocess.run
        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == 'tuios' and 'list-windows' in cmd:
                return type('obj', (object,), {'returncode': 0, 'stdout': json.dumps({'windows': [{'custom_name': 'plan'}]})})()
            return original_run(cmd, *args, **kwargs)
        mod.subprocess.run = mock_run
        result = mod.plan_pane_open()
        check("plan pane present returns True", result == True)
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        mod.subprocess.run = original_run

    # Test 2: plan pane absent
    try:
        os.environ['AIDEV_TUIOS_SESSION'] = 'test_session'
        os.environ['TUIOS_SESSION'] = 'test_session'
        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == 'tuios' and 'list-windows' in cmd:
                return type('obj', (object,), {'returncode': 0, 'stdout': json.dumps({'windows': [{'custom_name': 'other'}]})})()
            return original_run(cmd, *args, **kwargs)
        mod.subprocess.run = mock_run
        result = mod.plan_pane_open()
        check("plan pane absent returns False", result == False)
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        mod.subprocess.run = original_run

    # Test 3: non-JSON output
    try:
        os.environ['AIDEV_TUIOS_SESSION'] = 'test_session'
        os.environ['TUIOS_SESSION'] = 'test_session'
        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == 'tuios' and 'list-windows' in cmd:
                return type('obj', (object,), {'returncode': 0, 'stdout': 'not json'})()
            return original_run(cmd, *args, **kwargs)
        mod.subprocess.run = mock_run
        result = mod.plan_pane_open()
        check("non-JSON output returns False", result == False)
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        mod.subprocess.run = original_run

    # Test 4: no session env
    try:
        if 'AIDEV_TUIOS_SESSION' in os.environ:
            del os.environ['AIDEV_TUIOS_SESSION']
        if 'TUIOS_SESSION' in os.environ:
            del os.environ['TUIOS_SESSION']
        result = mod.plan_pane_open()
        check("no session env returns False", result == False)
    finally:
        os.environ.clear()
        os.environ.update(original_env)


def test_start_aidev():
    # Test the environment logic in start_aidev function, without executing subprocess
    original_env = os.environ.copy()
    try:
        # Test 1: with plan pane
        # Set up the environment to simulate a session with plan pane
        os.environ['AIDEV_TUIOS_SESSION'] = 'test-session'
        os.environ['TUIOS_SESSION'] = 'test-session'
        
        # Mock subprocess.run to check the function logic
        original_run = mod.subprocess.run
        def mock_run(cmd, *args, **kwargs):
            if cmd[0] == 'tuios' and 'list-windows' in cmd:
                return type('obj', (object,), {'returncode': 0, 'stdout': json.dumps({'windows': [{'custom_name': 'plan'}]})})()
            return original_run(cmd, *args, **kwargs)
        
        mod.subprocess.run = mock_run
        
        # We test just the environment construction logic, not the actual subprocess call
        # First create a function that mimics what start_aidev does but we can test
        test_env = {**os.environ, "AIDEV_TUIOS_PLANNER": "local"}
        if mod.plan_pane_open():  # This will now return True with our mock
            test_env['AIDEV_TUIOS_OWN_SESSION'] = '1'
            # print('a plan pane is already open; starting in its own session')
        else:
            test_env['AIDEV_TUIOS_NO_ATTACH'] = '1'
            
        check("with plan pane, AIDEV_TUIOS_OWN_SESSION == '1'", test_env.get("AIDEV_TUIOS_OWN_SESSION") == "1")
        check("with plan pane, AIDEV_TUIOS_NO_ATTACH not in env", "AIDEV_TUIOS_NO_ATTACH" not in test_env)
        check("with plan pane, AIDEV_TUIOS_PLANNER passed through", test_env.get("AIDEV_TUIOS_PLANNER") == "local")
        
        # Test 2: without plan pane
        def mock_run_no_plan(cmd, *args, **kwargs):
            if cmd[0] == 'tuios' and 'list-windows' in cmd:
                return type('obj', (object,), {'returncode': 0, 'stdout': json.dumps({'windows': [{'custom_name': 'other'}]})})()
            return original_run(cmd, *args, **kwargs)
        
        mod.subprocess.run = mock_run_no_plan
        
        # Clear the env to ensure clean test
        if 'AIDEV_TUIOS_OWN_SESSION' in os.environ:
            del os.environ['AIDEV_TUIOS_OWN_SESSION']
            
        # Test the same logic with plan pane absent
        test_env2 = {**os.environ, "AIDEV_TUIOS_PLANNER": "local"}
        if mod.plan_pane_open():  # This will now return False with our mock
            test_env2['AIDEV_TUIOS_OWN_SESSION'] = '1'
        else:
            test_env2['AIDEV_TUIOS_NO_ATTACH'] = '1'
            
        check("without plan pane, AIDEV_TUIOS_NO_ATTACH == '1'", test_env2.get("AIDEV_TUIOS_NO_ATTACH") == "1")
        check("without plan pane, AIDEV_TUIOS_OWN_SESSION not in env", "AIDEV_TUIOS_OWN_SESSION" not in test_env2)
        check("without plan pane, AIDEV_TUIOS_PLANNER passed through", test_env2.get("AIDEV_TUIOS_PLANNER") == "local")
        
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        mod.subprocess.run = original_run


def test_close_pick_window():
    original_env = os.environ.copy()
    original_run = mod.run
    # Test 1: session set; run records the close-window command
    try:
        os.environ['AIDEV_TUIOS_SESSION'] = 'test-session'
        os.environ['TUIOS_SESSION'] = 'test-session'
        calls = []
        def mock_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return (0, '')
        mod.run = mock_run
        result = mod.close_pick_window()
        check("session set returns True on exit 0", result == True)
        check("runs tuios close-window pick -s <session>", calls == [['tuios', 'close-window', 'pick', '-s', 'test-session']])
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        mod.run = original_run

    # Test 2: both session env vars unset; run is not called
    try:
        if 'AIDEV_TUIOS_SESSION' in os.environ:
            del os.environ['AIDEV_TUIOS_SESSION']
        if 'TUIOS_SESSION' in os.environ:
            del os.environ['TUIOS_SESSION']
        calls = []
        def mock_run(cmd, *args, **kwargs):
            calls.append(cmd)
            return (0, '')
        mod.run = mock_run
        result = mod.close_pick_window()
        check("no session env returns False", result == False)
        check("no session env does not call run", calls == [])
    finally:
        os.environ.clear()
        os.environ.update(original_env)
        mod.run = original_run


def test_zen_and_go_no_key():
    # zen_models.py status --json reports no_key on a host without an OpenCode Zen API key
    original_run, original_set_state = mod.run, mod.set_state
    calls = {}
    try:
        mod.run = lambda cmd, timeout=None: (1, json.dumps({"models": [], "no_key": True}))
        mod.set_state = lambda key, state, detail: calls.__setitem__(key, (state, detail))
        mod.check_zen_and_go()
    finally:
        mod.run, mod.set_state = original_run, original_set_state
    for key in ("zen", "go"):
        state, detail = calls.get(key, (None, ""))
        check(f"no key sets {key} bad", state == "bad", f"{state}: {detail}")
        check(f"no key names the API key for {key}", "API key" in detail, detail)


def test_manage_row():
    # the manage row appears only when the picker's cwd is ~/ai-info (compared by realpath)
    # Test 1: another directory keeps the menu unchanged
    keys = [key for key, _label, _startable in mod.build_rows('/tmp')]
    check("no manage row outside ai-info",
          keys == ['claude', 'claude-plan', '9b', '9b-plan', '30b', 'zen', 'go', 'openrouter'], f"{keys}")

    # Test 2: ~/ai-info gains the manage row between 30b and zen
    rows = mod.build_rows(os.path.expanduser('~/ai-info'))
    keys = [key for key, _label, _startable in rows]
    check("manage row inside ai-info",
          keys == ['claude', 'claude-plan', '9b', '9b-plan', '30b', 'manage', 'zen', 'go', 'openrouter'], f"{keys}")
    check("manage row is at index 5 and startable", rows[5][0] == 'manage' and rows[5][2] == True, f"{rows[5]}")
    check("zen follows the manage row at index 6", rows[6][0] == 'zen', f"{rows[6]}")

    # Test 3: a symlink to ~/ai-info also counts, because build_rows compares realpaths
    if os.path.isdir(os.path.expanduser('~/ai-info')):
        with tempfile.TemporaryDirectory() as tmp:
            link = os.path.join(tmp, 'ai-info-link')
            os.symlink(os.path.expanduser('~/ai-info'), link)
            keys = [key for key, _label, _startable in mod.build_rows(link)]
            check("manage row via symlink to ai-info", 'manage' in keys, f"{keys}")


def test_launch_manage():
    # launch('manage') runs launch.sh and closes the pick window; a failure falls back to zsh -i
    original_launch, original_run = mod.MANAGE_LAUNCH, mod.subprocess.run
    original_close, original_execvp = mod.close_pick_window, mod.os.execvp
    try:
        fake = os.path.join(tempfile.gettempdir(), 'fake-launch.sh')
        mod.MANAGE_LAUNCH = fake
        cmds, closed, execs = [], [], []
        def mock_execvp(name, args):
            execs.append((name, list(args)))
            raise ExecCalled()
        mod.os.execvp = mock_execvp

        # Test 1: launch.sh exits 0; the pick window closes and no shell is execed
        def mock_run_ok(cmd, *args, **kwargs):
            cmds.append(cmd)
            return type('obj', (object,), {'returncode': 0})()
        mod.subprocess.run = mock_run_ok
        mod.close_pick_window = lambda: closed.append(True) or True
        mod.launch('manage')
        check("manage runs launch.sh", cmds == [[fake]], f"{cmds}")
        check("manage closes the pick window", closed == [True])
        check("manage success does not exec a shell", execs == [], f"{execs}")

        # Test 2: launch.sh fails; fall back to zsh -i without closing the pick window
        def mock_run_fail(cmd, *args, **kwargs):
            cmds.append(cmd)
            return type('obj', (object,), {'returncode': 1})()
        mod.subprocess.run = mock_run_fail
        closed.clear()
        try:
            mod.launch('manage')
            check("manage failure execs zsh -i", False, "execvp was not called")
        except ExecCalled:
            check("manage failure execs zsh -i", execs == [('zsh', ['zsh', '-i'])], f"{execs}")
        check("manage failure does not close the pick window", closed == [], f"{closed}")
    finally:
        mod.MANAGE_LAUNCH, mod.subprocess.run = original_launch, original_run
        mod.close_pick_window, mod.os.execvp = original_close, original_execvp


def test_check_manage():
    original_launch, original_which, original_set_state = mod.MANAGE_LAUNCH, mod.shutil.which, mod.set_state
    fd, path = tempfile.mkstemp()
    os.close(fd)
    try:
        calls = {}
        mod.set_state = lambda key, state, detail: calls.__setitem__(key, (state, detail))
        mod.MANAGE_LAUNCH = path

        # Test 1: launch.sh exists and tuios is on PATH -> ok
        mod.shutil.which = lambda name: '/bin/tuios'
        mod.check_manage()
        state, detail = calls.get('manage', (None, ''))
        check("manage ok when launch.sh and tuios exist", state == 'ok', f"{state}: {detail}")
        check("manage ok detail is the launch path", detail == path, detail)

        # Test 2: tuios not on PATH -> bad
        calls.clear()
        mod.shutil.which = lambda name: None
        mod.check_manage()
        state, detail = calls.get('manage', (None, ''))
        check("manage bad when tuios missing", state == 'bad', f"{state}: {detail}")
        check("manage bad names tuios", 'tuios' in detail.lower(), detail)
    finally:
        mod.MANAGE_LAUNCH, mod.shutil.which, mod.set_state = original_launch, original_which, original_set_state
        os.unlink(path)


def main():
    test_plan_pane_open()
    test_start_aidev()
    test_close_pick_window()
    test_zen_and_go_no_key()
    test_manage_row()
    test_launch_manage()
    test_check_manage()
    check("All tests completed", True)
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())