# aidev

aidev is the planner/runner stack in `.config/aistack/`. A person talks to a small **local model in pi**; the
local model finds the relevant code, hands it to stronger models, and relays what comes back. Claude Code writes a
plan, a free coding agent builds it task by task, the harness decides a task is done only when that task's verify
commands exit 0, and Claude Code reviews the whole result once. Everything this document describes is what the
files in `.config/aistack/` show: `ralph_mcp.py` (the MCP bridge and tools used by the chat agent), `ralph_driver.py`
(the detached run driver), `planner-prompt.md` (the local model's prompt), the shell agent wrappers
(`claude-plan.sh`, `claude-fetch.sh`, `claude-review.sh`, `claude-work.sh`, `opencode-auto.sh`), the templates
(`task-template.hbs`, `review-template.hbs`), `zen_models.py`, and the RFC tooling (`rfc_check.py`,
`rfc-template.md`, `rfcs/`).

## Overview

- The chat agent (pi) is a small **local model**, free. It does **not** answer the user's request itself and has no
  tool that writes files. Its only ways to act are the `ralph_*` tools in `ralph_mcp.py`.
- `ralph_plan` gives one billed Claude Code call that writes `prd.json` and `verify.json`. The local model does the
  research for free and passes a brief plus the files that matter; the tool inlines the files so the local model
  never has to copy code through its own output.
- `ralph_run` starts `ralph_driver.py` in the background: a worker builds each task, the harness runs the verify
  commands, failures are retried and then escalated, and a read-only reviewer checks the result. The local model
  follows the run with `ralph_status` and relays events.
- Nothing aistack-related is written into the repository. Plans, runs, questions, reviews and Ralph's own state live
  in the **state dir** (`AISTACK_STATE_DIR`, default `~/.aistack/<project key>`). Only the agents' code changes land
  in the work dir (a git worktree, or the project itself).
- Safety: the bridge only works inside `RALPH_MCP_ROOTS` (colon-separated). Agent names come from the environment the
  launcher sets, never from tool arguments.

## Roles

The models that take part, from `planner-prompt.md` and the code:

- **Local model in pi (tier 0, free).** The coordinator. It finds code with `repo_tree` / `repo_read` / `repo_grep`,
  calls tools, and relays results. It never writes its own evaluation, findings, recommendations or plan, and it
  cannot create a PR, write specs or make a roadmap. It has no file-writing tool; the plan changes only through
  `ralph_update_task`.
- **Lumo (tier 0, free).** Proton's cloud assistant, reached through lumo-tamer. It can look things up online.
  `ralph_plan` asks it for a draft (with sources) before Claude plans; the local model does not call it directly
  when `AISTACK_TIER0=lumo`. When Lumo is unreachable the launcher sets `AISTACK_TIER0=local`
  (`planner-tier0-local.md`) and planning continues without a draft. `planner-tier0-lumo.md` is the tier-0 label
  shown when Lumo is reachable.
- **Claude Code (plan and review, billed).** `claude-plan.sh` writes the plan in **one** billed call (`ralph_plan`)
  and `claude-review.sh` reviews the whole result **once** at the end. `claude-work.sh` is the billed fallback agent
  used when a task keeps failing.
- **Worker (builder, free).** Builds one task per agent session. The default is `opencode-pickle`
  (`AISTACK_WORKER_AGENT`), the free OpenCode Zen model; `opencode-auto.sh` runs `opencode run --auto` for it, and
  `zen_models.py` picks the free Zen model (tier 1).
- **Fallback (`claude-work`, billed).** Used after the worker's attempts are exhausted, when a task keeps failing
  verification (`AISTACK_FALLBACK_AGENT`).
- **Harness.** The `ralph_driver.py` loop decides a task is done: a task counts as `verified` only when its verify
  commands exit 0. Ralph's own completion marker alone never counts.

## Flow

### 1. `ralph_runs`

The local model's first call is `ralph_runs`, listing the runs in the project. If one is running or waiting for the
user it says so and offers to follow it; otherwise it goes on to research. One run at a time per project.

### 2. Research (16-call budget, `AISTACK_RESEARCH_CALLS`)

`repo_tree` (whole project two levels deep by default), `repo_read` (400 lines / 24 000 chars per call) and
`repo_grep` (at most 60 matches) are the only ways the local model looks at the project. Every call counts against
`AISTACK_RESEARCH_CALLS` (default **16**). Past the budget the tools refuse with `calls_left: 0` and say to call
`ralph_plan` now. Each call is logged to `research-calls.jsonl` (see State dir). The budget resets to 0 when the
plan exists or when Claude asks for more, so a fresh question gets its own small budget.

### 3. `ralph_plan` (Claude writes the plan, one billed call)

The local model calls `ralph_plan` once with `request` (the user's words plus their answers), `brief`
(plain text, at most 16 000 characters, only what was seen in files) and `files` (up to 12 entries). `ralph_plan`
consults Lumo automatically when it is reachable and no draft was passed in, inlines the files, and runs
`claude-plan.sh` once (`AISTACK_PLAN_TIMEOUT_S`, default 280 s). Claude returns `prd.json` and `verify.json`; the tool
writes them to the plan dir, records a `PLANNED` verdict in `plan-review.json`, and writes the finished text to
`PLAN.txt`.

URLs in the request (RFC 0001): the local model cannot open them. URLs the user typed on `atlassian.net`,
`github.com`, `terraform.io` or `developer.hashicorp.com` (`AISTACK_MCP_URL_HOSTS`) are read by `claude-fetch.sh` before Lumo drafts: one small
billed call (haiku, read-only Atlassian connector, github and terraform MCP tools, WebFetch) that returns each page
close to verbatim. Lumo and the plan call both get the content. Other URLs are left to Lumo, which browses; a URL
Lumo reports with an `UNREACHABLE: <url>` line, and every typed URL when there is no Lumo draft, goes to the same fetch
before the plan call. When the URLs come with the task (`aidev <words with a URL>`), the launcher runs the fetch at
start (`ralph_mcp.py --fetch-urls`) and hands the content to the local model, so its research is aimed at the right
code; `ralph_plan` reuses that result from `plan/urls.json`. `AISTACK_REQUEST_URLS` keeps the typed URLs when the
local model rewords the request. A failed fetch never stops the plan: Claude is told the URL could not be read, and
the result's `urls` field and the plan text say which.

Results:

- `ok=true`: the plan is valid; the local model shows `present` verbatim in a code block and asks the user to change
  something or start.
- `ok=false` with `problems`: the plan is saved but invalid (see Troubleshooting).
- `ok=false` with `needs_more`: Claude asked for more (see Troubleshooting).
- `ok=false` with `files_need_ranges`: nothing was sent yet (see Troubleshooting).
- `already_planned=true`: an earlier plan exists (see Troubleshooting).

### 4. `present` / `ralph_update_task` / `ralph_validate_plan`

The tool returns `present`, the finished text for the user with every task, its acceptance criteria, verify commands,
Claude's notes and what happened with Lumo. The local model copies it into a code block and adds only the single
line "Change something, or start?".

- **`ralph_validate_plan`** re-checks `prd.json` / `verify.json` and returns a `plan_hash` and `plan_dir`.
- **`ralph_update_task`** changes ONE task (or adds/removes one): `task_id` plus only the fields that change
  (`title`, `description`, `acceptanceCriteria`, `priority`, `dependsOn`, `verify` = list of commands; `remove=true`
  deletes). It is free (no model) and is the only way to edit the plan. It returns the validation result and the new
  `plan_hash`.
- A different approach or new scope is `ralph_plan` with `replan=true` (another billed call). Nothing starts until
  the user clearly says to.

### 5. `ralph_run` (worktree and draft PR)

`ralph_run` needs the latest `plan_hash` and is called only after the user confirms the plan. In a main checkout
(`AISTACK_WORKTREE_MODE=create`) it first creates a git worktree and a draft PR through `gpr` (about 15 s) and the
agents work there; later runs reuse the worktree while it exists. Elsewhere the project itself is the work dir. The
result reports `work_dir`, `worktree_created`, `pr_url`, `worker`, `fallback` and `reviewer`. It writes
`runs/<run_id>/config.json` and starts `ralph_driver.py` detached. The local model follows with `ralph_status`
(`wait_s` up to 45, passing `since=<last_seq>`) and relays each batch of new events. When `state` is `waiting_user`
it quotes the question or findings and calls `ralph_respond` with exactly what the user decided.

### 6. Verify (the harness decides)

`ralph_driver.py` works the plan task by task in dependency and priority order. For each task it runs the worker for
`AISTACK_WORKER_ATTEMPTS` attempts (default 2), then the fallback for `AISTACK_FALLBACK_ATTEMPTS` (default 1). After
each attempt the harness runs the task's verify commands with `shlex.split` and **no shell** (so a command with an
unquoted `; & | < >` backtick or `$()` is refused). A task is `verified` only when every command exits 0. A failed
attempt feeds the output back as guidance; when all agents fail the task is `blocked` and the run pauses for the
user (retry with guidance, skip, or abort). An agent can ask a question by writing a question file; the run pauses,
surfaces it, and resumes with the user's answer (a question is not counted as a failed attempt).

### 7. Review

After the work phase, the read-only reviewer checks every verified task for security, accuracy and completeness and
writes a report whose first line is `Verdict: PASS` or `Verdict: FAIL`. `AISTACK_REVIEW_MODE` defaults to `batch`:
**one** review call covers the whole run. `each` reviews one task per call; `off` skips review. If a review fails the
run pauses for the user to rework (re-run the task with the findings) or accept it as is.

## Handoff from an interactive Claude Code session

When a build was worked out in a normal Claude Code session, that session already holds the context, so pi's research
and the billed `ralph_plan` call add nothing. `/aidev-handoff` (`.config/aistack/aidev-handoff.md`, linked into
`~/.claude/commands` by activation) has Claude write `prd.json` and `verify.json` with the same rules as `PLAN_PROMPT`,
show them to the user, and run `aidev --handoff <dir>`:

- The launcher does its usual setup (tier 1 choice, Ralph config, worktree mode) but skips the local model and Lumo,
  then calls `ralph_mcp.py --handoff <project> <dir>`.
- `--handoff` refuses while a run of the project is active, validates the plan (same `problems` as `ralph_validate_plan`),
  writes it to the plan dir, records it in `plan-review.json` with `source: claude-code-session`, and starts the run
  exactly like `ralph_run` (worktree and draft PR through `gpr` in a main checkout). It prints one JSON object.
- With no free tier-1 model it refuses unless `AISTACK_ASSUME_YES=1`: it usually runs from Claude Code's shell, where
  nobody answers the billing question.
- The session then stops; `aidev` in the project follows the run through pi like any other.

### Delegating one edit

`/delegate` (`.config/aistack/delegate.md`) is the small version of the handoff: for one large, mechanical, cheaply
verified edit, Claude writes a spec, runs `aidev -p` (OpenCode Zen, `opencode run --auto`), and reviews only the
verify result and `git diff --stat`. Small or subtle edits stay with Claude: dispatch plus review costs about as many
turns as making a small edit directly. Local Qwen is not used for this: on the same 10-line edit it took 152 s and
missed part of the spec, where Big Pickle took 83 s and matched it.

## Cost model

- A **normal run has exactly two billed Claude calls**: the plan (`ralph_plan`) and the final review. Everything the
  local model does, Lumo, and the free worker are not billed.
- `ralph_plan` with a plan from an earlier session returns `already_planned` with `billed_calls: 0`. Claude asking
  for more detail costs one call (`billed_calls: 1`), and the follow-up plan call is a second billed call.
- **URLs** on MCP hosts add one small billed fetch call (haiku, measured about 0.03 USD for one Jira issue); a URL
  Lumo could not open can add a second. A cached page (`plan/urls.json`, 6 hours) is not fetched again.
- **Replan** (`ralph_plan` with `replan=true`) adds one billed call.
- **Rework** (re-run a task whose review failed) adds a review call.
- **Retry** (re-run a blocked task, or escalate to the billed fallback) can add a billed call.
- The local model never chooses rework, retry, replan or abort for the user: each can cost another billed call, so it
  offers the option with that note and lets the user decide.
- The billed calls are spent through Claude Code wrappers that cap cost per call: `AISTACK_CLAUDE_BUDGET_PLAN`
  (default 1.5 USD), `AISTACK_CLAUDE_BUDGET_REVIEW` (1.5), `AISTACK_CLAUDE_BUDGET_WORK` (3),
  `AISTACK_CLAUDE_MODEL` (default `sonnet`) and `AISTACK_CLAUDE_EFFORT` (default `medium`).

## File rules for `ralph_plan`

Files are sent to Lumo and Claude as **excerpts**, not by the local model copying code. `ralph_plan` accepts:

- **At most 12 entries** (`files` over the limit are dropped; `LUMO_FILES_MAX = 12`).
- Each entry is a path, optionally with a line range `path/to/file.py:40-120` (for example `lib/a.py:40-120`).
- Values chosen from `lumo_readable`: a file **over 24 000 bytes** (`LUMO_FILE_MAX`) is refused unless a line range
  is given. A range may be at most **200 lines** (`RANGE_MAX_LINES`); a whole file is accepted only when it is under
  **120 lines** (`FILE_WHOLE_MAX_LINES`), and a "range" that covers nearly the whole (≥ 80 %) of a long file counts
  as a whole file and is refused.
- **Secrets are denied**: a name-based deny list refuses anything under `.git`, `node_modules`, `.terraform`,
  `secrets`, `.ssh`, `.gnupg`, `.aistack`, `.ralph-tui`, or matching `.env*`, `*.tfvars`, `*.tfstate*`, `*.pem`,
  `*.key`, `*.p12`, `*.pfx`, `id_rsa*`, `id_ed25519*`, `*kubeconfig*`, `*.age`, `*.sops.*`, `*secret*`,
  `*credential*`, `*.kdbx`, `.doppler*`, `.netrc`, `*.token`. A path outside the project is refused too.
- The total sent to Claude is capped at **24 000 characters** (`PLAN_FILES_TOTAL_MAX`); each entry is cut at about
  **7 000 characters** (`PLAN_FILE_ENTRY_MAX`). Entries are taken in order until the limit, so put the files the
  request is about first and documentation last. Anything skipped, truncated or sent only in part is reported in the
  result (`files_skipped`, `truncated`, `trimmed`).

## State dir

The state dir is `AISTACK_STATE_DIR` when set, else `~/.aistack/<basename(project)>-<sha1(project)[:10]>` (with
`AISTACK_HOME` defaulting to `~/.aistack`). It is outside the repository and holds everything (`plan_dir` is
`<state>/plan`, `runs_dir` is `<state>/runs`):

- **`plan/prd.json`** — the plan: `name`, optional `title` (the PR title), optional `type` (`feat`/`fix`),
  `description`, and `userStories` (each with `id`, `title`, `description`, `acceptanceCriteria`, `priority`,
  `passes` always `false`, `dependsOn`).
- **`plan/verify.json`** — maps each task id to at least one verify command; every task must have one, commands run
  without a shell, and an id that is not a task id is an error.
- **`plan/PLAN.txt`** — the `present` text shown to the user (saved on every validate/change).
- **`plan/plan-meta.json`** — Claude's notes and the status lines (Lumo, skipped/trimmed files) reshown after every
  change.
- **`plan-review.json`** — the plan's recorded source and verdict (`verdict: PLANNED`, `source: claude-plan`,
  `plan_hash`, `request`, `ts`); `ralph_run` requires a verdict here unless `skip_plan_review` is passed.
