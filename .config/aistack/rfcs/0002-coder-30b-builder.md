---
title: Build with the on-device 30B, escalate to Big Pickle, then Claude; relay without thinking
status: approved
author: Josh Rollet
date: 2026-10-16
touches: .config/aistack/coder_pi.py, .config/aistack/local_edit_mcp.py, .config/aistack/ralph_mcp.py, .config/aistack/ralph_driver.py, .zshrc_functions_ai
---

## 1. TL;DR

aidev's free builder becomes the on-device Qwen3-Coder-30B-A3B (in pi for planned runs, in aider for `aidev -p` /
`--direct`). OpenCode Zen's Big Pickle takes over a task the 30B could not get through verification, where a Zen key
exists; Claude Code stays the billed last resort, the planner and the reviewer; Lumo stays the web source. The 9B relay
in pi (aidev and ainfo) runs with thinking off.

## 2. Problem

- The user's routing (2026-10-16): edits go to the free on-device 30B first, cloud models only when it struggles.
  aidev built with Big Pickle (a cloud model) whenever a Zen key existed, and with billed Claude when not, even on
  hosts that have the 30B. `aidev -p` used Big Pickle, or aider on the 9B without a Zen key.
- The relay is slow. Over 120 requests on the 9B, half the time was prompt processing and half generation, with long
  thinking runs (p90 216 tokens, max 8438). pi's `--thinking off` did nothing: it sends `reasoning_effort`, which
  Qwen3.5's template ignores.

## 3. Proposed solution

- `coder_pi.py` (new): the `coder-30b` Ralph agent (`plugin = "pi"`). Takes local_edit's lock (one 30B job at a time),
  loads the 30B with `local_edit_mcp.ensure_server()`, points pi at it (provider `coder`, 32k context), runs pi with
  Ralph's arguments, then starts `local_edit_mcp.py --stop-when-idle`, which unloads the model after the usual idle
  time. `--hold -- <command>` does the same for aider. Exit 3 when the 30B is not on the host.
- `ralph_mcp.py` / `ralph_driver.py`: an optional escalation agent (`AISTACK_ESCALATE_AGENT`,
  `AISTACK_ESCALATE_ATTEMPTS`, default 1) between the worker and the fallback: worker x2, escalation x1, fallback x1.
- `_aidev_stack`: where the 30B model file exists, worker `coder-30b`, escalation `opencode-pickle` when a Zen model
  was chosen, fallback `claude-work` (billed). Without the 30B, unchanged (Big Pickle, else Claude).
- `_aidev_direct`: where the 30B exists, aider on it (through `coder_pi.py --hold`). A headless edit that changed
  nothing, exited non-zero, or left `AIDEV_TEST_CMD` failing goes on to OpenCode Zen when there is a key.
- Relay: pi's model entry gets `compat.thinkingFormat: "qwen-chat-template"` (thinking reaches the template as
  `chat_template_kwargs.enable_thinking`), and both launchers pass `--thinking ${AISTACK_RELAY_THINKING:-off}`.

## 4. Alternatives considered

- The 30B as the relay too: 2.3x faster generation, but 19 GB that unloads after 2 idle minutes; ainfo idles while
  Claude works, so it would reload (16-25 s) mid-conversation, and it would block local_edit. Not chosen.
- Big Pickle as the relay: not available on the work laptop (no Zen key, compliance), so the stack would differ per host.
- Keep thinking on: measured slower for the same tool calls (section 7).

## 5. Cost and billing impact

- Billed Claude calls: unchanged for planning and review. Building: Claude now comes third instead of second on hosts
  with the 30B, so fewer billed fallback attempts.
- Free calls: Big Pickle builds only what the 30B could not finish. The relay writes fewer tokens (no thinking).

## 6. Backwards compatibility and rollout

Hosts without the 30B (below 32 GB) keep today's tiers. `AISTACK_RELAY_THINKING=on` (any pi level) restores thinking.
`AISTACK_ESCALATE_AGENT` unset gives the old worker -> fallback order. Reverting the PR restores everything.

## 7. Success criteria

- Measured 2026-10-16 (one run each, thinking on -> off): ainfo via Lumo 39 -> 21 s, ainfo investigate 88 -> 41 s,
  aidev research to `ralph_plan` 294 -> 245 s; same tools called, answers as good (one run skipped the first
  `ralph_runs` call). Reconsider if relays start skipping required calls.
- Tests: `test_coder_pi.py`, `test_driver.py` (escalation order), the existing aistack suites.
- A live aidev run on a 32 GB+ host shows `worker=coder-30b escalate=opencode-pickle fallback=claude-work`.

## 8. Open questions

None.
