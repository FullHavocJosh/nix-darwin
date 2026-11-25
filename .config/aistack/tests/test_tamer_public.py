"""Tests for TAMER_PUBLIC_URL and tamer_public_key in aidev_lib.py: the public tamer endpoint is
https://llm.rollet.family/lumo/v1, and AISTACK_LUMO_PUBLIC_KEY wins over the gateway device key
that remote_builder.read_key() would return; any failure of that lookup falls through to ''.

Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_tamer_public.py
"""

import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(
    0, os.path.dirname(HERE)
)  # aidev_lib's "import remote_builder" resolves to ../remote_builder.py

os.environ.pop(
    "AISTACK_LUMO_PUBLIC_URL", None
)  # keep this run hermetic whatever the caller has set
os.environ.pop("AISTACK_LUMO_PUBLIC_KEY", None)


def load_aidev_lib():
    spec = importlib.util.spec_from_file_location(
        "aidev_lib", os.path.join(HERE, "..", "aidev_lib.py")
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


FAILS = []


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


aidev_lib = load_aidev_lib()

# TAMER_PUBLIC_URL: the default, then the AISTACK_LUMO_PUBLIC_URL override (trailing / stripped)
check(
    "default public url is llm.rollet.family/lumo/v1",
    aidev_lib.TAMER_PUBLIC_URL == "https://llm.rollet.family/lumo/v1",
    repr(aidev_lib.TAMER_PUBLIC_URL),
)
os.environ["AISTACK_LUMO_PUBLIC_URL"] = "https://override.test/v1/"
aidev_lib = load_aidev_lib()
check(
    "AISTACK_LUMO_PUBLIC_URL overrides the url",
    aidev_lib.TAMER_PUBLIC_URL == "https://override.test/v1",
    repr(aidev_lib.TAMER_PUBLIC_URL),
)
del os.environ["AISTACK_LUMO_PUBLIC_URL"]
aidev_lib = load_aidev_lib()

# tamer_public_key: AISTACK_LUMO_PUBLIC_KEY first, then remote_builder.read_key(), then ''
import remote_builder

real_read_key = remote_builder.read_key
remote_builder.read_key = lambda: "sk-device-key-test"
try:
    check(
        "no env key falls back to the device key",
        aidev_lib.tamer_public_key() == "sk-device-key-test",
    )
    os.environ["AISTACK_LUMO_PUBLIC_KEY"] = "sk-env-key-test"
    check(
        "AISTACK_LUMO_PUBLIC_KEY wins over the device key",
        aidev_lib.tamer_public_key() == "sk-env-key-test",
    )
    del os.environ["AISTACK_LUMO_PUBLIC_KEY"]

    def boom():
        raise RuntimeError("read_key failed")

    remote_builder.read_key = boom
    check(
        "a raising read_key falls through to ''",
        aidev_lib.tamer_public_key() == "",
    )
finally:
    remote_builder.read_key = real_read_key

# while remote_builder cannot even be imported, the same two rules still hold
saved_mod = sys.modules.pop("remote_builder", None)
saved_path = sys.path.pop(0)
try:
    try:
        got = aidev_lib.tamer_public_key()
        check("import failure falls through to ''", got == "", repr(got))
    except Exception as e:
        check("import failure falls through to ''", False, repr(e))
    os.environ["AISTACK_LUMO_PUBLIC_KEY"] = "sk-env-key-test"
    try:
        got = aidev_lib.tamer_public_key()
        check(
            "env key wins even when the import fails",
            got == "sk-env-key-test",
            repr(got),
        )
    except Exception as e:
        check("env key wins even when the import fails", False, repr(e))
    del os.environ["AISTACK_LUMO_PUBLIC_KEY"]
finally:
    sys.path.insert(0, saved_path)
    if saved_mod is not None:
        sys.modules["remote_builder"] = saved_mod

if FAILS:
    print(f"{len(FAILS)} failed")
    sys.exit(1)
print("all passed")
