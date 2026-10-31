#!/usr/bin/env python3
"""
Test that plan_bash_guard.py is properly wired up in the hooks.
"""
import importlib.util
import os
import sys
import tempfile

# Import the module
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("aidev_tuios", os.path.join(HERE, "..", "aidev_tuios.py"))
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

FAILS = 0

with tempfile.TemporaryDirectory() as tmp:
    s = os.path.join(tmp, "s")
    b = os.path.join(tmp, "b")
    
    # Call write_backbone_settings
    a.write_backbone_settings({'claude_settings': s, 'claude_backbone': b})
    
    # Read the backbone file
    import json
    with open(b, 'r') as f:
        backbone_data = json.load(f)
    
    # Check that hooks.PreToolUse contains a Bash entry
    hooks = backbone_data.get('hooks', {})
    pre_tool_hooks = hooks.get('PreToolUse', [])
    
    bash_hook_found = False
    mcp_hook_found = False
    
    for hook in pre_tool_hooks:
        if hook.get('matcher') == 'Bash':
            # Check if it ends with plan_bash_guard.py
            command = hook.get('hooks', [{}])[0].get('command', '')
            if command.endswith('plan_bash_guard.py'):
                bash_hook_found = True
        elif hook.get('matcher', '').startswith('mcp__atlassian__') or hook.get('matcher', '').startswith('mcp__github__'):
            mcp_hook_found = True
    
    if not bash_hook_found:
        print("FAIL: No Bash hook found ending with plan_bash_guard.py")
        FAILS += 1
    else:
        print("PASS: Bash hook found ending with plan_bash_guard.py")
        
    if not mcp_hook_found:
        print("FAIL: No MCP hook found")
        FAILS += 1
    else:
        print("PASS: MCP hook found")

sys.exit(1 if FAILS else 0)