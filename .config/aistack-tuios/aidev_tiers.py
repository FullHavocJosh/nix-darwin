#!/usr/bin/env python3
"""The aidev builder tier registry: six named tiers, a context size per tier, old builder names kept as aliases.

Stdlib only. Defaults live in DEFAULTS; ~/.config/aidev/tiers.json (or $AIDEV_TIERS_FILE) overrides keys per tier.
"""
import copy
import json
import os

TIER_IDS = ('tier-0', 'tier-1', 'tier-2', 'tier-3', 'tier-4', 'tier-5', 'tier-6')

# The four gateway nodes, numbered by rank: tier-1 is the slowest, tier-4 the fastest (the ranks in the gateway's
# PROXY_GROUPS). Every one is reached through https://llm.rollet.family/auto/v1 as model node-<backend id>.
NODE_TIERS = ('tier-1', 'tier-2', 'tier-3', 'tier-4')
NODE_BACKEND = {'tier-1': 'trashcan', 'tier-2': 'macmini-m1', 'tier-3': 'cait-g14', 'tier-4': 'josh-g14'}
NODES_FASTEST_FIRST = tuple(reversed(NODE_TIERS))

# MAX_OUTPUT_TOKENS: tier-0 runs at about 37 tok/s; the G14 30B runs at about 35 tok/s so 8192 tokens
# is about 235 s and a 400 line file write is about 5000 tokens; do not set lower.
MAX_OUTPUT_TOKENS = {'tier-0': 4096, 'tier-1': 4096, 'tier-2': 8192, 'tier-3': 8192, 'tier-4': 8192}

_URL = 'https://llm.rollet.family/auto/v1'  # the pool; a node-<id> model pins the request to one node


def _node(n, label, ctx):
    bid = NODE_BACKEND[f'tier-{n}']
    return {'pane': f'build-local-tier-{n}', 'label': label, 'kind': 'pi', 'ctx': ctx, 'alias': 'node-' + bid,
            'url': _URL, 'enabled': True, 'min_ram_gb': 0, 'max_tokens': 8192}


DEFAULTS = {
    'tier-0': {'pane': 'build-local-tier-0', 'label': 'local gpt-oss-20b', 'kind': 'pi', 'ctx': 32768,
               'alias': '', 'url': '', 'enabled': True, 'min_ram_gb': 24, 'max_tokens': 4096},
    # The window is the default; the gateway's live window replaces it (aidev_tuios.tiers_live). The TrashCan serves
    # Qwen3.5-35B-A3B (experts in RAM) with a 65536 window and the gateway's plan profile (4096 output tokens).
    'tier-1': dict(_node(1, 'TrashCan 35B-A3B', 65536), max_tokens=4096),
    'tier-2': _node(2, 'Mac mini M1 9B', 65536),
    'tier-3': _node(3, 'Cait G14 9B', 65536),
    'tier-4': _node(4, 'Josh G14 30B', 65536),
    'tier-5': {'pane': 'build-free-tier-5', 'label': 'free cloud', 'kind': 'opencode', 'ctx': 0,
               'alias': '', 'url': '', 'enabled': True, 'min_ram_gb': 0, 'max_tokens': 0},
    'tier-6': {'pane': 'build-billed-tier-6', 'label': 'billed Claude', 'kind': 'claude', 'ctx': 0,
               'alias': '', 'url': '', 'enabled': True, 'min_ram_gb': 0, 'max_tokens': 0},
}

_OLD = {
    'build-semi-local': 'tier-4', 'build-local': 'tier-0', 'build-free': 'tier-5', 'build-billed': 'tier-6',
    'semi-local': 'tier-4', 'local': 'tier-0', 'free': 'tier-5', 'billed': 'tier-6',
    'semi': 'tier-4', 'g14': 'tier-4', '30b': 'tier-0', 'pickle': 'tier-5', 'claude': 'tier-6',
    # pane names from the first renumbering (free cloud tier-3, billed Claude tier-4); the bare ids now mean nodes
    'build-free-tier-3': 'tier-5', 'build-billed-tier-4': 'tier-6',
}


