# aistack-tuios: aidev on tuios

The daily terminal and AI stack, on tuios, with Claude Code as the backbone of aidev and the other models in panes it
talks to by tuios mail. The commands are in `.zsh_functions/tuios/`. `ai` and `ainfo` use no multiplexer and are
unchanged.

| Command                            | What it does                                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `dev`                              | reattach the daemon's sessions; with none, create nix-darwin, terraform-infrastructure and              |
|                                    | home-infrastructure where cloned. Layout: workspace 1 holds nvim, aidev's Claude, Lumo and              |
|                                    | the builders. Where `~/ai-info` exists it also ensures an `ai-info` session and a manage window         |
|                                    | (never twice).                                                                                          |
| `devim [name]`                     | that layout for the current directory, always a new session                                             |
|                                    | workspace 1 opens nvim and a `pick` pane (`aidev_pick.py`): choose Claude, 9B or gpt-oss-20b in advisor |
|                                    | mode while green check, yellow ? or red x show what is usable; a red x never blocks a choice            |
| `nxvim`, `psvim`, `hivim`, `itvim` | the session of one project, skipped where it is not cloned                                              |
| `hiwt <branch>`                    | a new home-infrastructure worktree and branch in `.worktrees/`, with a session of its own               |
| `peerdev <session>`                | a session on the peer Mac through tuios host link                                                       |
| `nxpeer`, `hipeer`                 | peerdev for nix-darwin and home-infrastructure sessions                                                 |
| `mmdev`, `himmdev`, `nxmmdev`      | old names, kept as aliases of `peerdev`, `hipeer`, `nxpeer`                                             |
| `aidev [task]`                     | Claude, Lumo and a builder, in the current tuios session (else session `<repo>`)                        |
| `aidev --resume`                   | reopen the Claude and Lumo panes of an unfinished run after a daemon restart, conversations included    |
| `aidev -p "<change>" [files]`      | one edit by a free builder, blocking; `AIDEV_TEST_CMD` must pass                                        |
| `aidev --handoff <dir>`            | a run for a plan another session wrote (`/aidev-handoff`); one JSON line, no attach                     |
| `aidev --rfc <name> [words]`       | a run whose Claude plans from an RFC in `~/.ai/rfcs`                                                    |
| `aidev --direct [words]`           | a free builder, interactive, in this terminal (gpa's fix windows use it)                                |
| `aidev_status`                     | the latest run's work dir, builder and tasks                                                            |
| `ai_tuios [-c] [message]`          | one Claude Code pane in session `<dir>` (`-c` continues the last one here)                              |

gpr points the current session's `nvim` and `zsh` windows at its new worktree. gpa's manual-fix choices open nvim
and aidev on a free workspace of the current session.

`gprr` (also a zsh function) is for a PR that is done: the on-device 9B rewrites the detailed task list in the PR body
as a short human-readable description (`pr-describe` does only that), the PR is marked ready for review, and
`gprr --monitor` watches it for failed checks and Qodo, Copilot and Akkido comments. In the plan pane `gprr` also
queues `/compact` first, then a follow-up prompt tells Claude to run `gprr --monitor`.

Review: `ctrl+t v` opens the tuios review view of the focused pane's changes, against the branch's upstream (a pushed
gpr branch shows only unpushed and uncommitted work). `c` notes a line, `C` a hunk, `S` sends the notes to the pane's
agent. `prdiff` prints the whole PR's diff against origin's default branch.

Keys (`.config/tuios/config.toml`): `ctrl+t` is tuios's prefix. `ctrl+1`..`9` switch workspaces,
`ctrl+shift+j`/`k` the next and previous session, `ctrl+shift+p` goes to an agent, session or pane,
`ctrl+shift+h` shows the sidebar. `ctrl+t i` opens the agents and the Inbox, `ctrl+t g` lazygit, `ctrl+t s` the
scratch terminal. `ctrl+t n`/`w`/`W` open a window, close it and close the session, `ctrl+t h`/`j`/`k`/`l` move
focus, `ctrl+t space` is the workspace prefix and `ctrl+t q` detaches, `ctrl+t ctrl+t` sends `ctrl+t` to the pane.
Without the prefix, `ctrl+tab`/`ctrl+shift+tab` cycle windows, `ctrl+shift+arrows` move focus and
`ctrl+shift+1`..`9` move the pane to a workspace. tuios is ctrl only: alt belongs to aerospace.

## Two Macs

The host entries `macmini` (MacMiniM1) and `macbookpro` (MacBookM2Pro) are in `.config/tuios/config.toml`. After a pull,
run `tuios config apply` once per machine, in a terminal outside tuios.

`dev` ensures the other Mac's nix-darwin and home-infrastructure sessions exist, but only when ssh answers within
3 seconds, and through `dev --detached` also its `ai-info` session and manage window. When it does not, `dev` prints
one line and carries on. `TUIOS_DEV_NO_PEER=1` turns the peer step off.

The sessions run on their own Mac. You only see and attach them from this one. The `*_ssh` commands (`mmdev_ssh`,
`himmdev_ssh`, `nxmmdev_ssh`) are the old ssh-window versions.

## aidev

Claude Code is the backbone: you talk to it, it reads the code, plans, sends tasks, checks them and reviews. Lumo does
web lookups for it, and a free model edits the code. Every dev session (`dev`, `devim`, `nxvim`, ...) starts one with
`AIDEV_TUIOS_SESSION=<session>`: Claude, Lumo and every builder open on workspace 1 beside nvim (`aidev -p` edits
included), so you can watch each agent and type into it. Started by hand inside another tuios session, Claude joins
the workspace of a window named `nvim`, else the lowest free one, and the rest share it. Outside tuios, or with
`AIDEV_TUIOS_OWN_SESSION=1`, they get session `<repo>` with the numbers below and a bare `zsh` window next to `nvim`. One run
per session; `finish` closes a piece of work, and the panes stay for the next. Plan and the billed builder start with
`--strict-mcp-config`, so they load only the tuios MCP; the global lumo, local-edit and oczen MCP servers stay for
gpr, gpa and other sessions. The plan pane also loads the Atlassian remote MCP (https://mcp.atlassian.com/v1/mcp,
OAuth once through `/mcp`) and the GitHub MCP (`@edjl/github-mcp`, through the logged-in `gh`) from `plan-mcp.json`.
`plan_mcp_guard.py`, a PreToolUse hook judged by ainfo's guard, allows their read tools and the Jira writes in
`JIRA_WRITES` (comment, transition, edit, create, link, worklog), and builder panes keep
the tuios MCP only.

| Workspace | Pane                  | Model                                                                                                               | Grants                           |
| --------- | --------------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------- |
| 1         | `plan`                | Claude Code, advisor off: plans, sends tasks, verifies, reviews                                                     | read, write, fan, files, respond |
| 1         | `nvim`                | your editor, with a bare `zsh` window next to it                                                                    | default                          |
| 1         | `research`            | pi on Lumo through lumo-tamer, no tools: web lookups                                                                | read                             |
| 1         | `build-local-tier-2`  | pi on the Qwen3-Coder-30B on the G14, large ctx                                                                     | read, write                      |
| 1         | `build-local-tier-1`  | pi on the Qwen3.5-9B on the G14 (Cait), 65536 ctx                                                                   | read, write                      |
| 1         | `build-local-tier-0`  | pi on the on-device gpt-oss-20b (MXFP4, reasoning effort low, ctx 32768); Claude opens it when the plan is approved | read, write                      |
| 1         | `build-free-tier-3`   | escalation: pi on a free Zen model                                                                                  | read, write                      |
| 1         | `build-billed-tier-4` | escalation: Claude Code (billed, asks you first)                                                                    | read, write                      |

The billed builder's settings use `acceptEdits`, allow the plan's verify commands by exact text and the read-only
commands, and deny git writes, `gh`, `rm -rf` and `sudo` (deny wins over allow). Edits to the plan directory and to the run's `state.json` and `events.jsonl` are denied too. Each run has its own plan directory and worktree record (`meta_path`) under `runs/<id>/`, so concurrent runs of one project never share a plan, worktree or PR; finish archives the plan to `runs/<id>/plan-done-<time>`.
Tasks added after the builder opened
still prompt.

The billed builder runs Bash in the Claude Code sandbox (`sandbox.enabled`, `autoAllowBashIfSandboxed`) inside `.worktrees`, with a read-only command allowlist and the plan's verify commands allowed. The free OpenCode builder gets the same allowlist as `permission.bash`, with `ask` for everything else and `deny` for git writes, `gh`, `rm -rf` and `sudo`. The local pi builder has no permission prompts and relies on the PATH git guard.
Sandbox check: from inside the sandbox, `nix --version` (2.32.4), `nix eval --expr 1` (1) and `python3.15 --version` (3.15.2) ran with no permission prompt and no sandbox denial; running `python3.15 .config/aistack-tuios/tests/test_builder_work_dir.py` directly as a script also ran without a prompt or denial, printed all PASS lines and exited 0.

1. You describe the work to Claude. It reads the code and asks Lumo (`ask-lumo`) for current docs, API changes and known
   bugs. Lumo is the first lumo-tamer that answers (this machine, MacMiniM1, then lumo.rollet.family); with none, there
   is no Lumo pane and Claude does the lookups itself.
2. Claude writes `plan/prd.json` and `plan/verify.json`, checks them with aistack's rules (`check-plan`) and shows you
   the tasks. It builds only when you say so.
3. Claude creates the gpr worktree and draft PR (`worktree`, main checkout only) and opens the builder (`builder`). For
   each task it writes a task file, mails it to the builder and types the prompt (`send-task`), waits for the builder's
   reply mail, then runs the task's verify commands itself, without a shell (`wait-task`). On a failure it sends the
   task again with a note; after two failures it asks you: retry, escalate or skip.
4. Claude reviews the whole diff and reports findings to you; fixes go back to the builder as tasks.
5. When the review is clean, Claude commits and pushes with `commit` (`gpa --auto`); gpa's findings go back to the
   builder as tasks.

After every Lumo answer and every builder result, Claude tells you what came back and asks before it goes on. While it
waits for you it runs `watch` in the background: new mail, or an exchange you have with Lumo in the research pane, wakes it,
and it reports that too. So you can correct Lumo or the builder in their panes and Claude picks it up.

After a daemon restart, `dev` (or any dev command for an existing session) runs `aidev_tuios.py restore <session>`: the
plan and research windows that came back holding a shell start again, conversations included.

How the panes talk:

- Claude and the builder use tuios mail. The builder holds read and write: it can mail Claude, but tuios lets a pane
  type only into panes that hold no grant it lacks, so it cannot type into Claude. Mail is marked as data, not
  instructions.
- Every `ask-lumo` question is wrapped with a forced-search preamble. A reply is accepted only with a
  `SEARCH-CONFIRMATION` line (searched=yes, the queries, at least one source link). Lumo is asked again twice if it
  is missing, then the reply is rejected (exit 4, REJECTED) and Claude must not use it. The confirmation is Lumo's own
  statement: lumo-tamer does not pass search calls through, so it cannot be checked. Each lumo-tamer needs
  `enableWebSearch: true` in its config.
- Claude types questions into the Lumo pane (`tuios ask-agent`) and reads the reply from Lumo's pi session file. Lumo
  holds read alone and has no tools: it cannot see the project, so Claude sends each question self-contained.
- Plan, tasks, check output and events are files under `~/.ai/aidev_tuios/<project>-<hash>/` (`plan/`, `runs/<id>/`).
  tuios keeps mail in memory only, so those files are the source of truth.
- Remaining permission prompts surface in `wait-task` and `watch`. Plan answers them with `approvals`, which uses
  `tuios respond`. aidev opens the plan pane with the respond grant, so the user saying yes in the conversation is the
  only gate. tuios still refuses an allow of a risky prompt (recursive delete, force push, pipe to a shell, a write
  outside the worktree): the user answers those in the Inbox (`ctrl+t i`). The shell grants in `.config/tuios/config.toml`
  include respond so the launcher can pass it on; only a plan pane opened from a pane without respond needs
  `tuios set-pane-grants -w plan --grants read,write,fan,files,respond` run outside any pane.
- A billed builder starts only after you say yes: in the plan pane's chat (the pane then runs `builder billed --approved`),
  else in the tuios Inbox (`ctrl+t i`), where the ask gives up after `AIDEV_BILLED_ASK_TIMEOUT_S` seconds (default 120).

Cost: Claude is interactive, so no per-call budget cap applies. `AIDEV_TUIOS_CLAUDE_MODEL` and
`AIDEV_TUIOS_CLAUDE_EFFORT` set its model and effort (default: `AISTACK_CLAUDE_MODEL` / `AISTACK_CLAUDE_EFFORT`, else
sonnet / medium). Lumo and the 30B are free; a free Zen model is used only when one fits the repo (a private repo needs
a zero-retention one).

Plan and billed panes start with `--setting-sources project,local`, so `~/.claude` settings, the user memory file,
skills and plugins are not loaded. `explore '<question>' [file[:START-END] ...]` has the on-device 9B read code (a free Zen model when
the 9B is down or the input is too big) and returns at most 1500 characters. `review-diff [paths]` has the 9B review the
diff file by file. Waiting is event-driven (`wait-task` and `watch` block on mail), so a wait costs no Claude tokens.
`finish` queues `/compact` when follow-ups remain (dirty tree, unverified task, non-empty `followups.txt` in the plan
dir) and `/clear` otherwise; `AIDEV_TUIOS_FINISH_RESET=off` turns that off.

### Escalation and Zen credits

Zen has no balance API, so `zen_models.py status` probes each candidate free model with one tiny `opencode run` (the
oczen MCP tool `zen_free_models` reports the same to any Claude session). Results are cached for ten minutes. The free
builder opens on the first available free model, and an exhausted or missing free tier is skipped by `builder free`,
`aidev -p` and `escalate`. `escalate` moves a task from tier-2 to tier-3 to tier-4 after `AIDEV_TUIOS_ESCALATE_AFTER`
failures at a tier (default 2), and from tier-0 or tier-3 straight to tier-4 when no free model is usable. Billed always asks in
the Inbox.

For public repos the free builder tries each OpenCode Go model first, then the same model on Zen (the Zen twin,
`opencode/<id>`), then the free Zen models. The Zen twin is paid and pay-per-token, so it spends Zen balance; it is tried
automatically only after the Go model reports a usage limit. Private repos are unchanged.

### Script forms

Agents reach them through
`~/.local/bin/aidev` (`../aistack/aidev-cli`), which allows only `-p` and `--handoff`.

- `aidev -p "<change>" [files]`: one edit in this directory. Inside tuios the on-device gpt-oss-20b opens in a pane on a free
  workspace (you can watch it and type into it), gets the change by mail and a typed prompt, and replies by mail to the
  caller's pane. The change counts only when the tree changed and `AIDEV_TEST_CMD` (a shell command) exits 0; otherwise
  a free Zen model tries once more, where one fits the repo. The pane closes afterwards, and the script prints each
  builder's reply and `git diff --stat`. Outside tuios the same builders run headless. Exit 0 means done.
  `AIDEV_TUIOS_EDIT_TIMEOUT_S` (540) caps each attempt.
  `--cwd DIR` / `--worktree DIR` edit the given work tree instead of the current directory. The builder pane is named
  `<run id>-tier-N`; its details are printed as one JSON line and written to `<run dir>/pane.json`. The guard (turns,
  loops, wall time, no progress, context overflow) runs while the pane works, with the same `AIDEV_GUARD_*` limits as
  `wait-task`, and escalates to the next tier. Tier-4 (billed) is used only with `--billed`. The last stdout line is a
  JSON result with `ok`, `tier`, `files`, `check_exit`, `run_dir`.
- `aidev --handoff <dir>`: checks `prd.json` and `verify.json` with aistack's rules (`problems` on failure), creates the
  gpr worktree and draft PR in a main checkout, and opens Claude and Lumo with Claude told to build the approved plan.
  It prints `started`, `run_id`, `session`, `work_dir`, `pr_url`.
- `aidev --rfc <name> [words]`: a normal run whose first prompt names the RFC file; Claude reads it and plans from it.
- `aidev --direct [words]`: pi on the on-device gpt-oss-20b in this terminal, else OpenCode on a free Zen model.
- A builder pane carries `AIDEV_TUIOS_BUILDER=1`, and `-p` and `--handoff` refuse to run there.

tuios agent features must be on: `[agents] enabled = true` in `../tuios/config.toml`. After a change to that file, run
`tuios config apply` from a terminal outside tuios (a pane cannot widen grants), or restart the daemon.

## Local planner

- aidev probes `claude` at start. If the probe fails, the plan pane runs `pi` on the local 9B model.
- `AIDEV_TUIOS_PLANNER=claude|local` forces the choice.
- The local planner cannot run `check-plan` or `send-task` until `ask-lumo` ran once or `ask-lumo --none-needed "<reason>"`
  was recorded. `AIDEV_TUIOS_PLANNER_GATE=off` disables the gate.
- `ask-lumo` saves confirmed replies as notes under the run's `research` directory and reuses them for the same
  question. `ask-lumo --fresh <question>` asks again.

## Files

- `aidev_tuios.py`: the launcher (`start`, `ai`, `status`) and Claude's helpers (`ask-lumo`, `check-plan`, `worktree`,
  `builder`, `send-task`, `wait-task`, `verify`, `finish`). It uses `validate`, `ensure_workdir` and the tamer list from
  `~/.config/aistack/aidev_lib.py`.
