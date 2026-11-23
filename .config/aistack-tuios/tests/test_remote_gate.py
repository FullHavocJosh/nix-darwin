"""Tests for aidev's local builder gate (aidev_tuios.py local_builder_available): the model file or a remote
llama-server env makes the local builder available. Needs no tuios daemon, no model and no network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_remote_gate.py
"""
import importlib.util
import os
import sys
import tempfile

os.environ["AISTACK_ZEN_KEY"] = "1"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ["AISTACK_DIR"] = os.path.join(os.path.dirname(ROOT), "aistack")  # this checkout's zen_models.py
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
    for var in ("AIDEV_TUIOS_SESSION", "AIDEV_TUIOS_RUN", "AIDEV_TUIOS_PROJECT", "AIDEV_TUIOS_BUILDER"):
        os.environ.pop(var, None)
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-home-"))
    os.environ["AIDEV_TUIOS_HOME"] = tmp
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))
    model = os.path.join(tmp, "model.gguf")

    print("local builder gate")
    a.CODER_FILE = os.path.join(tmp, "missing.gguf")
    for var in ("AIDEV_REMOTE_BUILDER_URL", "AIDEV_REMOTE_BUILDER_KEY_FILE"):
        os.environ.pop(var, None)
    check("no model file, no env: unavailable", not a.local_builder_available())

    os.environ["AIDEV_REMOTE_BUILDER_URL"] = "http://g14:8080"
    check("no model file, only url: unavailable", not a.local_builder_available())
    os.environ["AIDEV_REMOTE_BUILDER_KEY_FILE"] = os.path.join(tmp, "key")
    # Stub the remote builder probe for this test case
    original_load_remote_builder = a.load_remote_builder
    class FakeRemoteBuilder:
        @staticmethod
        def configured():
            return True
        @staticmethod
        def probe():
            return (True, "")
    a.load_remote_builder = FakeRemoteBuilder
    check("no model file, both env vars: available", a.local_builder_available())
    # Restore original
    a.load_remote_builder = original_load_remote_builder

    for var in ("AIDEV_REMOTE_BUILDER_URL", "AIDEV_REMOTE_BUILDER_KEY_FILE"):
        os.environ.pop(var, None)
    with open(model, "w") as f:
        f.write("x")
    a.CODER_FILE = model
    # Test with 64GB RAM
    os.environ["AIDEV_HOST_RAM_GB"] = "64"
    check("model file, env unset: available", a.local_builder_available())

    # Test various RAM scenarios
    a.CODER_FILE = model
    os.environ["AIDEV_HOST_RAM_GB"] = "16"
    reason = a.local_skip_reason()
    check("file present with AIDEV_HOST_RAM_GB=16 is unavailable", "host has 16 GB, needs 24 GB" in reason)
    
    # Test with 64GB RAM and file present
    os.environ["AIDEV_HOST_RAM_GB"] = "64"
    reason = a.local_skip_reason()
    check("file present at 64 is available", reason is None)
    
    # Test with no file but 64GB RAM
    a.CODER_FILE = os.path.join(tmp, "missing.gguf")
    os.environ["AIDEV_HOST_RAM_GB"] = "64"
    reason = a.local_skip_reason()
    check("no file at 64 GB: reason contains the file path", "missing.gguf" in reason)

    print()
    print("FAILED: " + ", ".join(FAILS) if FAILS else "all passed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
