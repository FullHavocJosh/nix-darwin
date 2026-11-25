#!/usr/bin/env python3
"""Tier-8 launch test: tier_online('tier-8') is False without OPENROUTER_API_KEY, and the tier-8 builder body
starts pi with --provider openrouter and the configured model while the launcher script never holds the key.
No network.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_tier8_launch.py
"""

import importlib.util
import os
import sys
import tempfile

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
        "OPENROUTER_API_KEY",
        "AI_OPENROUTER_MODEL",
    ):
        os.environ.pop(var, None)
    os.environ["AIDEV_TUIOS_HOME"] = os.path.realpath(
        tempfile.mkdtemp(prefix="aidev-test-home-")
    )
    a = load("aidev", os.path.join(ROOT, "aidev_tuios.py"))

    print("tier-8 online gate")
    check(
        "tier-8 is offline without OPENROUTER_API_KEY", a.tier_online("tier-8") is False
    )
    os.environ["OPENROUTER_API_KEY"] = "sk-or-t8-test-secret"
    # stub urllib.request.urlopen to return 200 for openrouter_usable()
    import urllib.request
    original_urlopen = urllib.request.urlopen
    class FakeResponse:
        def __init__(self, code): self.code = code
        def getcode(self): return self.code
        def __enter__(self): return self
        def __exit__(self, *args): return None
    urllib.request.urlopen = lambda req, timeout=None: FakeResponse(200)
    check("tier-8 is online with OPENROUTER_API_KEY", a.tier_online("tier-8") is True)
    urllib.request.urlopen = original_urlopen
    check(
        "the default model is the one aidev_pick configures",
        a.OPENROUTER_MODEL == "~anthropic/claude-sonnet-latest",
    )

    print("tier-8 body starts pi on the OpenRouter provider")
    p = os.path.realpath(tempfile.mkdtemp(prefix="aidev-test-proj-"))
    trun = a.Run(p, "tier8-test")
    tcfg = a.pane_configs(p)
    a.write_git_guard = lambda r: a.write_text(
        os.path.join(r.dir, "bin", "guard", "git"), ""
    )
    a.OPENROUTER_MODEL = "acme/t8-model"  # the configured model
    body = a.build_body(trun, tcfg, "tier-8", "build-openrouter-tier-8")
    check(
        "tier-8 body runs pi with --provider openrouter and the configured model",
        body is not None and "pi --provider openrouter --model acme/t8-model " in body,
        body,
    )
    check(
        "the tier-8 pane is labelled with the model",
        trun.data["panes"]["build-openrouter-tier-8"]["builder"]
        == "OpenRouter acme/t8-model (billed)",
    )
    check(
        "tier-8 keeps one pi session id",
        bool(trun.data["panes"]["build-openrouter-tier-8"].get("session_id")),
    )

    print("the launcher script never contains the key value")
    script = a.write_script(trun, "build-openrouter-tier-8", body)
    with open(script) as fh:
        text = fh.read()
    check(
        "the key value is not in the launcher script",
        "sk-or-t8-test-secret" not in text,
    )
    check("the key is not exported with a value", "OPENROUTER_API_KEY=" not in text)

    print("tier-8 without an OpenRouter key")
    os.environ.pop("OPENROUTER_API_KEY")
    none_run = a.Run(p, "tier8-none")
    check(
        "tier-8 body is None without OPENROUTER_API_KEY",
        a.build_body(none_run, tcfg, "tier-8", "build-openrouter-tier-8") is None,
    )
    check(
        "no_builder_why names the missing OpenRouter key",
        a.no_builder_why("tier-8") == "OPENROUTER_API_KEY is not set",
    )
    check("tier-8 resets like the other pi panes", a.RESET_CMD["tier-8"] == "/new")

    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
