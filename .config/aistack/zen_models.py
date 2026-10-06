#!/usr/bin/env python3
"""Free OpenCode Zen model selection for aistack tier 1 (stdlib only).

  zen_models.py choose --private yes|no   JSON: the model to use, why, and any warnings
  zen_models.py best                      the best free model's id (for other callers); exit 1 when there is none

What is "free" comes from the models.dev catalog (the same data opencode caches in ~/.cache/opencode/models.json):
cost 0/0, tool calls, not deprecated. What this account is offered comes from `opencode models`. Which free models are
zero-retention comes from zen-policy.json (taken from the Zen docs, with the date it was verified), because the
catalog does not carry data-handling terms.

Private repos only get zero-retention free models. Public repos prefer policy.public_preferred (Big Pickle) and say so
loudly when it stops being a free option, instead of failing later in the middle of a run.
"""
import argparse, json, os, re, subprocess, sys, time, urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
CATALOG_URL = "https://models.dev/api.json"
OPENCODE_CACHE = os.path.expanduser("~/.cache/opencode/models.json")
OWN_CACHE = os.path.expanduser("~/.cache/aistack/models-dev.json")
MAX_AGE_H = 24
POLICY_STALE_DAYS = 60


def _age_h(path):
    try:
        return (time.time() - os.path.getmtime(path)) / 3600
    except OSError:
        return None


