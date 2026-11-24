#!/usr/bin/env python3
"""Test that verified tasks lose their guard when a new task goes to the same builder."""

import importlib.util
import os
import sys
import tempfile

# Set up the environment
os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
os.environ["AIDEV_TUIOS_WORKTREE_MODE"] = "none"
os.environ["AISTACK_WORKTREE_MODE"] = "none"
os.environ["AISTACK_DIR"] = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", "..", "aistack"))

# Load aidev_tuios
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(os.path.dirname(__file__), "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

def check(name, cond):
    """Record failures and print a summary."""
    if not cond:
        print(f"FAIL: {name}")
        return False
    return True

def test_guard_stale():
    """Test that verified tasks lose their guard when a new task goes to the same builder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up a mock run
        run = a.Run(tmpdir, "20260101-000001")
        run.data["session"] = "test"
        
        # Set up the test environment with stubbed functions
        def mock_load_lib(project, run_obj=None):
            class MockLib:
                def load_plan(self, project):
                    return ({'userStories': [{'id': 'T0', 'title': 'Test 0'}, {'id': 'T1', 'title': 'Test 1'}, {'id': 'T2', 'title': 'Test 2'}]}, 
                            {'T0': 'true', 'T1': 'true', 'T2': 'true'}, None)
            return MockLib()
        
        def mock_window_named(session, name):
            return True
            
        def mock_prepare_builder(run_obj, builder):
            return True
            
        def mock_mail_task(run_obj, builder, subject, mail_text, prompt):
            return "7"
            
        def mock_snapshot_work(run_obj, label):
            return None
            
        def mock_compaction_count(run_obj, builder):
            return 0
            
        def mock_overflow_count(run_obj, builder):
            return 0
            
        # Monkey patch the functions
        original_load_lib = a.load_lib
        original_window_named = a.window_named
        original_prepare_builder = a.prepare_builder
        original_mail_task = a.mail_task
        original_snapshot_work = a.snapshot_work
        original_compaction_count = a.compaction_count
        original_overflow_count = a.overflow_count
        
        a.load_lib = mock_load_lib
        a.window_named = mock_window_named
        a.prepare_builder = mock_prepare_builder
        a.mail_task = mock_mail_task
        a.snapshot_work = mock_snapshot_work
        a.compaction_count = mock_compaction_count
        a.overflow_count = mock_overflow_count
        
        # Set up the test tasks
        run.data["tasks"]["T1"] = {"status": "verified", "attempts": 1, "notes": [], "builder": "build-free-tier-3", "guard": {"offset": 0}}
        run.data["tasks"]["T0"] = {"status": "verified", "attempts": 1, "notes": [], "builder": "build-local-tier-0", "guard": {"offset": 0}}
        run.data["tasks"]["T2"] = {"status": "pending", "attempts": 0, "notes": []}
        
        # Test that the function works correctly
        try:
            # Call the send task function (this should trigger our fix)
            result = a.cmd_send_task(run, ["T2", "--to", "tier-3"])
            
            # Check if T1's guard was removed (it should be on the same builder)
            has_guard_t1 = "guard" in run.data["tasks"]["T1"]
            has_guard_t0 = "guard" in run.data["tasks"]["T0"]  # Should still have guard (different builder)
            
            # The checks
            success = True
            success = check("T1 verified on the same builder loses its guard", not has_guard_t1) and success
            success = check("T0 on another builder keeps its guard", has_guard_t0) and success
            success = check("T2 gets a fresh guard", "guard" in run.data["tasks"]["T2"]) and success
            
            # Restore original functions
            a.load_lib = original_load_lib
            a.window_named = original_window_named
            a.prepare_builder = original_prepare_builder
            a.mail_task = original_mail_task
            a.snapshot_work = original_snapshot_work
            a.compaction_count = original_compaction_count
            a.overflow_count = original_overflow_count
            
            if success:
                print("All tests passed!")
                return 0
            else:
                print("Some tests failed!")
                return 1
                
        except Exception as e:
            # Restore original functions
            a.load_lib = original_load_lib
            a.window_named = original_window_named
            a.prepare_builder = original_prepare_builder
            a.mail_task = original_mail_task
            a.snapshot_work = original_snapshot_work
            a.compaction_count = original_compaction_count
            a.overflow_count = original_overflow_count
            print(f"Test failed with exception: {e}")
            return 1

    # Test for the new behavior: guard poll skipped when task is queued
    def mock_guard_poll(run_obj, builder, tid):
        if not hasattr(mock_guard_poll, 'polled'):
            mock_guard_poll.polled = []
        mock_guard_poll.polled.append(tid)
        
    # Set up the test tasks
    run.data["tasks"] = {}
    run.data["tasks"]["T1"] = {"status": "verified", "attempts": 1, "notes": [], "builder": "build-free-tier-3", "guard": {"offset": 0}}
    run.data["tasks"]["T2"] = {"status": "sent", "attempts": 1, "notes": [], "builder": "build-free-tier-3"}
    
    # Stub functions
    a.window_named = mock_window_named
    a.agent_state = lambda session, name: "working"
    a.guard_poll = mock_guard_poll
    
    # Run reap_pass
    tracker = a.aidev_guard.RestTracker()
    a.reap_pass(run, tracker)
    
    # Check that no verified-task guard poll occurred while T2 is queued
    success = check("no verified-task guard poll while T2 is queued", getattr(mock_guard_poll, 'polled', []) == []) and success
    
    # Reset the polled list
    mock_guard_poll.polled = []
    
    # Now set T2 to verified and give T1 its guard back
    run.data["tasks"]["T2"] = {"status": "verified", "attempts": 1, "notes": [], "builder": "build-free-tier-3"}
    run.data["tasks"]["T1"] = {"status": "verified", "attempts": 1, "notes": [], "builder": "build-free-tier-3", "guard": {"offset": 0}}
    
    # Run reap_pass again
    a.reap_pass(run, tracker)
    
    # Check that the verified task IS polled when nothing is queued
    success = check("the verified task is polled when nothing is queued", getattr(mock_guard_poll, 'polled', []) == ["T1"]) and success
    
    # Restore original functions
    a.load_lib = original_load_lib
    a.window_named = original_window_named
    a.prepare_builder = original_prepare_builder
    a.mail_task = original_mail_task
    a.snapshot_work = original_snapshot_work
    a.compaction_count = original_compaction_count
    a.overflow_count = original_overflow_count
    
    if success:
        print("All tests passed!")
        return 0
    else:
        print("Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(test_guard_stale())