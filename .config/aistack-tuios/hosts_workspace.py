#!/usr/bin/env python3
"""
Open one read-only tuios window per host on workspace 2, skipping windows that exist.
Reads the host table from the ai-info repo.
"""

import argparse
import json
import os
import sys

DEFAULT_TABLE = os.path.expanduser("~/ai-info/manage/") + "hosts" + ".json"
WORKSPACE = 2
GRANTS = "read"


def load_hosts(path):
    """
    Load hosts from the JSON table.

    Args:
        path: Path to the JSON file containing {"hosts": [...]}

    Returns:
        The 'hosts' list from the JSON file.

    Raises:
        ValueError: If the file is missing, not JSON, or an entry lacks a non-empty string 'name'
                    or has a name not starting with 'top-'.
    """
    expanded = os.path.expanduser(path)

    if not os.path.isfile(expanded):
        raise ValueError(f"file missing: {expanded}")

    try:
        with open(expanded, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"not JSON: {e}")

    if "hosts" not in data:
        raise ValueError("missing 'hosts' key")

    hosts = data["hosts"]

    for host in hosts:
        if "name" not in host:
            raise ValueError(f"entry lacks 'name': {host}")
        name = host["name"]
        if not isinstance(name, str) or name == "":
            raise ValueError(f"name must be a non-empty string: {host}")
        if not name.startswith("top-"):
            raise ValueError(f"name must start with 'top-': {name}")

    return hosts


def plan_windows(hosts, existing_windows):
    """
    Plan which windows to open.

    Returns:
        The hosts whose name is not the 'custom_name' of any dict in existing_windows.
    """
    existing_custom_names = {win.get("custom_name") for win in existing_windows}
    result = []
    for host in hosts:
        name = host["name"]
        if name not in existing_custom_names:
            result.append(host)
    return result


def open_hosts(session, hosts, workspace, tuios, tuios_json, script, cwd):
    """
    Open windows for each host.

    Args:
        session: Session name
        hosts: All hosts loaded from the table
        workspace: Workspace number
        tuios: tuios function
        tuios_json: tuios_json function
        script: Path to the script to run in each new window
        cwd: Working directory for each new window

    Returns:
        A list of (name, ok) for the hosts it opened.
        Prints 'exists NAME' for hosts whose window already exists (never tried),
        and 'opened NAME' or 'failed NAME: <first 200 chars of err>' for the rest.
    """
    existing = tuios_json("list-windows", "-s", session).get("windows") or []
    todo = plan_windows(hosts, existing)
    todo_names = {host["name"] for host in todo}
    results = []

    for host in hosts:
        name = host["name"]
        if name not in todo_names:
            print(f"exists {name}")
            continue
        code, out, err = tuios(
            "new-window",
            name,
            "-s",
            session,
            "--workspace",
            str(workspace),
            "--cwd",
            cwd,
            "--grants",
            GRANTS,
            "--no-focus",
            "--",
            "/bin/zsh",
            script,
            name,
        )
        ok = code == 0
        if ok:
            print(f"opened {name}")
        else:
            print(f"failed {name}: {err[:200]}")
        results.append((name, ok))

    return results


def main(argv=None):
    """
    Main entry point.

    Args:
        argv: Command line arguments, defaults to sys.argv[1:]

    Returns:
        0 when no host failed, else 1
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", type=str, default=DEFAULT_TABLE)
    parser.add_argument("--session", type=str, default=None)
    parser.add_argument("--workspace", type=int, default=WORKSPACE)
    args = parser.parse_args(argv)

    # Add the module's own directory to sys.path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, script_dir)

    script = os.path.join(os.path.dirname(args.table), "host-pane" + ".sh")
    cwd = os.path.dirname(os.path.dirname(args.table))

    # Import tuios and tuios_json lazily
    from aidev_tuios import tuios, tuios_json

    session = args.session
    if not session:
        env_session = os.environ.get("TUIOS_SESSION")
        if not env_session:
            print("missing TUIOS_SESSION env")
            return 2
        session = env_session

    try:
        hosts = load_hosts(args.table)
    except ValueError as e:
        print(str(e))
        return 2

    results = open_hosts(session, hosts, args.workspace, tuios, tuios_json, script, cwd)

    failed = any(ok is False for _, ok in results)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
