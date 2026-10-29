# aistack-tuios: aidev on tuios

The daily terminal and AI stack, on tuios, with Claude Code as the backbone of aidev and the other models in panes it
talks to by tuios mail. The commands are in `.zshrc_functions_tuios`. `ai` and `ainfo` use no multiplexer and are
unchanged.

| Command                            | What it does                                                                                         |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `dev`                              | reattach the daemon's sessions; with none, create nix-darwin, terraform-infrastructure and           |
|                                    | home-infrastructure where cloned. Layout: workspace 1 holds nvim, aidev's Claude, Lumo and           |
|                                    | the builders.                                                                                        |
| `devim [name]`                     | that layout for the current directory, always a new session                                          |
| `nxvim`, `psvim`, `hivim`, `itvim` | the session of one project, skipped where it is not cloned                                           |
| `hiwt <branch>`                    | a new home-infrastructure worktree and branch in `.worktrees/`, with a session of its own            |
| `peerdev <session>`                | a session on the peer Mac through tuios host link                                                    |
| `nxpeer`, `hipeer`                 | peerdev for nix-darwin and home-infrastructure sessions                                              |
| `mmdev`, `himmdev`, `nxmmdev`      | old names, kept as aliases of `peerdev`, `hipeer`, `nxpeer`                                          |
| `aidev [task]`                     | Claude, Lumo and a builder, in the current tuios session (else session `aidev-<repo>`)               |
| `aidev --resume`                   | reopen the Claude and Lumo panes of an unfinished run after a daemon restart, conversations included |
| `aidev -p "<change>" [files]`      | one edit by a free builder, blocking; `AIDEV_TEST_CMD` must pass                                     |
| `aidev --handoff <dir>`            | a run for a plan another session wrote (`/aidev-handoff`); one JSON line, no attach                  |
| `aidev --rfc <name> [words]`       | a run whose Claude plans from an RFC in `~/.ai/rfcs`                                                 |
| `aidev --direct [words]`           | a free builder, interactive, in this terminal (gpa's fix windows use it)                             |
| `aidev_status`                     | the latest run's work dir, builder and tasks                                                         |
| `ai_tuios [-c] [message]`          | one Claude Code pane in session `ai_tuios-<dir>` (`-c` continues the last one here)                  |

gpr points the current session's `nvim` and `zsh` windows at its new worktree. gpa's manual-fix choices open nvim
and aidev on a free workspace of the current session.

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

The host entries `mini` (MacMiniM1) and `macbook` (MacBookM2Pro) are in `.config/tuios/config.toml`. After a pull,
run `tuios config apply` once per machine, in a terminal outside tuios.

`dev` ensures the other Mac's nix-darwin and home-infrastructure sessions exist, but only when ssh answers within
3 seconds. When it does not, `dev` prints one line and carries on. `TUIOS_DEV_NO_PEER=1` turns the peer step off.

The sessions run on their own Mac. You only see and attach them from this one. The `*_ssh` commands (`mmdev_ssh`,
`himmdev_ssh`, `nxmmdev_ssh`) are the old ssh-window versions.

## aidev

Claude Code is the backbone: you talk to it, it reads the code, plans, sends tasks, checks them and reviews. Lumo does
web lookups for it, and a free model edits the code. Every dev session (`dev`, `devim`, `nxvim`, ...) starts one with
`AIDEV_TUIOS_SESSION=<session>`: Claude, Lumo and every builder open on workspace 1 beside nvim (`aidev -p` edits
included), so you can watch each agent and type into it. Started by hand inside another tuios session, Claude joins
the workspace of a window named `nvim`, else the lowest free one, and the rest share it. Outside tuios, or with
`AIDEV_TUIOS_OWN_SESSION=1`, they get session `aidev-<repo>` with the numbers below and a `dev-nvim` window. One run
per session; `finish` closes a piece of work, and the panes stay for the next. Plan and the billed builder start with
`--strict-mcp-config`, so they load only the tuios MCP; the global lumo, local-edit and oczen MCP servers stay for
gpr, gpa and other sessions. The plan pane also loads the Atlassian remote MCP (https://mcp.atlassian.com/v1/mcp,
OAuth once through `/mcp`) and the GitHub MCP (`@edjl/github-mcp`, through the logged-in `gh`) from `plan-mcp.json`.
`plan_mcp_guard.py`, a PreToolUse hook judged by ainfo's guard, allows only their read tools, and builder panes keep
the tuios MCP only.

| Workspace | Pane                | Model                                                              | Grants                           |
| --------- | ------------------- | ------------------------------------------------------------------ | -------------------------------- |
| 1         | `plan`              | Claude Code, advisor off: plans, sends tasks, verifies, reviews    | read, write, fan, files, respond |
| 1         | `nvim` (`dev-nvim`) | your editor (`dev-nvim` only in a session of its own)              | default                          |
| 1         | `research`          | pi on Lumo through lumo-tamer, no tools: web lookups               | read                             |
| 1         | `build-local`       | pi on the on-device 30B; Claude opens it when the plan is approved | read, write                      |
| 1         | `build-free`        | escalation: pi on a free Zen model                                 | read, write                      |
| 1         | `build-billed`      | escalation: Claude Code (billed, asks you first)                   | read, write                      |

The billed builder's settings use `acceptEdits`, allow the plan's verify commands by exact text and the read-only
commands, and deny git writes, `gh`, `rm -rf` and `sudo` (deny wins over allow). Edits to the plan directory and to the run's `state.json` and `events.jsonl` are denied too. Each run has its own plan directory and worktree record (`meta_path`) under `runs/<id>/`, so concurrent runs of one project never share a plan, worktree or PR; finish archives the plan to `runs/<id>/plan-done-<time>`.
Tasks added after the builder opened
still prompt.

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
- A billed builder starts only after you say yes in the tuios Inbox (`ctrl+t i`).

Cost: Claude is interactive, so no per-call budget cap applies. `AIDEV_TUIOS_CLAUDE_MODEL` and
`AIDEV_TUIOS_CLAUDE_EFFORT` set its model and effort (default: `AISTACK_CLAUDE_MODEL` / `AISTACK_CLAUDE_EFFORT`, else
sonnet / medium). Lumo and the 30B are free; a free Zen model is used only when one fits the repo (a private repo needs
a zero-retention one).

### Escalation and Zen credits

Zen has no balance API, so `zen_models.py status` probes each candidate free model with one tiny `opencode run` (the
oczen MCP tool `zen_free_models` reports the same to any Claude session). Results are cached for ten minutes. The free
builder opens on the first available free model, and an exhausted or missing free tier is skipped by `builder free`,
`aidev -p` and `escalate`. `escalate` moves a task from local to free to billed after `AIDEV_TUIOS_ESCALATE_AFTER`
failures at a tier (default 2), and from local straight to billed when no free model is usable. Billed always asks in
the Inbox.

### Script forms

These replace the pi + ralph stack's forms. Agents reach them through
`~/.local/bin/aidev` (`../aistack/aidev-cli`), which allows only `-p` and `--handoff`.

- `aidev -p "<change>" [files]`: one edit in this directory. Inside tuios the on-device 30B opens in a pane on a free
  workspace (you can watch it and type into it), gets the change by mail and a typed prompt, and replies by mail to the
  caller's pane. The change counts only when the tree changed and `AIDEV_TEST_CMD` (a shell command) exits 0; otherwise
  a free Zen model tries once more, where one fits the repo. The pane closes afterwards, and the script prints each
  builder's reply and `git diff --stat`. Outside tuios the same builders run headless. Exit 0 means done.
  `AIDEV_TUIOS_EDIT_TIMEOUT_S` (540) caps each attempt.
- `aidev --handoff <dir>`: checks `prd.json` and `verify.json` with aistack's rules (`problems` on failure), creates the
  gpr worktree and draft PR in a main checkout, and opens Claude and Lumo with Claude told to build the approved plan.
  It prints `started`, `run_id`, `session`, `work_dir`, `pr_url`.
- `aidev --rfc <name> [words]`: a normal run whose first prompt names the RFC file; Claude reads it and plans from it.
- `aidev --direct [words]`: pi on the on-device 30B in this terminal, else OpenCode on a free Zen model.
- A builder pane carries `AIDEV_TUIOS_BUILDER=1`, and `-p` and `--handoff` refuse to run there.

tuios agent features must be on: `[agents] enabled = true` in `../tuios/config.toml`. After a change to that file, run
`tuios config apply` from a terminal outside tuios (a pane cannot widen grants), or restart the daemon.

## Files

- `aidev_tuios.py`: the launcher (`start`, `ai`, `status`) and Claude's helpers (`ask-lumo`, `check-plan`, `worktree`,
  `builder`, `send-task`, `wait-task`, `verify`, `finish`). It uses `validate`, `ensure_workdir` and the tamer list from
  `~/.config/aistack/ralph_mcp.py`, unchanged.