- **`research-calls.jsonl`** — one JSON line per `repo_tree` / `repo_read` / `repo_grep` call, including calls the
  budget refuses. Only the arguments are logged, never a file's contents, so no secret can leak into the log. Fields:
  - `ts` — UTC ISO-8601 timestamp (`...Z`).
  - `tool` — the tool function name without the `tool_` prefix (`repo_tree`, `repo_read`, `repo_grep`).
  - `args` — the call's arguments (stringified, values cut to 200 chars); `project_dir` is never included.
  - `calls_left` — research calls remaining after this call (0 for a refused call).
  - `ok` — whether the call worked.
  - `bytes` — `len(json.dumps(result))`.
- **`plan/urls.json`**: the fetched URLs, `{url: {ok, content, ts}}`; a page is reused for `AISTACK_URL_CACHE_S`, a
  failure for 10 minutes.
- Other files the code writes: `plan/need.json` (Claude's questions, removed after the final attempt),
  `plan/claude-plan.raw.txt` (when Claude returned no plan), `project.json` (work dir, branch, PR url), and under
  `runs/<run_id>/`: `state.json`, `config.json`, `events.jsonl`, `control.jsonl`, `driver.log`, plus `tasks/` and
  `logs/`. The bridge also keeps `questions/`, `reviews/`, `progress.md`, `ralph/` and `iterations/`.

## Settings

All are optional unless noted; the default is the code's fallback. Every name below is read somewhere in
`.config/aistack/`.

| Variable                                 | Default                                                         | Meaning                                                                                     |
| ---------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `RALPH_MCP_ROOTS`                        | _(none; required)_                                              | Colon-separated roots the bridge may run in. Without it the bridge refuses to run anywhere. |
| `AISTACK_STATE_DIR`                      | `~/.aistack/<project>-<hash>`                                   | Where all aistack state lives.                                                              |
| `AISTACK_HOME`                           | `~/.aistack`                                                    | Parent of the default state dir.                                                            |
| `AISTACK_RESEARCH_CALLS`                 | `16`                                                            | Research budget for `repo_tree` / `repo_read` / `repo_grep`.                                |
| `AISTACK_TIER0`                          | _(unset)_                                                       | `lumo` lets `ralph_plan` consult Lumo; `local` skips it because Lumo was unreachable.       |
| `AISTACK_TIERS`                          | _(unset)_                                                       | Free text about tiers put in the draft PR body.                                             |
| `AISTACK_WORKTREE_MODE`                  | _(unset)_                                                       | `create` makes `ralph_run` create a git worktree + draft PR in a main checkout.             |
| `AISTACK_WORKTREE_CMD`                   | `gpr_func --auto ...`                                           | Command that creates the worktree/PR; its last stdout line is JSON.                         |
| `AISTACK_PLAN_CMD`                       | `claude-plan.sh -p <prompt>`                                    | The planning call.                                                                          |
| `AISTACK_PLAN_TIMEOUT_S`                 | `280`                                                           | Timeout for the planning call.                                                              |
| `AISTACK_FETCH_CMD`                      | `claude-fetch.sh -p <prompt>`                                   | The URL fetch call.                                                                         |
| `AISTACK_FETCH_TIMEOUT_S`                | `180`                                                           | Timeout for the URL fetch call.                                                             |
| `AISTACK_MCP_URL_HOSTS`                  | `atlassian.net,github.com,terraform.io,developer.hashicorp.com` | Typed URLs on these domains (and subdomains) are fetched by Claude, not left to Lumo.       |
| `AISTACK_URL_CACHE_S`                    | `21600`                                                         | Seconds a fetched page is reused.                                                           |
| `AISTACK_REQUEST_URLS`                   | _(set by the launcher)_                                         | The URLs typed with the task, for `ralph_plan`.                                             |
| `AISTACK_CLAUDE_FETCH_MODEL`             | `haiku`                                                         | Model for the URL fetch call.                                                               |
| `AISTACK_CLAUDE_BUDGET_FETCH`            | `0.3`                                                           | USD cap for the URL fetch call.                                                             |
| `AISTACK_PLAN_WHOLE_FILE_LINES`          | `120`                                                           | A whole file is accepted only under this many lines.                                        |
| `AISTACK_PLAN_RANGE_LINES`               | `200`                                                           | Most lines one `files` range may cover.                                                     |
| `AISTACK_PLAN_FILES_CHARS`               | `24000`                                                         | Total characters of files sent to Claude.                                                   |
| `AISTACK_PLAN_ENTRY_CHARS`               | `7000`                                                          | Most characters one `files` entry may use.                                                  |
| `AISTACK_LUMO_CONDENSE_AT`               | `12000`                                                         | A Lumo draft over this length is sent back to be shortened.                                 |
| `AISTACK_LUMO_ROUNDS`                    | `4`                                                             | Most rounds of Lumo asking for more files.                                                  |
| `AISTACK_LUMO_LOOP_S`                    | `480`                                                           | Most seconds the Lumo loop may run.                                                         |
| `AISTACK_LUMO_MODEL`                     | `lumo`                                                          | Model name sent to the Lumo endpoint.                                                       |
| `AISTACK_LUMO_RESOLVER`                  | `llm`                                                           | How vague Lumo requests are resolved (through the local model).                             |
| `AISTACK_LUMO_PLANNER_LIB`               | _(searched)_                                                    | Path to `lumo_planner.py` used as a library.                                                |
| `AISTACK_TAMER_URL` / `AISTACK_LUMO_URL` | _(tried in order)_                                              | Pin one Lumo endpoint.                                                                      |
| `AISTACK_TAMER_KEY` / `AISTACK_LUMO_KEY` | _(empty)_                                                       | Key for the pinned endpoint.                                                                |
| `AISTACK_TAMER_MINI_URL`                 | `http://macminim1.rollet.family:3003/v1`                        | MacMiniM1's tamer.                                                                          |
| `AISTACK_TAMER_MINI_KEY`                 | _(Doppler)_                                                     | Key for the Mini's tamer.                                                                   |
| `AISTACK_LUMO_PUBLIC_URL`                | `https://lumo.rollet.family/v1`                                 | Public endpoint.                                                                            |
| `AISTACK_LUMO_PUBLIC_KEY`                | _(Doppler)_                                                     | Key for the public endpoint.                                                                |
| `AISTACK_PLAN_REVIEW`                    | `on`                                                            | `off` disables the plan-review gate in `ralph_run`.                                         |
| `AISTACK_WORKER_AGENT`                   | `opencode-pickle`                                               | The (free) worker agent.                                                                    |
| `AISTACK_FALLBACK_AGENT`                 | `claude-work`                                                   | The (billed) fallback agent.                                                                |
| `AISTACK_REVIEW_AGENT`                   | `claude-review`                                                 | The reviewer agent.                                                                         |
| `AISTACK_WORKER_ATTEMPTS`                | `2`                                                             | Worker attempts per task.                                                                   |
| `AISTACK_FALLBACK_ATTEMPTS`              | `1`                                                             | Fallback attempts per task.                                                                 |
| `AISTACK_ATTEMPT_TIMEOUT_S`              | `1500`                                                          | Timeout for one agent attempt.                                                              |
| `AISTACK_VERIFY_TIMEOUT_S`               | `300`                                                           | Timeout for one verify command.                                                             |
| `AISTACK_REVIEW_MODE`                    | `batch`                                                         | `batch` = one review call per run; `each` = one per task; `off` = no review.                |
| `AISTACK_WORK_TEMPLATE`                  | `task-template.hbs`                                             | Worker prompt template.                                                                     |
| `AISTACK_REVIEW_TEMPLATE`                | `review-template.hbs`                                           | Review prompt template.                                                                     |
| `AISTACK_DRIVER`                         | `ralph_driver.py`                                               | The run driver script.                                                                      |
| `AISTACK_BILLED_AGENTS`                  | `claude*` among the agents                                      | Comma list of agents whose calls are billed.                                                |
| `RALPH_TUI_BIN`                          | `~/.bun/bin/ralph-tui`                                          | The ralph-tui binary the driver runs.                                                       |
| `AISTACK_CLAUDE_MODEL`                   | `sonnet`                                                        | Model for the Claude Code wrappers.                                                         |
| `AISTACK_CLAUDE_EFFORT`                  | `medium`                                                        | Effort for the Claude Code wrappers.                                                        |
| `AISTACK_CLAUDE_BUDGET_PLAN`             | `1.5`                                                           | USD cap for the planning call.                                                              |
| `AISTACK_CLAUDE_BUDGET_REVIEW`           | `1.5`                                                           | USD cap for the review call.                                                                |
| `AISTACK_CLAUDE_BUDGET_WORK`             | `3`                                                             | USD cap for one work (fallback) call.                                                       |
| `AISTACK_ZEN_CATALOG`                    | _(unset)_                                                       | Test hook: a fixed models.dev catalog for `zen_models.py`.                                  |
| `AISTACK_ZEN_OFFERED`                    | _(unset)_                                                       | Test hook: a fixed list of offered Zen models.                                              |

Some names are set **by** the code/launcher rather than read from the user's environment: `AISTACK_WORKDIR`,
`AISTACK_PLAN_PROMPT`, `AISTACK_FETCH_PROMPT`, `AISTACK_REVIEWS_DIR`, `AISTACK_BRANCH`, `AISTACK_PR_TYPE`, `AISTACK_PR_TITLE`,
`AISTACK_PR_BODY`.

## Troubleshooting

- **`files_need_ranges`** — `ralph_plan` returned `ok=false`, `files_need_ranges` (a path → line count map),
  `billed_calls: 0`. Nothing was sent: some `files` entries were whole files longer than 120 lines (or a range
  covering nearly all of one). Call `ralph_plan` again at once with the same request and brief, giving each of those
  files as `path:START-END` (at most 200 lines per range; the same file may appear twice with different ranges),
  using the line numbers from `repo_read` / `repo_grep`. This refusal happens at most once per project.
- **`needs_more`** — `ralph_plan` returned `ok=false`, `needs_more: true`, `billed_calls: 1` and `questions`. Claude
  could not plan from what it got. The budget is fresh (research resets to 0); answer each question with the
  `repo_*` tools, then call `ralph_plan` once more with the same request, a brief that now includes the answers, and
  line ranges that show them. That second call is the last: Claude plans with what it gets.
- **`already_planned`** — `ralph_plan` returned `ok=true`, `already_planned: true`, the existing `plan_hash`, the
  `planned_request` it was for, and `billed_calls: 0`. A plan from an earlier session exists. If it is this work,
  call `ralph_validate_plan` and continue. Pass `replan=true` only when the user wants a new plan (billed).
- **Invalid plan** — `ralph_plan` returned `ok=false` with a `problems` list: the plan is saved but invalid. Fix each
  problem with `ralph_update_task`, then call `ralph_validate_plan`; do **not** call `ralph_plan` again (it is billed
  and the plan exists). `ralph_run` refuses to start while `validate` reports problems, if `plan_hash` does not match
  the current plan, if a run is already active, or if there is no recorded plan verdict and `skip_plan_review` was
  not passed.

## RFC process

Significant changes to aidev must be covered by an RFC before they land. `rfc_check.py` decides this:

```
python3 .config/aistack/rfc_check.py [--rfc-dir DIR] [--base REF] [--changed PATH ...]
```

- A **significant file** is a `.py` file directly in `.config/aistack/` (not in a subdirectory) or
  `planner-prompt.md`. Such a file must be listed in the `touches` frontmatter (the exact repo-relative path) of an
  RFC whose `status` is `approved` or `implemented`. Tests, docs and the `rfcs/` directory itself never gate
  anything.
- Without `--changed` the changed paths come from `git diff --name-only <base>...HEAD` (base defaults to `main`).
- Exit codes: `0` when every significant path is covered (`rfc_check: ok`), `1` when a significant path is not
  covered (one `RFC required: <path>` line plus a pointer to the template), `2` when an RFC is malformed (one
  `invalid RFC: <name>: <why>` line per bad RFC).

**When an RFC is required** (from `rfc-template.md`): changes to the research budget or the tools' file handling
limits (the 16-call cap, the file size and line-range rules); the `ralph_plan` / `ralph_run` flow; billed-call
patterns; tier assignment; verify/harness rules; and `planner-prompt.md` hard rules. An RFC is **not** required for
bug fixes, tests, docs, and wording-only prompt edits.

RFCs live in `.config/aistack/rfcs/NNNN-slug.md`, numbered in order and named with a short slug (for example
`0003-research-budget.md`); start from `../rfc-template.md` (`.config/aistack/rfc-template.md`). Statuses move
`draft -> review -> approved -> implemented`. Only `approved` or `implemented` satisfies `rfc_check.py`; a `draft` or
`review` RFC does not gate anything, and the status is moved in the frontmatter as the RFC progresses.
