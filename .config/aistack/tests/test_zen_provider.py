"""Tests for zen_models.py provider filtering: 'go' = OpenCode Go ids, 'zen' = Zen ids. No network, no opencode.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack/tests/test_zen_provider.py
"""

import contextlib
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import zen_models as z

os.environ["AISTACK_ZEN_KEY"] = "1"

FAILS = []


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def model(cost=0, tool=True, rel="2026-01-01", status=None):
    m = {
        "cost": {"input": cost, "output": cost},
        "tool_call": tool,
        "release_date": rel,
    }
    if status:
        m["status"] = status
    return m


POLICY = {
    "verified": "2026-10-06",
    "source": "https://opencode.ai/docs/zen/",
    "public_preferred": "big-pickle",
    "zero_retention": ["space-bunny-free", "longcat-2.5-preview-free"],
    "go_preferred": [
        "glm-5.3",
        "kimi-k2.7-code",
        "deepseek-v4-pro",
        "qwen3.8-max",
        "minimax-m3",
    ],
    "go_zero_retention": [],
}
GO_POLICY = dict(
    POLICY, go_zero_retention=["glm-5.3"]
)  # a private repo may use this Go model


def cat(**models):
    return {"opencode": {"models": models}}


ALL = {
    "big-pickle",
    "space-bunny-free",
    "longcat-2.5-preview-free",
    "other-free",
    "paid-one",
    "glm-5.3",
}
BASE = cat(
    **{
        "big-pickle": model(),
        "space-bunny-free": model(),
        "longcat-2.5-preview-free": model(),
        "other-free": model(rel="2026-09-01"),
        "paid-one": model(cost=3),
        "glm-5.3": model(cost=3),
    }
)
GO_IDS = {"glm-5.3", "kimi-k2.7-code", "deepseek-v4-pro", "qwen3.8-max", "minimax-m3"}
GO_OUT = [
    "opencode-go/glm-5.3",
    "opencode-go/kimi-k2.7-code",
    "opencode-go/deepseek-v4-pro",
    "opencode-go/qwen3.8-max",
    "opencode-go/minimax-m3",
]
ZEN_OUT = [
    "big-pickle",
    "other-free",
    "space-bunny-free",
    "longcat-2.5-preview-free",
    "opencode/glm-5.3",
]

print("provider=None keeps the old behavior")
DEFAULT = z._candidates_all(BASE, ALL, POLICY, False, go_offered=GO_IDS)
check(
    "public default: each Go id with its paid Zen twin, then the free ids",
    DEFAULT == ["opencode-go/glm-5.3", "opencode/glm-5.3"] + GO_OUT[1:] + ZEN_OUT[:4],
    DEFAULT,
)
check(
    "provider=None equals _candidates_all for a public repo",
    z.candidates(BASE, ALL, POLICY, False, go_offered=GO_IDS) == DEFAULT,
    DEFAULT,
)
check(
    "provider=None equals _candidates_all for a private repo",
    z.candidates(BASE, ALL, GO_POLICY, True, go_offered=GO_IDS)
    == z._candidates_all(BASE, ALL, GO_POLICY, True, go_offered=GO_IDS),
)

print("provider='go'")
r = z.candidates(BASE, ALL, POLICY, False, go_offered=GO_IDS, provider="go")
check("public: every opencode-go/ id and nothing else", r == GO_OUT, r)
check(
    "private: only the zero-retention Go id",
    z.candidates(BASE, ALL, GO_POLICY, True, go_offered=GO_IDS, provider="go")
    == ["opencode-go/glm-5.3"],
)

print("provider='zen'")
r = z.candidates(BASE, ALL, POLICY, False, go_offered=GO_IDS, provider="zen")
check("public: no opencode-go/ id", not any(m.startswith("opencode-go/") for m in r), r)
check(
    "public: the free ids first (Big Pickle first), then the paid twin", r == ZEN_OUT, r
)
check(
    "private: only the free zero-retention ids",
    z.candidates(BASE, ALL, GO_POLICY, True, go_offered=GO_IDS, provider="zen")
    == ["space-bunny-free", "longcat-2.5-preview-free"],
)

print("status passes the provider to candidates")
z.STATUS_CACHE = os.path.join(tempfile.mkdtemp(), "sub", "status.json")
calls = []


def fresh_cache():
    try:
        os.remove(z.STATUS_CACHE)
    except OSError:
        pass


def fake(cmd, **kw):
    calls.append(cmd)
    return z.subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")


