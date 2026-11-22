"""Tests for aidev's probe_gateway retry logic (aidev_tuios.py probe_gateway): the function retries once on 502, 503, 504, or curl failure.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_probe_retry.py
"""
import importlib.util
import os
import sys
import tempfile

os.environ["AISTACK_ZEN_KEY"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    for var in ("AIDEV_TUIOS_SESSION", "AIDEV_TUIOS_RUN", "AIDEV_TUIOS_PROJECT", "AIDEV_TUIOS_BUILDER",
                "AIDEV_SEMI_LOCAL", "AIDEV_SEMI_LOCAL_URL", "AIDEV_REMOTE_BUILDER_KEY_FILE"):
        os.environ.pop(var, None)
    
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_HOME"] = tmp
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))
    
    # Create a temporary key file
    secret = "test-key"
    key_file = os.path.join(tmp, "api-key")
    with open(os.open(key_file, os.O_WRONLY | os.O_CREAT, 0o600), "w") as f:
        f.write(secret)
    
    # Create a mock server URL
    url = "http://127.0.0.1:12345/v1"
    
    class Done:
        def __init__(self, returncode, stdout):
            self.returncode, self.stdout = returncode, stdout

    def stub(results, calls):
        """Create a stub that returns results from a queue"""
        def run(cmd, *args, **kwargs):
            calls.append((cmd, kwargs))
            if not results:
                raise AssertionError("no more results in stub")
            result = results.pop(0)
            if isinstance(result, BaseException):
                raise result
            return result
        return run

    # Test case 1: 503 then 200 with the alias gives True and two calls and one sleep of 1.0
    print("Test 1: 503 then 200")
    calls = []
    results = [Done(0, '{"data":[{"id":"qwen3.5-9b"}]}\n503'), Done(0, '{"data":[{"id":"qwen3.5-9b"}]}\n200')]
    a.subprocess.run = stub(results, calls)
    sleep_calls = []
    a.time.sleep = lambda t: sleep_calls.append(t)
    
    try:
        result = a.probe_gateway(url, "qwen3.5-9b", key_file)
        check("should succeed with 503 then 200", result is True)
        check("should make two calls", len(calls) == 2)
        check("should sleep once for 1.0s", len(sleep_calls) == 1 and sleep_calls[0] == 1.0)
        # Check that the curl command was formed correctly
        cmd1 = calls[0][0]
        cmd2 = calls[1][0]
        # Check that the curl command was formed correctly (the 9th element is the URL)
        # The actual URL is in position 8 (index 8) which is the last positional argument
        check("first call is curl command with proper URL", cmd1[8] == url.rstrip('/') + "/models")
        check("second call is curl command with proper URL", cmd2[8] == url.rstrip('/') + "/models")
    finally:
        a.subprocess.run = a.subprocess.run
        a.time.sleep = a.time.sleep

    # Test case 2: 503 twice gives False and two calls
    print("Test 2: 503 twice")
    calls = []
    results = [Done(0, '{"data":[{"id":"qwen3.5-9b"}]}\n503'), Done(0, '{"data":[{"id":"qwen3.5-9b"}]}\n503')]
    a.subprocess.run = stub(results, calls)
    sleep_calls = []
    a.time.sleep = lambda t: sleep_calls.append(t)
    
    try:
        result = a.probe_gateway(url, "qwen3.5-9b", key_file)
        check("should fail with 503 twice", result is False)
        check("should make two calls", len(calls) == 2)
        check("should sleep once for 1.0s", len(sleep_calls) == 1 and sleep_calls[0] == 1.0)
    finally:
        a.subprocess.run = a.subprocess.run
        a.time.sleep = a.time.sleep

    # Test case 3: 200 first gives True and one call, no sleep
    print("Test 3: 200 first")
    calls = []
    results = [Done(0, '{"data":[{"id":"qwen3.5-9b"}]}\n200')]
    a.subprocess.run = stub(results, calls)
    sleep_calls = []
    a.time.sleep = lambda t: sleep_calls.append(t)
    
    try:
        result = a.probe_gateway(url, "qwen3.5-9b", key_file)
        check("should succeed with 200 first", result is True)
        check("should make one call", len(calls) == 1)
        check("should not sleep", len(sleep_calls) == 0)
    finally:
        a.subprocess.run = a.subprocess.run
        a.time.sleep = a.time.sleep

    # Test case 4: curl returncode 7 then 200 gives True
    print("Test 4: curl returncode 7 then 200")
    calls = []
    results = [Done(7, ""), Done(0, '{"data":[{"id":"qwen3.5-9b"}]}\n200')]
    a.subprocess.run = stub(results, calls)
    sleep_calls = []
    a.time.sleep = lambda t: sleep_calls.append(t)
    
    try:
        result = a.probe_gateway(url, "qwen3.5-9b", key_file)
        check("should succeed with curl failure then 200", result is True)
        check("should make two calls", len(calls) == 2)
        check("should sleep once for 1.0s", len(sleep_calls) == 1 and sleep_calls[0] == 1.0)
    finally:
        a.subprocess.run = a.subprocess.run
        a.time.sleep = a.time.sleep

    # Test case 5: 401 gives False and one call
    print("Test 5: 401")
    calls = []
    results = [Done(0, '{"data":[{"id":"qwen3.5-9b"}]}\n401')]
    a.subprocess.run = stub(results, calls)
    sleep_calls = []
    a.time.sleep = lambda t: sleep_calls.append(t)
    
    try:
        result = a.probe_gateway(url, "qwen3.5-9b", key_file)
        check("should fail with 401", result is False)
        check("should make one call", len(calls) == 1)
        check("should not sleep", len(sleep_calls) == 0)
    finally:
        a.subprocess.run = a.subprocess.run
        a.time.sleep = a.time.sleep

    print()
    print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())