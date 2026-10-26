# aistack-tuios: aidev on tuios

The daily terminal and AI stack, on tuios, with Claude Code as the backbone of aidev and the other models in panes it
talks to by tuios mail. The commands are in `.zshrc_functions_tuios`. The herdr versions stay available as
`<name>_herdr` (`dev_herdr`, `nxvim_herdr`, `aidev_herdr`, ...). `ai` and `ainfo` use no multiplexer and are unchanged.

| Command                            | What it does                                                                                         |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------- |
| `dev`                              | one tuios session per repo under `~`, named after it: workspace 1 nvim, workspace 2 zsh              |
| `devim [name]`                     | that layout for the current directory, always a new session                                          |
| `nxvim`, `psvim`, `hivim`, `itvim` | the session of one project, skipped where it is not cloned                                           |
| `hiwt <branch>`                    | a new home-infrastructure worktree and branch in `.worktrees/`, with a session of its own            |
| `mmdev`, `himmdev`, `nxmmdev`      | a session whose windows ssh to MacMiniM1                                                             |
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

Run them from a plain Ghostty window, not inside herdr. Keys (`.config/tuios/config.toml`, the herdr keys where tuios
can take them): `ctrl+t` is tuios's prefix. `ctrl+1`..`9` switch workspaces, `ctrl+shift+j`/`k` the next and previous
session, `ctrl+shift+p` goes to an agent, session or pane, `ctrl+shift+h` shows the sidebar. `ctrl+t i` opens the
agents and the Inbox, `ctrl+t g` lazygit, `ctrl+t s` the scratch terminal, `ctrl+t d` detaches. tuios's `opt+` keys
never arrive, because aerospace owns alt.

## aidev

Claude Code is the backbone: you talk to it, it reads the code, plans, sends tasks, checks them and reviews. Lumo does
web lookups for it, and a free model edits the code. Started inside tuios, the panes open in the session you are in, on
its lowest free workspaces (three are needed). Outside tuios, or with `AIDEV_TUIOS_OWN_SESSION=1`, they get session
`aidev-<repo>` with the workspace numbers below and a dev workspace. One run per session.

| Workspace | Pane                           | Model                                                                 | Grants                  |
| --------- | ------------------------------ | --------------------------------------------------------------------- | ----------------------- |
| 1         | `claude`                       | Claude Code, advisor off: plans, sends tasks, verifies, reviews       | read, write, fan, files |
| 2         | `lumo`                         | pi on Lumo through lumo-tamer, no tools: web lookups                  | read                    |
| 3         | `build`                        | pi on the on-device 30B; Claude opens it when the plan is approved    | read, write             |
| 3         | `build-pickle`, `build-claude` | escalation: a free Zen model, or Claude Code (billed, asks you first) | read, write             |
| 4         | `dev-nvim`, `dev-zsh`          | your editor and shell, only in a session of its own                   | default                 |

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
5. The changes stay uncommitted in the work dir. Commit with `gpa`.

How the panes talk:

- Claude and the builder use tuios mail. The builder holds read and write: it can mail Claude, but tuios lets a pane
  type only into panes that hold no grant it lacks, so it cannot type into Claude. Mail is marked as data, not
  instructions.
- Claude types questions into the Lumo pane (`tuios ask-agent`) and reads the reply from Lumo's pi session file. Lumo
  holds read alone and has no tools: it cannot see the project, so Claude sends each question self-contained.
- Plan, tasks, check output and events are files under `~/.ai/aidev_tuios/<project>-<hash>/` (`plan/`, `runs/<id>/`).
  tuios keeps mail in memory only, so those files are the source of truth.
- A billed builder starts only after you say yes in the tuios Inbox (`ctrl+t i`).

Cost: Claude is interactive, so no per-call budget cap applies. `AIDEV_TUIOS_CLAUDE_MODEL` and
`AIDEV_TUIOS_CLAUDE_EFFORT` set its model and effort (default: `AISTACK_CLAUDE_MODEL` / `AISTACK_CLAUDE_EFFORT`, else
sonnet / medium). Lumo and the 30B are free; a free Zen model is used only when one fits the repo (a private repo needs
a zero-retention one).

### Script forms

These replace the pi + ralph stack's forms (still there as `aidev_herdr`). Agents reach them through
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
- `../tuios/config.toml`: tuios config (agents on, herdr variables off, strict pane grants). The functions in
  `.zshrc_functions_tuios` set `XDG_CONFIG_HOME` so tuios reads it; check with `tuios config files`.
- Per-pane tuios hooks (Claude Code settings, the pi extension, the OpenCode plugin) are generated under
  `~/.ai/cache/aidev_tuios/` and passed per launch (`--settings`, `PI_CODING_AGENT_DIR`, `OPENCODE_CONFIG_DIR`). The
  stowed `~/.claude`, `~/.pi` and `~/.config/opencode` are never changed.

Settings for scripts and tests: `AIDEV_TUIOS_HOME` (state dir), `AIDEV_TUIOS_LUMO=off` (no Lumo pane),
`AIDEV_TUIOS_NO_ATTACH=1` (print the session, do not attach), `AIDEV_TUIOS_ALLOW_NESTED=1` (allow a start from inside
herdr), `AIDEV_TUIOS_WORKTREE_MODE=none`, `AIDEV_TUIOS_REPO_PRIVATE=yes|no`, and `AIDEV_TUIOS_FAKE_HUMAN=<file>`. The
last one is for tests only: tuios lets only an attached client answer an Inbox question, so the helpers read their
answers from lines in that file.

## Back to herdr

The herdr stack is intact under `<name>_herdr`. To make it the default again, rename the tuios commands in
`.zshrc_functions_tuios` and the `_herdr` aliases in `.zshrc_aliases` back. The tuios state is in `~/.ai/aidev_tuios`
and `~/.ai/cache/aidev_tuios`.