- `explore.py`: the `explore` helper; the 9B (else a free Zen model) reads code and answers in at most 1500 characters.
- `review_diff.py`: the `review-diff` helper; the 9B reviews the diff file by file.
- `plan_bash_guard.py`: PreToolUse hook for the plan pane; denies grep and find in Bash and points to rg and fd.
- `layer-claude.md`, `layer-lumo.md`, `layer-build.md`: each pane's system prompt.
- `tests/test_aidev_tuios.py`: `PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_aidev_tuios.py`.
- `tests/test_edit_guard.py`: `PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_edit_guard.py`.
- `tests/test_edit_manage.py`: `PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_edit_manage.py`.
- `../tuios/config.toml`: tuios config (agents on, herdr protocol emulation off, strict pane grants). The functions in
  `.zsh_functions/tuios/` set `XDG_CONFIG_HOME` so tuios reads it; check with `tuios config files`.
- Per-pane tuios hooks (Claude Code settings, the pi extension, the OpenCode plugin) are generated under
  `~/.ai/cache/aidev_tuios/` and passed per launch (`--settings`, `PI_CODING_AGENT_DIR`, `OPENCODE_CONFIG_DIR`). The
  stowed `~/.claude`, `~/.pi` and `~/.config/opencode` are never changed.

Settings for scripts and tests: `AIDEV_TUIOS_HOME` (state dir), `AIDEV_TUIOS_LUMO=off` (no Lumo pane),
`AIDEV_TUIOS_NO_ATTACH=1` (print the session, do not attach), `AIDEV_TUIOS_WORKTREE_MODE=none`,
`AIDEV_TUIOS_REPO_PRIVATE=yes|no`, `AIDEV_TUIOS_REPLY_ECHO_MAX` (default 300, characters of the builder reply
wait-task echoes), and `AIDEV_TUIOS_FAKE_HUMAN=<file>`. The
last one is for tests only: tuios lets only an attached client answer an Inbox question, so the helpers read their
answers from lines in that file.

