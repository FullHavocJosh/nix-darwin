---
title: Resolve request URLs through Claude MCP before planning
status: approved
author: Josh Rollet
date: 2026-10-14
touches: .config/aistack/ralph_mcp.py, .config/aistack/planner-prompt.md, .config/aistack/claude-fetch.sh, .zshrc_functions_ai
---

## 1. TL;DR

URLs the user types on Jira/Confluence, GitHub or Terraform hosts (terraform.io, developer.hashicorp.com) are read by one small, read-only Claude Code call
(`claude-fetch.sh`) before Lumo drafts and Claude plans. Other URLs stay with Lumo; any URL Lumo cannot open falls back
to the same fetch.

## 2. Problem

`aidev "review https://smartpager.atlassian.net/browse/PLT-5995, and plan our next steps ..."` (2026-10-14): the local
model has no way to open a URL, so it ran `repo_grep PLT-5995` and `repo_grep PLT-5996` and treated code comments as
the ticket. The ticket's "Decisions needed" and "Next" comments never reached the planner. The plan call could not
fix this either: `claude-plan.sh` runs with `--restricted --strict-mcp-config --tools Read,Grep,Glob`, so it has no
MCP servers. This happens for every request that links a ticket, PR or registry page.

Measured on 2026-10-14:

- The claude.ai Atlassian connector loads only when `--restricted` and `--strict-mcp-config` are both off. With
  `--restricted` alone, the call has no MCP servers.
- A headless haiku call with `--tools WebFetch` and no ToolSearch loaded all MCP schemas eagerly: 95k tokens,
  0.30 USD for one Jira issue. With `--tools WebFetch,ToolSearch --setting-sources ""`: 0.03 USD, same content.

## 3. Proposed solution

- `claude-fetch.sh` (new): `claude -p` with haiku (`AISTACK_CLAUDE_FETCH_MODEL`), `--effort low`,
  `--max-budget-usd 0.3` (`AISTACK_CLAUDE_BUDGET_FETCH`), `--tools WebFetch,ToolSearch`, `--setting-sources ""` (no
  hooks, plugins or permission rules), and an `--allowedTools` list of read-only Atlassian, github and terraform tools.
  In `-p` mode every other tool is denied, write tools included.
- `ralph_mcp.py`:
  - `extract_urls`, `mcp_url` (`AISTACK_MCP_URL_HOSTS`, default `atlassian.net,github.com,terraform.io,developer.hashicorp.com`),
    `submitted_urls` (the request plus `AISTACK_REQUEST_URLS`).
  - `resolve_urls`: one fetch call for the URLs not cached in `plan/urls.json`. A page is cached for 6 h; a failure
    for 10 min.
  - `tool_plan` fetches typed MCP-host URLs before Lumo. With no Lumo (`AISTACK_TIER0` not `lumo`), it fetches every
    typed URL. The content goes to Lumo's request and to a `URL CONTENTS` section of the plan prompt.
  - After Lumo, URLs from its `UNREACHABLE: <url>` lines are fetched before the plan call. With no draft at all, the
    remaining typed URLs are fetched too.
  - `LUMO_PROMPT` asks Lumo for those lines.
  - The result gains `urls` and a line in `present`. `billed_calls` includes the fetch.
  - `--fetch-urls PROJECT TEXT` CLI entry for the launcher.
- `.zshrc_functions_ai` (`_aidev_stack`):
  - When the task has URLs, it runs `--fetch-urls` at start and appends the content to pi's first message, so the
    local model's research is aimed at the right code.
  - It passes `AISTACK_REQUEST_URLS` to the bridge.
  - `claude-fetch.sh` joins `need_files`.
- `planner-prompt.md`: hard rule 7. The local model cannot open URLs. It copies them unchanged into the request and
  never treats a ticket-key grep as the ticket.

## 4. Alternatives considered

- **Unrestrict the plan call when a URL is present.** No extra call, but the expensive model pays for the hooks and
  about 8k tokens again, and the hook that denied Glob returns (both measured 2026-10-08). Lumo would also draft
  without the ticket. Rejected.
- **Let Lumo read every URL.** Lumo cannot authenticate to Jira, Confluence or private GitHub repositories.
  Rejected for MCP hosts; kept for other URLs.
- **Pass Atlassian as a `--mcp-config` server under `--strict-mcp-config`.** The connector's OAuth belongs to the
  claude.ai account, and no local token is available. Rejected.

## 5. Cost and billing impact

- **Billed:**
  - A request with no URL: no change.
  - A request with typed MCP-host URLs: one more small call, measured 0.03 USD (haiku). The plan call grows by the
    fetched content, at most 24,000 characters.
  - A URL Lumo could not open: at most one more fetch call.
  - A cached page costs nothing. So the launcher's fetch at start and `ralph_plan`'s fetch are one call.
- **Free:**
  - Lumo gets the fetched content in its request.
  - The local model gets it in its first message.
  - No extra Lumo or local-model calls.

## 6. Backwards compatibility and rollout

- No change for requests without URLs.
- Existing plans, runs and state dirs are unaffected. `plan/urls.json` is new.
- `AISTACK_MCP_URL_HOSTS=` (empty) turns off the MCP-host routing. Typed URLs then go to Lumo, or to the fetch when
  there is no Lumo.
- Revert the PR to remove the feature.
- `claude-fetch.sh` is stowed with the rest of `.config/aistack`. `darwin-rebuild` is not needed, because the
  directory is linked.

## 7. Success criteria

- `python3 .config/aistack/tests/test_plan.py` passes. This includes the URL section: routing, caching, the Lumo
  fallback, the failed fetch and `--fetch-urls`.
- `ralph_mcp.py --fetch-urls` on PLT-5995 and a GitHub PR returns both, with the Jira comments in full (verified
  2026-10-14, 44 s).
- An `aidev` request linking PLT-5995 yields a plan whose tasks follow the ticket's "Next" list.
- Reconsider if a fetch call regularly costs over 0.10 USD or takes over 90 s.

## 8. Open questions

- URLs typed later in the pi session (not with the task) are fetched at `ralph_plan` time only, so the local
  model's research does not see them. A `fetch_url` tool for the local model could close this. Deferred.
