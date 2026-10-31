"""Test explore.py ground function: verify citations against files."""

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "explore", os.path.join(HERE, "..", "explore.py")
)
explore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(explore)

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


with tempfile.TemporaryDirectory() as root:
    # Create a 3-line file f.txt
    with open(os.path.join(root, "f.txt"), "w") as f:
        f.write("line1\nline2\nline3\n")
    
    # Test 1: ground('see f.txt:2', d) is unchanged
    result = explore.ground('see f.txt:2', root)
    check("f.txt:2 unchanged", result == 'see f.txt:2', result)
    
    # Test 2: ground('see f.txt:9', d) ends with 'f.txt:9' and contains 'UNVERIFIED'
    result = explore.ground('see f.txt:9', root)
    check("f.txt:9 contains UNVERIFIED", 'UNVERIFIED' in result, result)
    check("f.txt:9 ends with f.txt:9", result.endswith('f.txt:9'), result)
    
    # Test 3: ground('see nope.txt:9', d) is unchanged
    result = explore.ground('see nope.txt:9', root)
    check("nope.txt:9 unchanged", result == 'see nope.txt:9', result)

    # Test 4: binary file does not raise and leaves answer unchanged
    with open(os.path.join(root, "b.bin"), "wb") as f:
        f.write(b'\xff\xfe\x00')
    try:
        result = explore.ground('see b.bin:1', root)
    except Exception as e:
        result = repr(e)
    check("b.bin:1 unchanged", result == 'see b.bin:1', result)

sys.exit(1 if FAILS else 0)