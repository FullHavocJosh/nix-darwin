"""Every reader of AI_HOME expands a leading ~ (an env value from a JSON config is not tilde-expanded by any shell).
Each module runs in its own process with a temporary HOME, so nothing here touches the real ~/.ai.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_ai_home_tilde.py
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
AISTACK = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(AISTACK))
FAILS = []


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


H = os.path.realpath(tempfile.mkdtemp(prefix="ai-home-tilde-"))
OVERRIDES = ("CLAUDE_EDIT_ROUTER_STATE", "LOCAL_EDIT_STATE_DIR", "CODER_PI_AGENT_DIR", "AISTACK_STATE_DIR", "AISTACK_HOME")
ENV = {k: v for k, v in os.environ.items() if k not in OVERRIDES}
ENV.update(HOME=H, AI_HOME="~/aih")


def py(expr, module):
    code = f"import sys; sys.path.insert(0, {AISTACK!r}); import {module} as m; print({expr})"
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=ENV).stdout.strip()


print("AI_HOME=~/aih expands to $HOME/aih")
for module, expr, want in (
    ("edit_router_hook", "m.STATE_DIR", "/aih/guard/edit-router"),
    ("local_edit_mcp", "m.STATE", "/aih/cache/local-edit"),
    ("coder_pi", "m.AGENT_DIR", "/aih/cache/aistack-pi-coder"),
    ("aidev_lib", "m.state_dir('/p/x')", "/aih/aidev/x-"),
):
    got = py(expr, module)
    check(module, got.startswith(H + want), got)

zsh = subprocess.run(["zsh", "-fc", 'print -r -- "${${AI_HOME/#\\~/$HOME}:-$HOME/.ai}"'], capture_output=True, text=True,
                     env=ENV).stdout.strip()
check("the zsh expansion in .zshrc_functions_ai", zsh == H + "/aih", zsh)
with open(os.path.join(REPO, ".zshrc_functions_ai"), encoding="utf-8") as f:
    check("no unexpanded ${AI_HOME:-...} left in .zshrc_functions_ai", "${AI_HOME:-" not in f.read())

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
