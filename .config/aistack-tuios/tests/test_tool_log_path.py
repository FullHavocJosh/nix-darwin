#!/usr/bin/env python3
"""Test tool log path functionality."""

import importlib.util
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(SRC, "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = []


def check(name, cond, extra=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name}" + (f" ({extra})" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)



def main():
    # Test 1: PI_BUILD_EXTENSIONS contains pi-tool-log.ts
    check("PI_BUILD_EXTENSIONS contains pi-tool-log.ts", "pi-tool-log.ts" in a.PI_BUILD_EXTENSIONS)
    
    # Test 2: tool_log_path function works correctly
    run = types.SimpleNamespace(dir='/r')
    result = a.tool_log_path(run, 'p')
    expected = '/r/toollog/p.jsonl'
    check("tool_log_path function works correctly", result == expected, f"expected {expected}, got {result}")
    
    # Test 3: write_build_pi copies pi-tool-log.ts into the extensions dir
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test directory structure
        cfg = {
            'pi_build': os.path.join(tmpdir, 'pi_build')
        }
        os.makedirs(cfg['pi_build'], exist_ok=True)
        
        # Call write_build_pi
        a.write_build_pi(cfg, 'tier-0')
        
        # Check if pi-tool-log.ts was copied
        ext_dir = os.path.join(cfg['pi_build'], 'extensions')
        tool_log_path = os.path.join(ext_dir, 'pi-tool-log.ts')
        check("write_build_pi copies pi-tool-log.ts into the extensions dir", os.path.exists(tool_log_path))
    
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())