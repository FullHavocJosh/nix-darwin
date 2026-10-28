#!/usr/bin/env python3
"""
Tests for the plan_mcp_guard.py hook.
"""

import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "plan_mcp_guard.py")
FAILS = []

def check(name, cond, extra=""):
    if not cond:
        print(f"FAIL: {name}")
        if extra:
            print(f"  Extra info: {extra}")
        FAILS.append(name)
    else:
        print(f"PASS: {name}")

def run_hook(input_data, env=None, raw=False):
    """Run the hook with given input and environment; raw=True returns its stdout unparsed."""
    if env is None:
        env = {}
    
    result = subprocess.run([
        sys.executable, 
        HOOK
    ], 
    input=json.dumps(input_data), 
    capture_output=True, 
    text=True, 
    env=env)
    
    if raw:
        return result.stdout
    if result.stdout.strip():
        try:
            return json.loads(result.stdout.strip())
        except json.JSONDecodeError:
            return None
    return None

def main():
    # Test read tools that should be allowed
    read_tools = [
        "mcp__atlassian__getJiraIssue",
        "mcp__atlassian__searchJiraIssuesUsingJql",
        "mcp__atlassian__getConfluencePage",
        "mcp__atlassian__fetch",
        "mcp__github__github_pr_list",
        "mcp__github__github_file_get",
        "mcp__github__github_pr_changes"
    ]
    
    for tool in read_tools:
        input_data = {"tool_name": tool}
        result = run_hook(input_data)
        check(f"allow {tool}", 
              result and result.get("hookSpecificOutput", {}).get("permissionDecision") == "allow",
              f"Got {result}")
    
    # Test write tools that should be denied
    write_tools = [
        "mcp__atlassian__createJiraIssue",
        "mcp__atlassian__editJiraIssue",
        "mcp__atlassian__addCommentToJiraIssue",
        "mcp__atlassian__transitionJiraIssue",
        "mcp__atlassian__updateConfluencePage",
        "mcp__github__github_pr_create",
        "mcp__github__github_pr_approve",
        "mcp__github__github_pr_suggest_change"
    ]
    
    for tool in write_tools:
        input_data = {"tool_name": tool}
        result = run_hook(input_data)
        check(f"deny {tool}", 
              result and result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
              f"Got {result}")
    
    # Test tools without guarded prefix (should not output anything)
    other_tools = [
        "mcp__tuios__tuios_list_agents",
        "Bash"
    ]
    
    for tool in other_tools:
        input_data = {"tool_name": tool}
        out = run_hook(input_data, raw=True)
        check(f"no output for {tool}", 
              out.strip() == "",
              f"Got {out!r}")
    
    # Test with missing guard file - should deny
    env = {"AIDEV_TUIOS_GUARD": "/nonexistent/ainfo_guard.py"}
    input_data = {"tool_name": "mcp__atlassian__getJiraIssue"}
    result = run_hook(input_data, env)
    check("deny on missing guard", 
          result and result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny",
          f"Got {result}")
    
    # Test with invalid JSON input - should deny
    result = subprocess.run([
        sys.executable, 
        HOOK
    ], 
    input="not json", 
    capture_output=True, 
    text=True)
    
    # Should have error output
    check("deny on invalid JSON", 
          result.stdout.strip() and "plan_mcp_guard error" in result.stdout,
          f"Got stdout: '{result.stdout}', stderr: '{result.stderr}'")
    
    if FAILS:
        print(f"\nFailed tests: {len(FAILS)}")
        return 1
    else:
        print("\nAll tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())