def norm_tier(word):
    """Return 'tier-N' for a tier id, new or old pane name, old kind name or old alias; None otherwise."""
    w = str(word or '').strip().lower()
    if not w:
        return None
    if w in _OLD:
        return _OLD[w]
    for tid in TIER_IDS:
        if w in (tid, tid.replace('-', ''), tid[-1]) or w == DEFAULTS[tid]['pane']:
            return tid
    return None


def tiers_path():
    return os.environ.get('AIDEV_TIERS_FILE') or os.path.join(os.path.expanduser('~'), '.config', 'aidev', 'tiers.json')


def _valid(key, value):
    if key in ('ctx', 'min_ram_gb', 'max_tokens'):
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0
    if key == 'enabled':
        return isinstance(value, bool)
    return isinstance(value, str)


def load_tiers(path=None):
    """DEFAULTS deep-copied and merged with the JSON file; bad ids, keys, values or files are ignored."""
    tiers = copy.deepcopy(DEFAULTS)
    try:
        with open(path or tiers_path()) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return tiers
    if not isinstance(data, dict):
        return tiers
    for tid, over in data.items():
        if tid not in tiers or not isinstance(over, dict):
            continue
        for key, value in over.items():
            if key in tiers[tid] and _valid(key, value):
                tiers[tid][key] = value
    return tiers


def limits_for_ctx(ctx):
    """Task limits for a context window in tokens; None when the window is unknown or unlimited."""
    if ctx <= 0:
        return None
    room = ctx - 12000
    return {'max_read': max(0, room * 3), 'max_chars': max(2000, round(room * 0.08)), 'max_files': 3}


def estimate_tokens(desc_chars, file_bytes):
    """Rough prompt size in tokens: description, files and a fixed overhead for the system prompt and tools."""
    return int(desc_chars / 3.5 + file_bytes / 4 + 12000)


def _usable(tid, state, tiers, min_tier):
    """True when the tier is enabled, online and not below min_tier; tier-5 and tier-6 count as enabled."""
    if int(tid[-1]) < min_tier:
        return False
    if tid not in ('tier-5', 'tier-6') and not tiers.get(tid, {}).get('enabled'):
        return False
    return bool(state.get(tid, {}).get('online'))


def select_tier(need, state, tiers, min_tier=0):
    """Pick the builder tier for a task of `need` tokens; returns (tier_id or None, reason).

    state maps tier_id to {'online': bool, 'idle': bool}; a missing entry means offline and busy.
    None means the task must be split.
    """
    def ctx(tid):
        return tiers[tid]['ctx']

    # Fastest node first (the gateway rank: tier-4, 3, 2, 1); an idle node wins over a busy faster one.
    eligible = [t for t in NODES_FASTEST_FIRST if _usable(t, state, tiers, min_tier) and ctx(t) >= need]
    if eligible:
        idle = [t for t in eligible if state.get(t, {}).get('idle')]
        pool = idle or eligible
        why = 'idle' if idle else 'all busy'
        return pool[0], f'{pool[0]}: fastest fit, {why}'
    # a node whose window is under the pi overhead (the TrashCan at 8192) cannot hold any task, so it neither takes
    # the split verdict nor blocks tier-0 and the cloud tiers
    usable = [t for t in NODES_FASTEST_FIRST if _usable(t, state, tiers, min_tier) and ctx(t) > PI_OVERHEAD]
    if usable:
        top = usable[0]
        return None, f"split: need {need} tokens, {top} ctx {ctx(top)}"
    if _usable('tier-0', state, tiers, min_tier) and ctx('tier-0') >= need:
        return 'tier-0', 'tier-0: build hosts offline'
    if _usable('tier-5', state, tiers, min_tier):
        return 'tier-5', 'tier-5: no local tier fits'
    return 'tier-6', 'tier-6: last resort'


def next_tier_id(tier_id, state, tiers):
    """The tier to escalate to after tier_id fails; None for tier-6 and unknown ids.

    Dispatch order: the nodes from fastest to slowest, then tier-0 (only when online), tier-5, tier-6."""
    if tier_id in NODE_TIERS or tier_id == 'tier-0':
        if tier_id in NODE_TIERS:
            slower = [t for t in NODES_FASTEST_FIRST if int(t[-1]) < int(tier_id[-1])]
            for t in slower:
                if _usable(t, state, tiers, 0):
                    return t
            if _usable('tier-0', state, tiers, 0):
                return 'tier-0'
        target = 'tier-5'
    elif tier_id == 'tier-5':
        target = 'tier-6'
    else:
        return None
    if target == 'tier-5' and not state.get('tier-5', {}).get('online'):
        return 'tier-6'
    return target