#### Remote builder

The local builder uses a remote OpenAI-compatible llama-server (the G14, behind the llm-gateway) instead of the
on-device 30B. It is on by default at `https://llm.rollet.family/v1`, so no env setup is needed. The key is fetched
at runtime from Doppler (`LLM_PUBLIC_API_KEY` in `FullHavocJosh/root_hetzner-cluster`), like the public Lumo
endpoint. These settings override the defaults:

- `AIDEV_REMOTE_BUILDER=off`: disables the defaults and uses no remote tier.
- `AIDEV_REMOTE_BUILDER_URL`: the OpenAI base, for example `http://HOST:8082/v1`. An explicit value always wins over
  the default URL. AIDEV_REMOTE_BUILDER_URL is an explicit opt-in for build-local-tier-0 only; the gateway default no longer
  applies to local.
- `AIDEV_REMOTE_BUILDER_KEY`: the key itself, instead of the Doppler lookup.
- `AIDEV_REMOTE_BUILDER_KEY_FILE`: the path to a file that holds the key. Set the path, never the key itself.
- `AIDEV_REMOTE_BUILDER_MODEL`: the model name to request (default `qwen3-coder-30b`).

Before each local-builder start, aidev sends a 4 s probe, `GET /models`, to the remote. If the remote is
unreachable, aidev prints one stderr line and falls through to the on-device gpt-oss-20b, then to Zen. If it is healthy, the
local `edit.lock` and the idle unload are skipped, because the remote does not use the local GPU. If the remote dies
during a job, aidev kills pi, prints a partial-edit warning and exits 3 (escalate), so check the work dir before you
retry. The gateway returns 503 when the G14 is off, which counts as offline. The endpoint is deliberately not
monitored or alerted on: only aidev tracks online or offline, through the probe and the 5 s mid-job monitor (3
failures stop pi). aidev never logs the URL or the key.