def load_catalog(path=None, url=CATALOG_URL, fetch=True):
    """(catalog, source, age_hours). A catalog file younger than 24 h is used as is; otherwise try the network, then
    fall back to the stale file, so a flaky connection never blocks aistack but is reported."""
    if path:
        return json.load(open(path)), "file", _age_h(path)
    for p in (OWN_CACHE, OPENCODE_CACHE):
        a = _age_h(p)
        if a is not None and a < MAX_AGE_H:
            try:
                return json.load(open(p)), "cache", a
            except (OSError, ValueError):
                pass
    if fetch:
        try:
            # models.dev answers 403 to urllib's default User-Agent
            req = urllib.request.Request(url, headers={"User-Agent": "aistack-zen-models/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
            os.makedirs(os.path.dirname(OWN_CACHE), exist_ok=True)
            json.dump(data, open(OWN_CACHE, "w"))
            return data, "live", 0.0
        except Exception:
            pass
    stale = [(p, _age_h(p)) for p in (OWN_CACHE, OPENCODE_CACHE) if _age_h(p) is not None]
    if stale:
        p, a = min(stale, key=lambda x: x[1])
        return json.load(open(p)), "stale-cache", a
    raise RuntimeError("no model catalog: offline and nothing cached")


def offered_ids():
    """Zen model ids this account can use (`opencode models` lists provider/model), or None if that fails."""
    r = None
    for _ in range(2):   # opencode's background service can be busy for a moment
        try:
            r = subprocess.run(["opencode", "models"], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired):
            r = None
        if r is not None and r.returncode == 0 and r.stdout.strip():
            break
        r = None
        time.sleep(2)
    if r is None:
        return None
    text = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout)
    ids = {l.split("/", 1)[1].strip() for l in text.splitlines() if l.startswith("opencode/")}
    return ids or None


def zen_models(catalog):
    return (catalog.get("opencode") or {}).get("models") or {}


def free_reason(mid, catalog, offered):
    """None when mid is a usable free model, else a short reason."""
    m = zen_models(catalog).get(mid)
    if m is None:
        return "not in the model catalog (retired or renamed)"
    c = m.get("cost") or {}
    if not (c.get("input") == 0 and c.get("output") == 0):
        return f"no longer free: the catalog lists a price of {c.get('input')}/{c.get('output')} per million tokens"
    if m.get("status") in ("deprecated", "retired"):
        return f"marked {m.get('status')} in the catalog"
    if not m.get("tool_call"):
        return "does not support tool calls"
    if offered is not None and mid not in offered:
        return "not offered to this account"
    return None


def free_models(catalog, offered):
    out = []
    for mid in zen_models(catalog):
        if free_reason(mid, catalog, offered) is None:
            out.append(mid)
    return sorted(out, key=lambda i: zen_models(catalog)[i].get("release_date", ""), reverse=True)


def choose(catalog, offered, policy, private, source="", age_h=None, today=None):
    warnings, notes = [], []
    free = free_models(catalog, offered)
    if offered is None:
        warnings.append("could not list the models this account is offered (`opencode models` failed); availability is unverified")
    if source == "stale-cache":
        warnings.append(f"the model catalog could not be refreshed; using a cached copy that is {age_h:.0f} h old")
    verified = policy.get("verified")
    if verified:
        try:
            days = ((today or time.time()) - time.mktime(time.strptime(verified, "%Y-%m-%d"))) / 86400
            if days > POLICY_STALE_DAYS:
                warnings.append(f"zen-policy.json was last checked against the Zen docs {days:.0f} days ago; re-check {policy.get('source')}")
        except ValueError:
            pass
    zero = [m for m in policy.get("zero_retention", []) if m in free]
    preferred = policy.get("public_preferred", "big-pickle")
    model = None
    if private:
        model = zero[0] if zero else None
        missing = [m for m in policy.get("zero_retention", []) if m not in free]
        for m in missing:
            warnings.append(f"zero-retention model {m}: {free_reason(m, catalog, offered)}")
        if model:
            notes.append(f"private repository: {model} is free and zero-retention (not used for training)")
        else:
            warnings.append("no free zero-retention Zen model is available for a private repository")
    else:
        why = free_reason(preferred, catalog, offered)
        if why is None:
            model = preferred
            notes.append(f"public repository: {preferred} (free; its data may be used to improve the model, which is fine for public code)")
        else:
            warnings.append(f"{preferred} is not a free Zen option anymore: {why}")
            others = [m for m in free if m != preferred]
            model = (zero[0] if zero else (others[0] if others else None))
            if model:
                notes.append(f"using {model} instead")
    return {"model": model, "private": private, "free_models": free, "zero_retention": zero,
            "warnings": warnings, "notes": notes, "catalog": {"source": source, "age_hours": None if age_h is None else round(age_h, 1)}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("choose", "best"):
        sp = sub.add_parser(name)
        sp.add_argument("--catalog", help="catalog JSON file (tests)")
        sp.add_argument("--offered", help="comma separated ids this account is offered (tests); 'unknown' = could not list")
        sp.add_argument("--policy", default=os.path.join(HERE, "zen-policy.json"))
        sp.add_argument("--no-fetch", action="store_true")
        if name == "choose":
            sp.add_argument("--private", choices=("yes", "no"), required=True)
    a = ap.parse_args(argv)
    # test hooks for shell-level tests: a fixed catalog and a fixed list of offered models
    a.catalog = a.catalog or os.environ.get("AISTACK_ZEN_CATALOG")
    a.offered = a.offered if a.offered is not None else os.environ.get("AISTACK_ZEN_OFFERED")
    try:
        policy = json.load(open(a.policy))
    except (OSError, ValueError):
        policy = {}
    try:
        catalog, source, age = load_catalog(a.catalog, fetch=not a.no_fetch)
    except Exception as e:
        print(json.dumps({"model": None, "warnings": [f"model catalog unavailable: {e}"], "notes": [], "free_models": []}))
        return 2 if a.cmd == "best" else 0
    if a.offered is None:
        offered = offered_ids()
    else:
        offered = None if a.offered == "unknown" else {x for x in a.offered.split(",") if x}
    if a.cmd == "best":
        res = choose(catalog, offered, policy, private=False, source=source, age_h=age)
        if res["model"]:
            print(res["model"])
            return 0
        print("\n".join(res["warnings"]), file=sys.stderr)
        return 1
    res = choose(catalog, offered, policy, private=(a.private == "yes"), source=source, age_h=age)
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main())