def max_output_tokens(tier_id, tiers=None):
    """Return the max output tokens for a tier. Uses the given tiers dict, or DEFAULTS, or MAX_OUTPUT_TOKENS.
    Returns 8192 when missing."""
    if tiers is None:
        tiers = DEFAULTS
    if tier_id in tiers and 'max_tokens' in tiers[tier_id]:
        return tiers[tier_id]['max_tokens']
    return MAX_OUTPUT_TOKENS.get(tier_id, 8192)


# Measured 2026-11-24 through each host's own llama-server: cold prompt of about 20K tokens, prompt cache off.
# pp is prompt tokens per second, tg generation tokens per second at that depth. TrashCan is the ranking-table
# figure measured after the Nobara 44 upgrade.
SPEED = {
    'tier-4': {'pp': 945, 'tg': 47, 'note': 'Josh G14, Qwen3-Coder-30B'},
    'tier-3': {'pp': 2829, 'tg': 41, 'note': 'Cait G14, Qwen3.5-9B'},
    'tier-2': {'pp': 95, 'tg': 6, 'note': 'Mac mini M1, Qwen3.5-9B'},
    'tier-1': {'pp': 45, 'tg': 7, 'note': 'TrashCan, Qwen3.5-35B-A3B, experts in RAM (measured 2026-11-25 at 22K tokens deep)'},
}
PI_OVERHEAD = 12000  # tokens pi adds before the task text
FIT_HEADROOM = 0.25  # a tier is only recommended when at least this share of its window stays free


def fit_rows(need, out, tiers, state, speed=None):
    """Which tiers can take a task of `need` prompt tokens and `out` output tokens, and which one to use.

    Returns (rows, best_id or None, why). Each row: id, ctx, online, fits, headroom (share of ctx left, None for
    an unbounded cloud tier), est_s (prompt/pp + out/tg when the speed is known, else None). best is the online tier
    with the shortest est_s among those that fit with FIT_HEADROOM; with no known speed the largest window wins. A
    local tier is preferred over tier-5 and tier-6; None means split the task.
    """
    speed = SPEED if speed is None else speed
    rows = []
    for tid in TIER_IDS:
        cfg = tiers[tid]
        ctx = cfg['ctx']
        online = bool(state.get(tid, {}).get('online')) and (tid in ('tier-5', 'tier-6') or cfg['enabled'])
        total = need + out
        fits = ctx <= 0 or total <= ctx
        headroom = None if ctx <= 0 else round((ctx - total) / ctx, 2)
        sp = speed.get(tid)
        est = round(need / sp['pp'] + out / sp['tg'], 1) if sp and sp['pp'] and sp['tg'] else None
        rows.append({'id': tid, 'ctx': ctx or None, 'online': online, 'fits': fits, 'headroom': headroom, 'est_s': est})
    local = [r for r in rows if r['id'] not in ('tier-5', 'tier-6') and r['online'] and r['fits']
             and r['headroom'] is not None and r['headroom'] >= FIT_HEADROOM]
    if local:
        timed = [r for r in local if r['est_s'] is not None]
        best = min(timed, key=lambda r: r['est_s']) if timed else max(local, key=lambda r: r['ctx'])
        return rows, best['id'], f"{best['id']}: fits with {round(best['headroom'] * 100)}% of its window free"
    tight = [r for r in rows if r['id'] not in ('tier-5', 'tier-6') and r['online'] and r['fits']]
    if tight:
        best = max(tight, key=lambda r: r['ctx'])
        return rows, best['id'], f"{best['id']}: fits but under {round(FIT_HEADROOM * 100)}% of its window is left; trim the task"
    for tid in ('tier-5', 'tier-6'):
        if next(r for r in rows if r['id'] == tid)['online']:
            return rows, tid, f"{tid}: no local tier has the window for {need + out} tokens"
    return rows, None, f"split: no online tier has the window for {need + out} tokens"

