---
title: One ~/.ai directory for every AI tool, with cross-tool RFCs
status: approved
author: jrollet
date: 2026-10-16
touches: .config/aistack/ai_home.py, .config/ainfo/ainfo_mcp.py, .config/aistack/ralph_mcp.py, .config/aistack/advisor_hook.py, .config/aistack/edit_router_hook.py, .config/aistack/coder_pi.py, .config/aistack/local_edit_mcp.py, .config/aistack/planner-prompt.md
---

<!-- status is one of: draft, review, approved, implemented -->

## 1. TL;DR

Every file ainfo, aidev and ai write moves under `~/.ai` (`AI_HOME`). A new `~/.ai/rfcs/` holds RFCs that any model
may write from any tool, so work found in one tool (for example ainfo) can be picked up later in another (`ai`,
`aidev --rfc`, OpenCode, Claude Code).

## 2. Problem

Output is spread over seven places: `~/.ainfo/<project>`, `~/.aistack/<project>`, `~/.cache/aistack-pi-ai`,
`~/.cache/nix-darwin-ai`, `~/.cache/aistack-pi-coder`, `~/.cache/local-edit`, `~/.cache/aidev-aider`, plus the
advisor and edit-router state in `~/.cache`. Handoffs go to a session scratchpad that disappears.

There is no shared place to leave work for later. An ainfo session that finds something worth doing ends with advice
in `~/.ainfo/<project>/advice-NNN.md`, which nothing else reads. ainfo's Claude cannot write files at all; ai's Claude
runs under advisor mode, which only allows the scratchpad, memory and plans; OpenCode asks before every external path.

## 3. Proposed solution

### Layout

```
~/.ai/                         AI_HOME
  README.md                    the layout and the RFC format (linked from .config/ai/README.md)
  rfc-template.md              linked from .config/ai/rfc-template.md
  rfcs/YYYY-MM-DD-slug.md      RFCs: any model writes, any tool starts from one
  handoffs/YYYY-MM-DD-slug/    /aidev-handoff output (prd.json, verify.json)
  ainfo/<project key>/         was ~/.ainfo (AINFO_HOME still overrides)
  aidev/<project key>/         was ~/.aistack (AISTACK_HOME still overrides)
  ai/                          was ~/.cache/aistack-pi-ai
  cache/aistack-pi/            was ~/.cache/nix-darwin-ai/aistack-pi
  cache/aistack-pi-coder/      was ~/.cache/aistack-pi-coder
  cache/local-edit/            was ~/.cache/local-edit
  cache/aidev-aider/           was ~/.cache/aidev-aider
  guard/advisor/               was ~/.cache/advisor
  guard/edit-router/           was ~/.cache/edit-router
```

Every existing override variable keeps working; only defaults change. `AI_HOME` moves the whole tree.

### Write access

Models may write anywhere under `~/.ai` except `~/.ai/guard/`, which holds the advisor on/off flags and the
edit-router counters. Letting a model write there would let it switch off the hooks that restrict it.

- `advisor_hook.py` `own_file()`: allows `~/.ai/**` minus `~/.ai/guard/**` (resolved paths).
- Claude Code settings (activation): `permissions.additionalDirectories: ["~/.ai"]`, allow `Edit(~/.ai/**)`, deny
  `Edit(~/.ai/guard/**)`. An `Edit` rule covers Write too.
- OpenCode: `external_directory` and `edit` allow `~/.ai/**`, deny `~/.ai/guard/**` (last match wins), for the
  global, advisor and build permissions.
- ainfo: Claude keeps no write tool. The Seatbelt profile swaps `~/.ainfo` for `~/.ai` and denies `~/.ai/guard`.

### RFC format

`.config/ai/rfc-template.md`: the aistack template's frontmatter plus `source` (tool/model that wrote it) and
`repo` (absolute path of the project it is about), and seven sections written for a reader with no session context. Status: `draft | ready | in-progress | done | dropped`. `ai_home.py`
`write_rfc()` fills missing keys, names the file `YYYY-MM-DD-slug.md` and never overwrites (`-2`, `-3`).

### Per tool

- ainfo: new bridge tool `ainfo_rfc(request)`. One Claude call (resuming the session, so it has the research)
  writes the RFC as text; the bridge redacts it and saves it with `write_rfc()`.
- aidev: new bridge tool `ralph_save_rfc(title, body)` for the relay model; the bridge appends the current
  `plan/PLAN.txt` when one exists. `aidev --rfc FILE` starts the planner with the RFC as the request (a bare name is
  looked up in `~/.ai/rfcs`).
- ai, Claude Code, OpenCode: write with their own Write/Edit tools, as `~/.claude/CLAUDE.md` and
  `.config/opencode/model-routing.md` say.
- /aidev-handoff writes to `~/.ai/handoffs/YYYY-MM-DD-slug/`.

## 4. Alternatives considered

- RFCs only, state stays put. Smaller change, but output stays in seven places; rejected by the user.
- Every model may write all of `~/.ai`, including guard state. Rejected: a model could create
  `~/.ai/guard/advisor/<session>.off` and turn advisor mode off for itself.
- Give ainfo's Claude a Write tool limited to `~/.ai/rfcs`. Rejected: ainfo's guarantee is that its Claude cannot
  write; the bridge writing Claude's text gives the same result.
- Numbered RFCs (`NNNN-slug.md`). Rejected: two sessions writing at once race for the next number.

## 5. Cost and billing impact

- Billed Claude calls: none added to existing flows. `ainfo_rfc` is one billed call when the user asks for an RFC,
  under the same per-call budget (`AINFO_CLAUDE_BUDGET_USD`).
- Free calls: `ralph_save_rfc` is a file write by the bridge; no model call.

## 6. Backwards compatibility and rollout

Activation moves each old directory to its new place once (when the new one does not exist) and leaves a symlink at
the old path, so running jobs, old run configs and scripts that hard-code the old path keep working. Revert: remove
the symlinks and move the directories back; the old defaults return with the revert of this change.

## 7. Success criteria

- `python3 .config/aistack/tests/test_advisor_hook.py` passes, with new cases: a Write under `~/.ai/rfcs` is left to
  Claude Code, a Write under `~/.ai/guard` is refused.
- `python3 .config/aistack/tests/test_ai_home.py` passes: names, frontmatter fill, no overwrite.
- After `darwin-rebuild switch`: `~/.ai/{rfcs,handoffs,guard}` exist, `~/.ainfo` and `~/.aistack` are symlinks into
  `~/.ai`, and an ainfo session can save an RFC that `aidev --rfc <name>` then starts from.

## 8. Open questions

None.
