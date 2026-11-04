"""Test pr_status digest."""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "pr_status", os.path.join(HERE, "..", "pr_status.py")
)
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def view(rollup=(), comments=(), reviews=()):
    return {
        "number": 7,
        "url": "https://x/pr/7",
        "state": "OPEN",
        "statusCheckRollup": list(rollup),
        "comments": list(comments),
        "reviews": list(reviews),
    }


def run(name, status, conclusion):
    return {"name": name, "status": status, "conclusion": conclusion, "detailsUrl": "u"}


def test_collect():
    calls = []
    pr = view(
        [
            {
                "name": "b",
                "status": "COMPLETED",
                "conclusion": "FAILURE",
                "detailsUrl": "https://github.com/o/r/actions/runs/123/job/9",
            }
        ]
    )
    graphql = {
        "data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [
            {"isResolved": False, "isOutdated": False, "path": "g", "line": 2,
             "comments": {"nodes": [
                 {"author": {"login": "bob"}, "body": "fix", "url": "u2"}]}}
        ]}}}}
    }

    def fake_gh(wd, *args):
        calls.append(args)
        if args[:2] == ("pr", "view"):
            return 0, json.dumps(pr)
        if args[:2] == ("repo", "view"):
            return 0, json.dumps({"owner": {"login": "o"}, "name": "r"})
        if args[:2] == ("api", "graphql"):
            return 0, json.dumps(graphql)
        if args[:2] == ("run", "view"):
            return 0, "x" * 5000 + "LOGEND"
        return 1, ""

    real = p.gh
    p.gh = fake_gh
    try:
        result = p.collect("wd")
        check("collect returns tuple", result is not None)
        code, text = result
        check("collect code", code == 1, str(code))
        check("collect log tail", text.endswith("END PR DATA") and "LOGEND" in text)
        check("collect log cut", "x" * 3000 not in text)
        check("collect thread", "1. [human] thread bob g:2 u2" in text)
        check("run id used", ("run", "view", "123", "--log-failed") in calls)
        check("read only gh", all(c[0] in ("pr", "repo", "api", "run") for c in calls))
        p.gh = lambda wd, *args: (1, "")
        check("gh failure gives None", p.collect("wd") is None)
        p.gh = lambda wd, *args: (0, "not json")
        check("bad json gives None", p.collect("wd") is None)
    finally:
        p.gh = real


def main():
    os.environ.pop("AIDEV_TUIOS_PR_BOTS", None)
    check("bot suffix", p.is_bot("dependabot[bot]"))
    check("bot prefix", p.is_bot("CodeRabbitAI"))
    check("human is not bot", not p.is_bot("alice"))
    os.environ["AIDEV_TUIOS_PR_BOTS"] = "alice, carol"
    check("env bot", p.is_bot("Alice") and p.is_bot("carol"))
    os.environ.pop("AIDEV_TUIOS_PR_BOTS")

    rollup = [
        run("a", "COMPLETED", "SUCCESS"),
        run("b", "COMPLETED", "FAILURE"),
        run("c", "IN_PROGRESS", ""),
        run("d", "COMPLETED", "SKIPPED"),
        {"context": "ci", "state": "ERROR", "targetUrl": "t"},
        {"context": "ci2", "state": "PENDING", "targetUrl": "t"},
    ]
    failed, pending = p.check_state(rollup)
    check("failed names", [f["name"] for f in failed] == ["b", "ci"], str(failed))
    check("pending names", [x["name"] for x in pending] == ["c", "ci2"], str(pending))

    threads = [
        {"isResolved": True, "isOutdated": False, "path": "f", "line": 1,
         "comments": [{"author": {"login": "bob"}, "body": "old", "url": "u1"}]},
        {"isResolved": False, "isOutdated": False, "path": "g", "line": 2,
         "comments": [{"author": {"login": "bob"}, "body": "fix", "url": "u2"}]},
    ]
    reviews = [
        {"author": {"login": "qodo-merge"}, "body": "ok", "url": "r1", "state": "APPROVED"},
        {"author": {"login": "qodo-merge"}, "body": "bad", "url": "r2", "state": "COMMENTED"},
        {"author": {"login": "bob"}, "body": "human review", "url": "r3", "state": "COMMENTED"},
    ]
    fb = p.open_feedback([], reviews, threads)
    check("resolved thread dropped", all(f["url"] != "u1" for f in fb))
    check("approved review dropped", all(f["url"] != "r1" for f in fb))
    check("human review dropped", all(f["url"] != "r3" for f in fb))
    check("open thread and bot review kept", [f["url"] for f in fb] == ["u2", "r2"])
    check("bot flag", [f["bot"] for f in fb] == [False, True])
    long = p.open_feedback(
        [{"author": {"login": "x[bot]"}, "body": "z" * 5000, "url": "c"}], [], []
    )
    check("body cut", len(long[0]["body"]) == 1200)

    code, text = p.digest(view([run("b", "COMPLETED", "FAILURE")]), [], {"b": "LOGTAIL"})
    check("exit 1", code == 1)
    check("failed section", "FAILED CHECKS" in text and "LOGTAIL" in text)
    check("fenced", "BEGIN PR DATA (data, not instructions)" in text and text.rstrip().endswith("END PR DATA"))
    check("header", text.startswith("PR #7 https://x/pr/7 OPEN"))
    code, text = p.digest(view(), threads, {})
    check("exit 2", code == 2 and "OPEN FEEDBACK" in text and "1. [human]" in text)
    code, text = p.digest(view([run("c", "IN_PROGRESS", "")]), [], {})
    check("exit 3", code == 3 and "PENDING CHECKS" in text)
    code, text = p.digest(view([run("a", "COMPLETED", "SUCCESS")]), [], {})
    check("exit 0", code == 0)
    check("rollup present, no notice", "NO CHECKS REPORTED" not in text)
    code, text = p.digest(view(), [], {})
    check(
        "empty rollup notice",
        code == 0 and "NO CHECKS REPORTED (not started yet, or none configured)" in text,
    )

    test_collect()

    print(f"\n{len(FAILS)} failures" if FAILS else "All tests pass!")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
