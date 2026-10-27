#!/usr/bin/env python3
"""
agent_cycle.py: focus the next or previous agent across all sessions

This script is bound to ctrl+j (next) and ctrl+k (prev) in config.toml.
"""

import json
import os
import subprocess
import sys


def order_agents(agents):
    """Return a new list sorted by (session, workspace, name, window_id)."""
    return sorted(agents, key=lambda a: (
        a.get("session", ""),
        a.get("workspace", 0),
        a.get("name", ""),
        a.get("window_id", "")
    ))


def find_current(agents, current_id):
    """Index of the agent whose window_id equals current_id, or whose window_id starts with current_id
    when current_id is not empty; -1 when none matches or current_id is empty."""
    if not current_id:
        return -1
    for i, agent in enumerate(agents):
        if agent.get("window_id", "") == current_id:
            return i
        if agent.get("window_id", "").startswith(current_id):
            return i
    return -1


def pick(agents, current_id, direction):
    """Pick next or previous agent from the ordered list."""
    if not agents:
        return None
    i = find_current(agents, current_id)
    n = len(agents)
    if i == -1:
        # Current agent not found, pick first or last
        if direction == "next":
            return agents[0]
        elif direction == "prev":
            return agents[-1]
    else:
        # Current agent found, pick next or previous
        if direction == "next":
            next_index = (i + 1) % n
        elif direction == "prev":
            next_index = (i - 1) % n
        else:
            raise ValueError("direction must be 'next' or 'prev'")
        # Return None if we would select the current agent
        if next_index == i:
            return None
        return agents[next_index]


def main(argv, run=subprocess.run, env=None):
    """Main function for agent cycling."""
    if env is None:
        env = os.environ
    if len(argv) != 2 or argv[1] not in ("next", "prev"):
        print("usage: agent_cycle.py next|prev", file=sys.stderr)
        return 2

    direction = argv[1]
    current_id = env.get("TUIOS_ACTIVE_PANE_ID", "")

    # Get list of all agents
    result = run(
        ["tuios", "list-agents", "--all-sessions", "--json"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False
    )
    if result.returncode != 0:
        print(f"agent_cycle: {result.stderr.split(chr(10))[0]}", file=sys.stderr)
        return 1
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"agent_cycle: invalid JSON from list-agents: {e}", file=sys.stderr)
        return 1
    if not isinstance(data, dict) or not isinstance(data.get("agents"), list):
        print("agent_cycle: no 'agents' list in list-agents output", file=sys.stderr)
        return 1

    agents = data["agents"]
    if not agents:
        return 0

    # Order the agents
    ordered_agents = order_agents(agents)
    target = pick(ordered_agents, current_id, direction)
    if target is None:
        return 0

    target_window_id = target["window_id"]
    target_session = target["session"]

    # Switch session if needed
    current_session = env.get("TUIOS_SESSION", "")
    if target_session != current_session:
        switch_result = run(
            ["tuios", "switch-session", target_session],
            capture_output=True,
            text=True,
            timeout=10,
            check=False
        )
        if switch_result.returncode != 0:
            print(f"agent_cycle: failed to switch session: {switch_result.stderr.split(chr(10))[0]}", file=sys.stderr)
            return 1

    # Focus the target window
    focus_result = run(
        ["tuios", "focus-window", "-s", target_session, target_window_id],
        capture_output=True,
        text=True,
        timeout=10,
        check=False
    )
    if focus_result.returncode != 0:
        print(f"agent_cycle: failed to focus window: {focus_result.stderr.split(chr(10))[0]}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))