When a builder pane repeats 'successfully completed task T<n>' (two or more times in its last 80 scrollback
lines), or says it in mail to the plan pane, `wait-task` and `watch` interrupt it (Escape, then ctrl+c if
needed) and reset it with its reset command (`/new` for tiers 0 to 3, `/clear` for tier-4) without closing
the window, and print `builder X looped on completion; reset`. A reply already mailed on the task thread
stays the normal result and verify still runs. Set `AIDEV_TUIOS_LOOP_STOP=off` to disable it.

#### Builder tiers

aidev has five builder tiers, from a registry in `aidev_tiers.py`:

| Id     | Pane                  | Host                  | Ctx (tokens)  | Endpoint                          |
| ------ | --------------------- | --------------------- | ------------- | --------------------------------- |
| tier-0 | `build-local-tier-0`  | on-device gpt-oss-20b | 32768         | none (local model file)           |
| tier-1 | `build-local-tier-1`  | G14 9B (Cait)         | 65536         | `https://llm.rollet.family/t1/v1` |
| tier-2 | `build-local-tier-2`  | G14, large ctx        | 65536         | `https://llm.rollet.family/v1`    |
| tier-3 | `build-free-tier-3`   | free Zen model        | model-defined | Zen                               |
| tier-4 | `build-billed-tier-4` | Claude Code, billed   | model-defined | Anthropic                         |

