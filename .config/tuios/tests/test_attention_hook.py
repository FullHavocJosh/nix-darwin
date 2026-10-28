"""
Run: python3 .config/tuios/tests/test_attention_hook.py
"""

import os
import subprocess
import sys
import tomllib
from pathlib import Path

CONFIG = Path(__file__).parent.parent / "config.toml"
HOOK = Path(__file__).parent.parent / "hooks" / "agent-attention.sh"
WINDOW = "claude-builder"
SESSION = "session1"


# Helper to check test conditions
def check(name, cond):
    if cond:
        print(f"PASS: {name}")
    else:
        print(f"FAIL: {name}")
        return 1
    return 0


def run_hook(state, window=WINDOW, session=SESSION):
    env = dict(os.environ)
    env["TUIOS_HOOK_DRY_RUN"] = "1"
    env["TUIOS_AGENT_STATE"] = state
    env["TUIOS_WINDOW_NAME"] = window
    env["TUIOS_SESSION_ID"] = session
    result = subprocess.run(
        ["sh", str(HOOK)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.returncode, result.stdout


def test_alerts_when_attention_needed():
    """needs_input and errored print the alert."""
    failures = 0
    for state in ("needs_input", "errored"):
        code, out = run_hook(state)
        failures += check(f"{state} exits 0", code == 0)
        failures += check(f"{state} prints the window name", WINDOW in out)
        failures += check(f"{state} prints the state", state in out)
        failures += check(f"{state} names the Inbox", "tuios Inbox" in out)
    return failures


def test_quiet_when_not_needed():
    """working, idle and done print nothing."""
    failures = 0
    for state in ("working", "idle", "done"):
        code, out = run_hook(state)
        failures += check(f"{state} exits 0", code == 0)
        failures += check(f"{state} prints nothing", out == "")
    return failures


def test_config_wires_attention():
    """config.toml installs the hook, suppresses focused notifications and colours waiting tabs."""
    with CONFIG.open("rb") as f:
        config = tomllib.load(f)
    failures = 0
    hook = config.get("hooks", {}).get("after-agent-state")
    failures += check(
        "hooks.after-agent-state runs agent-attention.sh",
        hook == ["sh ~/.config/tuios/hooks/agent-attention.sh"],
    )
    failures += check(
        "notifications.agent.suppress_focused is true",
        config.get("notifications", {}).get("agent", {}).get("suppress_focused") is True,
    )
    failures += check(
        "dock.tabs.attention_fg is set",
        config.get("dock", {}).get("tabs", {}).get("attention_fg") == "#f38ba8",
    )
    return failures


def main():
    failures = 0
    failures += test_alerts_when_attention_needed()
    failures += test_quiet_when_not_needed()
    failures += test_config_wires_attention()

    if failures > 0:
        print(f"\n{failures} test(s) failed")
        return 1
    else:
        print("\nAll tests passed")
        return 0


if __name__ == "__main__":
    sys.exit(main())
