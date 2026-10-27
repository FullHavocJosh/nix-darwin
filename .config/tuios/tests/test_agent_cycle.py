"""
Run: python3 .config/tuios/tests/test_agent_cycle.py
"""

import importlib.util
import json
import sys
from pathlib import Path


# Helper to check test conditions
def check(name, cond):
    if cond:
        print(f"PASS: {name}")
    else:
        print(f"FAIL: {name}")
        return 1
    return 0

def test_order_agents():
    """Test order_agents function."""
    # Load the module
    spec = importlib.util.spec_from_file_location("agent_cycle", Path(__file__).parent.parent / "agent_cycle.py")
    agent_cycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_cycle)

    # Test data with various scenarios
    agents = [
        {"session": "session2", "workspace": 1, "name": "agent1", "window_id": "window3"},
        {"session": "session1", "workspace": 2, "name": "agent2", "window_id": "window2"},
        {"session": "session1", "workspace": 1, "name": "agent1", "window_id": "window1"},
        {"session": "session1", "workspace": 0, "name": "agent3", "window_id": "window4"},
        {"session": "session2", "workspace": 2, "name": "agent2", "window_id": "window5"},
        {"session": "session2", "name": "agent3", "window_id": "window6"},  # Missing workspace
    ]

    expected_order = [
        {"session": "session1", "workspace": 0, "name": "agent3", "window_id": "window4"},
        {"session": "session1", "workspace": 1, "name": "agent1", "window_id": "window1"},
        {"session": "session1", "workspace": 2, "name": "agent2", "window_id": "window2"},
        {"session": "session2", "name": "agent3", "window_id": "window6"},  # Missing workspace
        {"session": "session2", "workspace": 1, "name": "agent1", "window_id": "window3"},
        {"session": "session2", "workspace": 2, "name": "agent2", "window_id": "window5"},
    ]

    result = agent_cycle.order_agents(agents)
    failures = 0
    failures += check("order_agents sorts correctly", result == expected_order)

    return failures

def test_find_current():
    """Test find_current function."""
    spec = importlib.util.spec_from_file_location("agent_cycle", Path(__file__).parent.parent / "agent_cycle.py")
    agent_cycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_cycle)

    agents = [
        {"session": "session1", "name": "agent1", "window_id": "window1"},
        {"session": "session1", "name": "agent2", "window_id": "window2"},
        {"session": "session1", "name": "agent3", "window_id": "window3"},
    ]

    failures = 0
    failures += check("find_current with exact match", agent_cycle.find_current(agents, "window2") == 1)
    failures += check("find_current with prefix match", agent_cycle.find_current(agents, "windo") == 0)
    failures += check("find_current no match", agent_cycle.find_current(agents, "window4") == -1)
    failures += check("find_current empty current_id", agent_cycle.find_current(agents, "") == -1)
    return failures

def test_pick():
    """Test pick function."""
    spec = importlib.util.spec_from_file_location("agent_cycle", Path(__file__).parent.parent / "agent_cycle.py")
    agent_cycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_cycle)

    agents = [
        {"session": "session1", "name": "agent1", "window_id": "window1"},
        {"session": "session2", "name": "agent2", "window_id": "window2"},
        {"session": "session3", "name": "agent3", "window_id": "window3"},
    ]

    failures = 0
    # Test picking next from middle
    failures += check("pick next from middle", agent_cycle.pick(agents, "window1", "next") == agents[1])
    # Test picking prev from middle
    failures += check("pick prev from middle", agent_cycle.pick(agents, "window2", "prev") == agents[0])
    # Test wrapping at end (next)
    failures += check("pick next wraps", agent_cycle.pick(agents, "window3", "next") == agents[0])
    # Test wrapping at start (prev)
    failures += check("pick prev wraps", agent_cycle.pick(agents, "window1", "prev") == agents[2])
    # Test current not found
    failures += check("pick next when not found", agent_cycle.pick(agents, "window4", "next") == agents[0])
    failures += check("pick prev when not found", agent_cycle.pick(agents, "window4", "prev") == agents[2])
    # Test empty list
    failures += check("pick from empty list", agent_cycle.pick([], "window1", "next") is None)
    # Test single agent that is current
    single_agents = [{"session": "session1", "name": "agent1", "window_id": "window1"}]
    failures += check("pick single agent is current", agent_cycle.pick(single_agents, "window1", "next") is None)
    # Test prefix matching
    agents_with_prefix = [
        {"session": "session1", "name": "agent1", "window_id": "window123"},
        {"session": "session1", "name": "agent2", "window_id": "window234"},
    ]
    failures += check(
        "pick with prefix match",
        agent_cycle.pick(agents_with_prefix, "window1", "next") == agents_with_prefix[1],
    )

    return failures

