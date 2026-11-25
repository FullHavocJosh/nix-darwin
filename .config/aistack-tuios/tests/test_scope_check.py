#!/usr/bin/env python3
import os
import subprocess
import sys
import tempfile

# Setup import path like other tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import aidev_tuios


def main():
    # Create a temp directory
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(['git', '-c', 'user.email=test@example.com', '-c', 'user.name=Test User', 'config', 'user.email', 'test@example.com'], cwd=tmpdir, check=True)
        subprocess.run(['git', '-c', 'user.email=test@example.com', '-c', 'user.name=Test User', 'config', 'user.name', 'Test User'], cwd=tmpdir, check=True)
        
        # Create initial files
        with open(os.path.join(tmpdir, 'a.txt'), 'w') as f:
            f.write('content a')
        with open(os.path.join(tmpdir, 'b.txt'), 'w') as f:
            f.write('content b')
        with open(os.path.join(tmpdir, 'd.txt'), 'w') as f:
            f.write('content d')
            
        # Commit initial state
        subprocess.run(['git', 'add', '.'], cwd=tmpdir, check=True)
        subprocess.run(['git', '-c', 'user.email=test@example.com', '-c', 'user.name=Test User', 'commit', '-m', 'initial'], cwd=tmpdir, check=True)
        
        # Edit d.txt (an earlier task's change)
        with open(os.path.join(tmpdir, 'd.txt'), 'w') as f:
            f.write('modified content d')
        subprocess.run(['git', 'add', 'd.txt'], cwd=tmpdir, check=True)
        subprocess.run(['git', '-c', 'user.email=test@example.com', '-c', 'user.name=Test User', 'commit', '-m', 'modify d'], cwd=tmpdir, check=True)
        
        # Get base fingerprint
        base = aidev_tuios.scope_fingerprint(tmpdir)
        
        # Edit b.txt, add c.txt
        with open(os.path.join(tmpdir, 'b.txt'), 'w') as f:
            f.write('modified content b')
        with open(os.path.join(tmpdir, 'c.txt'), 'w') as f:
            f.write('new content c')
            
        # Get current fingerprint
        now = aidev_tuios.scope_violations(base, aidev_tuios.scope_fingerprint(tmpdir), {"a.txt"})
        expected = ["b.txt", "c.txt"]
        
        if set(now) == set(expected):
            print("PASS")
        else:
            print("FAIL")
            print(f"Expected: {expected}")
            print(f"Got: {now}")
            return 1
            
        # Test with correct files
        now2 = aidev_tuios.scope_violations(base, aidev_tuios.scope_fingerprint(tmpdir), {"b.txt", "c.txt"})
        if now2 == []:
            print("PASS")
        else:
            print("FAIL")
            print(f"Expected empty list, got: {now2}")
            return 1

    # A bare allowed name matches the full path that ends with it
    now3 = aidev_tuios.scope_violations({}, {".config/x/a.txt": "1"}, {"a.txt"})
    if now3 == []:
        print("PASS")
    else:
        print("FAIL")
        print(f"Expected empty list, got: {now3}")
        return 1

    now4 = aidev_tuios.scope_violations({}, {".config/x/b.txt": "1"}, {"a.txt"})
    if now4 == [".config/x/b.txt"]:
        print("PASS")
    else:
        print("FAIL")
        print(f"Expected ['.config/x/b.txt'], got: {now4}")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())