Task size limits scale with the target tier's context window. The tiers config file is `~/.config/aidev/tiers`
followed by the extension `.json`, or the path in `AIDEV_TIERS_FILE`. It overrides keys per tier: `ctx`, `enabled`,
`url`, `alias` (the model name to request) and `min_ram_gb`.

Selection: aidev routes a task to tier-1 or tier-2 by size and availability (a small task goes to tier-1 when it is
enabled and online, otherwise tier-2). Tier-0 is used only when both G14 tiers are offline. After that comes tier-3,
then tier-4. If a task fits no tier-2 ctx while tier-2 is online, aidev reports that the task must be split.

Tier-1 is the Qwen3.5-9B: it scored 4 of 9 coding cases in the bench, so it suits small, well-specified tasks.

Old names stay as aliases: semi-local is tier-2, local is tier-0, free is tier-3 and billed is tier-4 (the old
`build-semi-local`, `build-local`, `build-free` and `build-billed` pane names map the same way).

`aidev tiers [--json]` prints each tier with its ctx and online state, as text or JSON.

#### Tier-2 (G14) settings

The tier-2 builder (pane `build-local-tier-2`) is pi pointed at the Qwen3-Coder-30B llama.cpp server on the G14.
aidev tries it first, falls back to the on-device `build-local-tier-0` when the G14 is offline, then to the free and
billed chain. Selecting `build-local-tier-0` explicitly is unchanged. These settings override the defaults:

- `AIDEV_SEMI_LOCAL=off`: disables the tier-2 builder.
- `AIDEV_SEMI_LOCAL_URL`: the OpenAI base (default `https://llm.rollet.family/v1`).
- `AIDEV_SEMI_LOCAL_KEY_FILE`: the path to the key file (no default). pi reads it at runtime and aidev never prints it.
- `AIDEV_SEMI_LOCAL_MODEL`: the model name to request.
- `AIDEV_SEMI_LOCAL_TIMEOUT_S`: the availability probe timeout in seconds (default 4).

The G14 counts as available when an authenticated GET of /models returns 200 and lists the model. It is offline when it is off or a game runs. Then aidev falls back to `build-local-tier-0`.

The order is tier-2, tier-0, tier-3, tier-4; tier-0 runs the on-device gpt-oss-20b (MXFP4, reasoning effort low, ctx 32768) and needs the model file and 24 GB RAM; tier-3 needs a Zen API key; each skipped tier prints a reason.
