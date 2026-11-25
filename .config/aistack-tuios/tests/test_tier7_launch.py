#!/usr/bin/env python3
"""Tier-7 launch test: tier_online('tier-7') is False without a Zen key or with nothing offered, and the tier-7
builder body starts opencode on an opencode/ Zen model while tier-5 keeps picking opencode-go/ models.
No network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_tier7_launch.py
"""

import importlib.util
import json
import os
import sys
import tempfile
import types

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)  # .config/aistack-tuios
os.environ["AISTACK_DIR"] = os.path.join(
    os.path.dirname(ROOT), "aistack"
)  # this checkout's zen_models.py
os.environ["AIDEV_SEMI_LOCAL"] = "off"  # never probe the G14 over the network
FAILS = []


def check(name, cond, extra=""):
    print(
        ("  PASS " if cond else "  FAIL ")
        + name
        + (f"  [{extra}]" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    for var in (
        "AIDEV_TUIOS_SESSION",
        "AIDEV_TUIOS_RUN",
        "AIDEV_TUIOS_PROJECT",
        "AIDEV_TUIOS_BUILDER",
    ):
        os.environ.pop(var, None)
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(
        tempfile.mkdtemp(prefix="aidev-test-home-")
    )
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))
    real_zen_status = a.zen_status

    print("tier-7 online without a Zen key")
    a.zen_key_present = lambda: False
    check("tier-7 is offline without a Zen key", a.tier_online("tier-7") is False)

    print("tier-7 online with a key but nothing offered")
    a.zen_key_present = lambda: True
    seen = []

    def zen_off(run, refresh=False, provider="go"):
        seen.append(provider)
        return {
            "state": "none",
            "model": None,
            "detail": "no free model is offered to this account",
            "models": [],
        }

    a.zen_status = zen_off
    check("tier-7 is offline when nothing is offered", a.tier_online("tier-7") is False)
    check("tier-7 asks the zen provider", seen == ["zen"])
    check(
        "tier-5 asks the go provider",
        a.tier_online("tier-5") is False and seen == ["zen", "go"],
    )

    print("zen_model and zen_status carry the provider")
    cmds = []

    def fake_run(*args, **kw):
        cmds.append(args[0])
        return types.SimpleNamespace(
            returncode=0, stdout=json.dumps({"model": "opencode-go/glm-5.3"}), stderr=""
        )

    a.subprocess.run = fake_run
    check(
        "zen_model passes --provider go by default",
        a.zen_model("p") == "opencode-go/glm-5.3"
        and cmds[-1][cmds[-1].index("--provider") + 1] == "go",
        cmds,
    )
    check(
        "zen_model takes a positional provider",
        a.zen_model("p", "zen") is not None
        and cmds[-1][cmds[-1].index("--provider") + 1] == "zen",
        cmds,
    )
    payload = json.dumps(
        {
            "models": [{"model": "zen-free-id", "state": "available"}],
            "best": "zen-free-id",
        }
    )
    a.subprocess.run = lambda *args, **kw: (
        cmds.append(args[0])
        or types.SimpleNamespace(returncode=0, stdout=payload, stderr="")
    )
    a.zen_status = real_zen_status
    zst = a.Run(
        os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-")), "tier7-status"
    )
    s = a.zen_status(zst, provider="zen")
    check(
        "zen_status passes --provider zen and keeps the best model in zen7_model",
        s["state"] == "available"
        and zst.data.get("zen7_model") == "zen-free-id"
        and "zen_model" not in zst.data
        and cmds[-1][cmds[-1].index("--provider") + 1] == "zen",
        (s, cmds[-1]),
    )
    a.zen_status(zst)
    check(
        "zen_status keeps the default go pick in zen_model",
        zst.data.get("zen_model") == "zen-free-id"
        and cmds[-1][cmds[-1].index("--provider") + 1] == "go",
        cmds[-1],
    )

    print("tier-7 body starts opencode on a Zen model")
    p = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-"))
    zrun = a.Run(p, "tier7-test")
    zcfg = a.pane_configs(p)
    a.write_git_guard = lambda r: a.write_text(
        os.path.join(r.dir, "bin", "guard", "git"), ""
    )

    def fake_zen_model(project, provider="go"):
        return "opencode/zen-free-id" if provider == "zen" else "opencode-go/glm-5.3"

    a.zen_model = fake_zen_model
    body7 = a.build_body(zrun, zcfg, "tier-7", "build-zen-tier-7")
    check(
        "tier-7 body starts opencode on an opencode/ model",
        body7 is not None
        and "opencode mini --agent build --model opencode/zen-free-id " in body7,
        body7,
    )
    check(
        "tier-7 keeps its pick in run.data zen7_model",
        zrun.data.get("zen7_model") == "opencode/zen-free-id"
        and "zen_model" not in zrun.data,
    )
    check(
        "tier-7 pane is labelled with the Zen model",
        zrun.data["panes"]["build-zen-tier-7"]["builder"]
        == "OpenCode opencode/zen-free-id (Zen, paid)",
    )

    print("tier-5 body keeps the Go provider")
    body5 = a.build_body(zrun, zcfg, "tier-5", "build-free-tier-5")
    check(
        "tier-5 body starts opencode on an opencode-go/ model",
        body5 is not None and "--model opencode-go/glm-5.3 " in body5,
        body5,
    )
    check(
        "tier-5 does not reuse the tier-7 pick",
        "opencode/zen-free-id" not in body5
        and zrun.data.get("zen_model") == "opencode-go/glm-5.3",
    )

    print("tier-7 body without a Zen model")
    a.zen_model = lambda project, provider="go": (
        "opencode-go/glm-5.3" if provider == "go" else None
    )
    none_run = a.Run(p, "tier7-none")
    check(
        "tier-7 body is None when no Zen model is offered",
        a.build_body(none_run, zcfg, "tier-7", "build-zen-tier-7") is None,
    )

    print("no_builder_why names the tier-7 gap")
    a.zen_key_present = lambda: True
    check(
        "no_builder_why names the missing Zen offer",
        a.no_builder_why("tier-7") == "no Zen model is offered",
    )
    a.zen_key_present = lambda: False
    check(
        "no_builder_why names the missing Zen key",
        a.no_builder_why("tier-7") == a.NO_ZEN_KEY,
    )

    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
