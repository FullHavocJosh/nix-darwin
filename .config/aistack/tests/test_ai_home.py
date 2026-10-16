"""Tests for ai_home.py: the shared ~/.ai layout and the RFC writer every tool uses (RFC 0003).

AI_HOME points at a temp dir, so nothing here touches the real ~/.ai.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_ai_home.py
"""

import datetime
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
T = os.path.realpath(tempfile.mkdtemp(prefix="ai-home-"))
os.environ["AI_HOME"] = T
import ai_home

FAILS = []
TODAY = datetime.date.today().isoformat()


def check(name, cond, extra=""):
    print(("  PASS " if cond else "  FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))
    if not cond:
        FAILS.append(name)


check("AI_HOME moves the tree", ai_home.home() == T and ai_home.path("rfcs") == T + "/rfcs")
check("slugs are short, lower case and safe", ai_home.slug("Fix: the  ALB/TLS thing!") == "fix-the-alb-tls-thing"
      and ai_home.slug("!!!") == "rfc" and len(ai_home.slug("x" * 200)) == 60)

p = ai_home.write_rfc("# Rotate the TLS cert\n\nWhy.", source="ainfo/claude-sonnet", repo="/r")
fm, body = ai_home.split_frontmatter(open(p).read())
check("named YYYY-MM-DD-slug.md in rfcs/", p == f"{T}/rfcs/{TODAY}-rotate-the-tls-cert.md", p)
check("missing frontmatter is filled in", fm == {"title": "Rotate the TLS cert", "status": "draft", "date": TODAY,
                                               "source": "ainfo/claude-sonnet", "repo": "/r"}, fm)
check("the body is kept", body.strip() == "# Rotate the TLS cert\n\nWhy.", body)

p2 = ai_home.write_rfc("---\ntitle: Rotate the TLS cert\nstatus: ready\nsource: me\ntouches: a, b\n---\nBody", source="x")
fm2, _ = ai_home.split_frontmatter(open(p2).read())
check("a taken name gets -2, nothing is overwritten", p2.endswith(f"{TODAY}-rotate-the-tls-cert-2.md") and os.path.exists(p))
check("frontmatter the text brings wins", fm2["status"] == "ready" and fm2["source"] == "me" and fm2["touches"] == "a, b", fm2)
p3 = ai_home.write_rfc("---\ntitle: T\nstatus: whatever\n---\nb")
check("an unknown status becomes draft", ai_home.split_frontmatter(open(p3).read())[0]["status"] == "draft")
check("a title argument names an RFC with no heading", ai_home.write_rfc("plain text", title="Plain one").endswith("-plain-one.md"))

r = subprocess.run([sys.executable, os.path.join(os.path.dirname(HERE), "ai_home.py"), "--write-rfc", "-", "--source", "cli"],
                   input="# From a script\n", capture_output=True, text=True, env={**os.environ, "AI_HOME": T})
check("the CLI saves stdin and prints the path", r.returncode == 0 and r.stdout.strip().endswith("-from-a-script.md")
      and "source: cli" in open(r.stdout.strip()).read(), r.stderr)
check("the template exists and carries source and repo", "source:" in ai_home.template() and "repo:" in ai_home.template())

print("\nFAILED: " + str(FAILS) if FAILS else "\nall passed")
sys.exit(1 if FAILS else 0)