def test_main_bad_args():
    """Test main with bad arguments."""
    spec = importlib.util.spec_from_file_location("agent_cycle", Path(__file__).parent.parent / "agent_cycle.py")
    agent_cycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_cycle)

    # Test with bad arguments
    failures = 0
    # Capture stderr
    old_stderr = sys.stderr
    import io
    stderr_capture = io.StringIO()
    sys.stderr = stderr_capture

    # Test 1: No arguments
    result = agent_cycle.main([])
    failures += check("main with no args returns 2", result == 2)

    # Test 2: Wrong argument
    result = agent_cycle.main(["agent_cycle.py", "wrong"])
    failures += check("main with wrong arg returns 2", result == 2)

    # Restore stderr
    sys.stderr = old_stderr

    return failures

def test_main_list_agents_fail():
    """Test main when list-agents fails."""
    spec = importlib.util.spec_from_file_location("agent_cycle", Path(__file__).parent.parent / "agent_cycle.py")
    agent_cycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_cycle)

    calls = []

    def fake_run(argv, **kwargs):
        calls.append(argv)

        class Result:
            def __init__(self):
                self.returncode = 1
                self.stdout = ""
                self.stderr = "error from list-agents"
        return Result()

    # Test with fake run that fails
    failures = 0
    old_stderr = sys.stderr
    import io
    stderr_capture = io.StringIO()
    sys.stderr = stderr_capture

    result = agent_cycle.main(["agent_cycle.py", "next"], run=fake_run)
    failures += check("main with list-agents failure returns 1", result == 1)
    failures += check(
        "main with list-agents failure calls nothing else",
        calls == [["tuios", "list-agents", "--all-sessions", "--json"]],
    )

    # Restore stderr
    sys.stderr = old_stderr

    return failures

def test_main_same_session():
    """Test main in same session."""
    spec = importlib.util.spec_from_file_location("agent_cycle", Path(__file__).parent.parent / "agent_cycle.py")
    agent_cycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_cycle)

    # Test with same session
    def make_run(agents_json):
        calls = []
        def fake_run(argv, **kwargs):
            calls.append(argv)
            class Result:
                def __init__(self):
                    if argv[1] == "list-agents":
                        self.returncode = 0
                        self.stdout = json.dumps(agents_json)
                        self.stderr = ""
                    else:
                        self.returncode = 0
                        self.stdout = ""
                        self.stderr = ""
            return Result()
        return fake_run, calls

    agents_json = {
        "agents": [
            {"session": "session1", "name": "agent1", "window_id": "window1"},
            {"session": "session1", "name": "agent2", "window_id": "window2"},
        ]
    }

    fake_run, calls = make_run(agents_json)
    env = {"TUIOS_ACTIVE_PANE_ID": "window1", "TUIOS_SESSION": "session1"}
    result = agent_cycle.main(["agent_cycle.py", "next"], run=fake_run, env=env)
    failures = 0
    failures += check("main same session returns 0", result == 0)
    # Check that only the focus-window call was made (after the list-agents call)
    expected_calls = [["tuios", "focus-window", "-s", "session1", "window2"]]
    failures += check("main same session calls correct commands", calls[1:] == expected_calls)

    return failures

def test_main_cross_session():
    """Test main across sessions."""
    spec = importlib.util.spec_from_file_location("agent_cycle", Path(__file__).parent.parent / "agent_cycle.py")
    agent_cycle = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent_cycle)

    # Test with cross-session
    def make_run(agents_json):
        calls = []
        def fake_run(argv, **kwargs):
            calls.append(argv)
            class Result:
                def __init__(self):
                    if argv[1] == "list-agents":
                        self.returncode = 0
                        self.stdout = json.dumps(agents_json)
                        self.stderr = ""
                    else:
                        self.returncode = 0
                        self.stdout = ""
                        self.stderr = ""
            return Result()
        return fake_run, calls

    agents_json = {
        "agents": [
            {"session": "session1", "name": "agent1", "window_id": "window1"},
            {"session": "session2", "name": "agent2", "window_id": "window2"},
        ]
    }

    fake_run, calls = make_run(agents_json)
    env = {"TUIOS_ACTIVE_PANE_ID": "window1", "TUIOS_SESSION": "session1"}
    result = agent_cycle.main(["agent_cycle.py", "next"], run=fake_run, env=env)
    failures = 0
    failures += check("main cross session returns 0", result == 0)
    # Check that switch-session then focus-window were called
    expected_calls = [
        ["tuios", "switch-session", "session2"],
        ["tuios", "focus-window", "-s", "session2", "window2"]
    ]
    failures += check("main cross session calls correct commands", calls[1:] == expected_calls)

    return failures

def main():
    failures = 0
    failures += test_order_agents()
    failures += test_find_current()
    failures += test_pick()
    failures += test_main_bad_args()
    failures += test_main_list_agents_fail()
    failures += test_main_same_session()
    failures += test_main_cross_session()

    if failures > 0:
        print(f"\n{failures} test(s) failed")
        return 1
    else:
        print("\nAll tests passed")
        return 0

if __name__ == "__main__":
    sys.exit(main())