- `layer-claude.md`, `layer-lumo.md`, `layer-build.md`: each pane's system prompt.
- `tests/test_aidev_tuios.py`: `PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-tuios/tests/test_aidev_tuios.py`.
- `../tuios/config.toml`: tuios config (agents on, herdr protocol emulation off, strict pane grants). The functions in
  `.zshrc_functions_tuios` set `XDG_CONFIG_HOME` so tuios reads it; check with `tuios config files`.
- Per-pane tuios hooks (Claude Code settings, the pi extension, the OpenCode plugin) are generated under
  `~/.ai/cache/aidev_tuios/` and passed per launch (`--settings`, `PI_CODING_AGENT_DIR`, `OPENCODE_CONFIG_DIR`). The
  stowed `~/.claude`, `~/.pi` and `~/.config/opencode` are never changed.

Settings for scripts and tests: `AIDEV_TUIOS_HOME` (state dir), `AIDEV_TUIOS_LUMO=off` (no Lumo pane),
`AIDEV_TUIOS_NO_ATTACH=1` (print the session, do not attach), `AIDEV_TUIOS_WORKTREE_MODE=none`,
`AIDEV_TUIOS_REPO_PRIVATE=yes|no`, and `AIDEV_TUIOS_FAKE_HUMAN=<file>`. The
last one is for tests only: tuios lets only an attached client answer an Inbox question, so the helpers read their
answers from lines in that file.