r = z.status(BASE, ALL, POLICY, False, do_probe=False, go_offered=GO_IDS, provider="go")
check(
    "public go: the Go candidates, unprobed, nothing probed",
    [m["model"] for m in r["models"]] == GO_OUT
    and all(m["state"] == "unprobed" for m in r["models"])
    and not calls,
    r,
)
r = z.status(
    BASE, ALL, POLICY, False, do_probe=False, go_offered=GO_IDS, provider="zen"
)
check(
    "public zen: the Zen candidates, unprobed, nothing probed",
    [m["model"] for m in r["models"]] == ZEN_OUT
    and all(m["state"] == "unprobed" for m in r["models"])
    and not calls,
    r,
)
r = z.status(
    BASE,
    ALL,
    POLICY,
    False,
    do_probe=True,
    runner=fake,
    go_offered=GO_IDS,
    provider="go",
)
check(
    "public go: the first Go model is probed and is the best",
    r["best"] == "opencode-go/glm-5.3"
    and len(calls) == 1
    and "opencode-go/glm-5.3" in calls[0]
    and [m["state"] for m in r["models"]] == ["available"] + ["unprobed"] * 4,
    (calls, r),
)
fresh_cache()
calls.clear()
r = z.status(
    BASE,
    ALL,
    POLICY,
    False,
    do_probe=True,
    runner=fake,
    go_offered=GO_IDS,
    provider="zen",
)
check(
    "public zen: the first free model is probed and is the best",
    r["best"] == "big-pickle" and len(calls) == 1 and "opencode/big-pickle" in calls[0],
    (calls, r),
)
fresh_cache()
calls.clear()
r = z.status(
    BASE,
    ALL,
    GO_POLICY,
    True,
    do_probe=True,
    runner=fake,
    go_offered=GO_IDS,
    provider="go",
)
check(
    "private go: the zero-retention Go model is probed and is the best",
    r["best"] == "opencode-go/glm-5.3"
    and len(calls) == 1
    and "opencode-go/glm-5.3" in calls[0],
    (calls, r),
)
fresh_cache()
calls.clear()
r = z.status(
    BASE,
    ALL,
    GO_POLICY,
    True,
    do_probe=True,
    runner=fake,
    go_offered=GO_IDS,
    provider="zen",
)
check(
    "private zen: the first free zero-retention model is probed and is the best",
    r["best"] == "space-bunny-free"
    and len(calls) == 1
    and "opencode/space-bunny-free" in calls[0],
    (calls, r),
)
fresh_cache()
calls.clear()

print("choose passes the provider through")
r = z.choose(BASE, ALL, POLICY, private=False, provider="go", go_offered=GO_IDS)
check(
    "public go: the first Go model in policy order",
    r["model"] == "opencode-go/glm-5.3" and not r["warnings"],
    r,
)
r = z.choose(BASE, ALL, POLICY, private=False, provider="zen")
check(
    "public zen: Big Pickle, never a Go id or a paid twin",
    r["model"] == "big-pickle" and not r["warnings"],
    r,
)
check(
    "no provider: the old answer",
    z.choose(BASE, ALL, POLICY, private=False)["model"] == "big-pickle",
)
r = z.choose(BASE, ALL, GO_POLICY, private=True, provider="go", go_offered=GO_IDS)
check("private go: the zero-retention Go model", r["model"] == "opencode-go/glm-5.3", r)
r = z.choose(BASE, ALL, POLICY, private=True, provider="zen")
check(
    "private zen: the first free zero-retention model",
    r["model"] == "space-bunny-free",
    r,
)
r = z.choose(BASE, ALL, POLICY, private=False, provider="go", go_offered=set())
check(
    "go with nothing offered: no model and a warning",
    r["model"] is None and any("no Go model" in w for w in r["warnings"]),
    r,
)

print("command line")
d = tempfile.mkdtemp()
cf = os.path.join(d, "catalog.json")
pf = os.path.join(d, "policy.json")
json.dump(BASE, open(cf, "w"))
json.dump(POLICY, open(pf, "w"))


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = z.main(list(args))
    return rc, out.getvalue(), err.getvalue()


os.environ["AISTACK_ZEN_GO_OFFERED"] = ",".join(sorted(GO_IDS))
try:
    rc, out, _ = run(
        "status",
        "--catalog",
        cf,
        "--offered",
        ",".join(sorted(ALL)),
        "--policy",
        pf,
        "--private",
        "no",
        "--json",
        "--provider",
        "go",
    )
    check(
        "status --provider go lists only the Go ids, unprobed (exit 3)",
        rc == 3 and [m["model"] for m in json.loads(out)["models"]] == GO_OUT,
        (rc, out),
    )
    rc, out, _ = run(
        "status",
        "--catalog",
        cf,
        "--offered",
        ",".join(sorted(ALL)),
        "--policy",
        pf,
        "--private",
        "no",
        "--json",
        "--provider",
        "zen",
    )
    check(
        "status --provider zen lists only the Zen ids, unprobed (exit 3)",
        rc == 3 and [m["model"] for m in json.loads(out)["models"]] == ZEN_OUT,
        (rc, out),
    )
    rc, out, _ = run(
        "choose",
        "--catalog",
        cf,
        "--offered",
        ",".join(sorted(ALL)),
        "--policy",
        pf,
        "--private",
        "no",
        "--provider",
        "go",
    )
    check(
        "choose --provider go gives the first Go model",
        rc == 0 and json.loads(out)["model"] == "opencode-go/glm-5.3",
        out,
    )
    rc, out, _ = run(
        "choose",
        "--catalog",
        cf,
        "--offered",
        ",".join(sorted(ALL)),
        "--policy",
        pf,
        "--private",
        "no",
        "--provider",
        "zen",
    )
    check(
        "choose --provider zen gives Big Pickle",
        rc == 0 and json.loads(out)["model"] == "big-pickle",
        out,
    )
    rc, out, _ = run(
        "choose",
        "--catalog",
        cf,
        "--offered",
        ",".join(sorted(ALL)),
        "--policy",
        pf,
        "--private",
        "no",
    )
    check(
        "choose without --provider keeps the old answer",
        rc == 0 and json.loads(out)["model"] == "big-pickle",
        out,
    )
finally:
    del os.environ["AISTACK_ZEN_GO_OFFERED"]

print("\nFAILED:%s" % FAILS if FAILS else "\nALL PASSED")
sys.exit(1 if FAILS else 0)
