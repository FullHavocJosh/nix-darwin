"""Tests for gpa's secrets scan: the entropy scanner's identifier handling, the capped/unique report, and what happens
when the AI analysis fails. No network, no AI provider (the analysis is stubbed).
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_secrets_scan.py
"""
import os
import random
import string
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
FUNCS = os.path.join(ROOT, ".zshrc_functions_git")
FAILS = []

def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond: FAILS.append(name)

def zsh(script, cwd=None, timeout=120):
    env = {k: v for k, v in os.environ.items() if k not in ("AI_LOCAL_DEFAULT", "AI_LOCAL_ONLY")}
    return subprocess.run(["zsh", "-c", f"source {FUNCS} 2>/dev/null; " + script], cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)

def scan(lines):
    r = zsh("_entropy_scan_secrets", timeout=60) if False else subprocess.run(
        ["zsh", "-c", f"source {FUNCS} 2>/dev/null; _entropy_scan_secrets"], input="\n".join(lines) + "\n", capture_output=True, text=True, timeout=60)
    return [l.split("\t")[0] for l in r.stdout.splitlines() if l.strip()]

rnd = random.Random(7)
def token(n, alphabet): return "".join(rnd.choice(alphabet) for _ in range(n))

print("entropy scanner: identifiers are not secrets")
ids = ['CT_TextCharacterProperties', 'ST_HyperlinkSymbolType', 'EG_RunInnerContent', 'CT_GlobalVisualEffectsList',
       'ST_DashedUnderlineStyleKind', 'AbstractConnectionHandlerFactory', 'default_connection_timeout_seconds',
       'RemoteWorkspaceVariableSetBinding']
for i in ids:
    check(f"identifier {i} is not flagged", scan([f'type = "{i}"']) == [], i)
print("entropy scanner: real-looking secrets still are")
# 64 characters: random samples much shorter than that often score a little under the scanner's 4.5 threshold
secrets = {"base62 with digits": token(64, string.ascii_letters + string.digits), "hex": token(48, "0123456789abcdef"),
           "base64-ish": token(60, string.ascii_letters + string.digits + "+/") + "=", "token with underscores and digits": "sk_live_" + token(56, string.ascii_letters + string.digits),
           "letters only, few vowels": token(64, "bcdfghjklmnpqrstvwxyzBCDFGHJKLMNPQRSTVWXYZ")}
for name, v in secrets.items():
    check(f"{name} is flagged", len(scan([f'DB_CONN = "{v}"'])) == 1, v)

print("report: unique and capped")
t = tempfile.mkdtemp(); subprocess.run(["git", "init", "-q", t])
lines = []
for i in range(40):
    v = token(64, string.ascii_letters + string.digits)
    lines += [f'k{i} = "{v}"'] * 3          # each value appears in three copies
open(t + "/secrets.txt", "w").write("\n".join(lines) + "\n"); subprocess.run(["git", "add", "secrets.txt"], cwd=t)
STUB_FAIL = '_run_ai_plain() { cat >/dev/null; echo "Error: local model hit its token limit (alias x)"; return 1; }'
r = zsh(f"{STUB_FAIL}; _check_for_secrets true", cwd=t)
out = r.stdout
check("each distinct value is listed once (not once per copy)", out.count("(entropy") == 25, out.count("(entropy"))
check("the list is capped with an 'and N more' line", "... and 15 more" in out and "(40 distinct)" in out, out[-600:])

print("a failed AI analysis is not 'all clear'")
check("auto mode aborts", r.returncode == 1 and "Auto mode" in out and "aborting" in out, (r.returncode, out[-300:]))
check("the failure is shown, not mistaken for an analysis", "AI analysis unavailable" in out and "token limit" in out, out[-500:])
STUB_OK = '_run_ai_plain() { cat >/dev/null; printf "These are test values.\\nVERDICT: ALL_CLEAR\\n"; }'
r2 = zsh(f"{STUB_OK}; _check_for_secrets true", cwd=t)
check("an ALL_CLEAR verdict still proceeds", r2.returncode == 0 and "Proceeding" in r2.stdout, (r2.returncode, r2.stdout[-200:]))
STUB_BAD = '_run_ai_plain() { cat >/dev/null; printf "One is real.\\nVERDICT: NEEDS_REVIEW\\n"; }'
r3 = zsh(f"{STUB_BAD}; _check_for_secrets true", cwd=t)
check("NEEDS_REVIEW still aborts in auto mode", r3.returncode == 1, (r3.returncode, r3.stdout[-200:]))
prompt = zsh('_run_ai_plain() { cat > /tmp/secrets-prompt.$$; echo "VERDICT: ALL_CLEAR"; echo "$AI_LOCAL_ALIAS" > /tmp/secrets-alias.$$; }; _check_for_secrets true >/dev/null; wc -c < /tmp/secrets-prompt.$$; cat /tmp/secrets-alias.$$; rm -f /tmp/secrets-prompt.$$ /tmp/secrets-alias.$$', cwd=t).stdout.split()
check("the analysis runs with its own token budget alias", prompt[-1] == "local-coder-secrets", prompt)
check("and its prompt stays small (under 8000 chars) however many detections there are", int(prompt[0]) < 8000, prompt)

print("opencode v2 flag")
src = open(FUNCS).read()
check("the interactive fallback no longer passes --model", "opencode --model" not in src and 'opencode --prompt "I have staged' in src)

print("\nFAILED: %s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
