# aistack-test: the tuios test stack

A second copy of the terminal and AI stack, on tuios instead of herdr, with Claude Code as the backbone of aidev and the
other models in panes it talks to by tuios mail. RFC: `~/.ai/rfcs/2026-10-25-aidev-tuios-test.md`. Nothing here replaces
`dev`, `devim`, `aidev` or `ai`; those stay on herdr and are unchanged.

| Command                  | What it does                                                                                          |
| ------------------------ | ----------------------------------------------------------------------------------------------------- |
| `dev_test`               | one tuios session per repo under `~` (`dev_test-<repo>`): workspace 1 nvim and tuicr, workspace 2 zsh |
| `devim_test [name]`      | that layout for the current directory, always a new session                                           |
| `nxvim_test`             | the nix-darwin session only                                                                           |
| `aidev_test [task]`      | Claude, Lumo and a builder, in the current tuios session (else session `aidev_test-<repo>`)           |
| `aidev_test --resume`    | reopen the Claude and Lumo panes of an unfinished run after a daemon restart, conversations included  |
| `aidev_test_status`      | the latest run's work dir, builder and tasks                                                          |
| `ai_test [-c] [message]` | one Claude Code pane in session `ai_test-<dir>` (`-c` continues the last one here)                    |

Run them from a plain Ghostty window, not inside herdr. Keys: `ctrl+b` is tuios's prefix. `ctrl+b 1`..`9` switch
workspaces, `ctrl+b s` sessions, `ctrl+b i` the agents and the Inbox, `ctrl+b d` detach. tuios's `opt+` keys never
arrive, because aerospace owns alt.

## aidev_test

Claude Code is the backbone: you talk to it, it reads the code, plans, sends tasks, checks them and reviews. Lumo does
web lookups for it, and a free model edits the code. Started inside tuios, the panes open in the session you are in, on
its lowest free workspaces (three are needed). Outside tuios, or with `AIDEV_TEST_OWN_SESSION=1`, they get session
`aidev_test-<repo>` with the workspace numbers below and a dev workspace. One run per session.

| Workspace | Pane                               | Model                                                                 | Grants                  |
| --------- | ---------------------------------- | --------------------------------------------------------------------- | ----------------------- |
| 1         | `claude`                           | Claude Code, advisor off: plans, sends tasks, verifies, reviews       | read, write, fan, files |
| 2         | `lumo`                             | pi on Lumo through lumo-tamer, no tools: web lookups                  | read                    |
| 3         | `build`                            | pi on the on-device 30B; Claude opens it when the plan is approved    | read, write             |
| 3         | `build-pickle`, `build-claude`     | escalation: a free Zen model, or Claude Code (billed, asks you first) | read, write             |
| 4         | `dev-nvim`, `dev-tuicr`, `dev-zsh` | your editor and diff, only in a session of its own                    | default                 |

1. You describe the work to Claude. It reads the code and asks Lumo (`ask-lumo`) for current docs, API changes and known
   bugs. Lumo is the first lumo-tamer that answers (this machine, MacMiniM1, then lumo.rollet.family); with none, there
   is no Lumo pane and Claude does the lookups itself.
2. Claude writes `plan/prd.json` and `plan/verify.json`, checks them with the real stack's rules (`check-plan`) and
   shows you the tasks. It builds only when you say so.
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
- Plan, tasks, check output and events are files under `~/.ai/aidev_test/<project>-<hash>/` (`plan/`, `runs/<id>/`).
  tuios keeps mail in memory only, so those files are the source of truth.
- A billed builder starts only after you say yes in the tuios Inbox (`ctrl+b i`).

Cost: Claude is interactive, so no per-call budget cap applies. `AIDEV_TEST_CLAUDE_MODEL` and `AIDEV_TEST_CLAUDE_EFFORT`
set its model and effort (default: `AISTACK_CLAUDE_MODEL` / `AISTACK_CLAUDE_EFFORT`, else sonnet / medium). Lumo and the
30B are free; a free Zen model is used only when one fits the repo (a private repo needs a zero-retention one).

tuios agent features must be on: `[agents] enabled = true` in `../tuios/config.toml`. After a change to that file, run
`tuios config apply` from a terminal outside tuios (a pane cannot widen grants), or restart the daemon.

## Files

- `aidev_test.py`: the launcher (`start`, `ai`, `status`) and Claude's helpers (`ask-lumo`, `check-plan`, `worktree`,
  `builder`, `send-task`, `wait-task`, `verify`, `finish`). It uses `validate`, `ensure_workdir` and the tamer list from
  `~/.config/aistack/ralph_mcp.py`, unchanged.
- `layer-claude.md`, `layer-lumo.md`, `layer-build.md`: each pane's system prompt.
- `tests/test_aidev_test.py`: `PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-test/tests/test_aidev_test.py`.
- `../tuios/config.toml`: tuios config (agents on, herdr variables off, strict pane grants). The `_test` functions set
  `XDG_CONFIG_HOME` so tuios reads it; check with `tuios config files`.
- Per-pane tuios hooks (Claude Code settings, the pi extension, the OpenCode plugin) are generated under
  `~/.ai/cache/aidev_test/` and passed per launch (`--settings`, `PI_CODING_AGENT_DIR`, `OPENCODE_CONFIG_DIR`). The
  stowed `~/.claude`, `~/.pi` and `~/.config/opencode` are never changed.

Settings for scripts and tests: `AIDEV_TEST_HOME` (state dir), `AIDEV_TEST_LUMO=off` (no Lumo pane),
`AIDEV_TEST_NO_ATTACH=1` (print the session, do not attach), `AIDEV_TEST_ALLOW_NESTED=1` (allow a start from inside
herdr), `AIDEV_TEST_WORKTREE_MODE=none`, `AIDEV_TEST_REPO_PRIVATE=yes|no`, and `AIDEV_TEST_FAKE_HUMAN=<file>`. The last
one is for tests only: tuios lets only an attached client answer an Inbox question, so the helpers read their answers
from lines in that file.

## Undo

Remove the `.zshrc_functions_test` line in `.zshrc`, then delete `.zshrc_functions_test`, `.config/aistack-test/`,
`.config/tuios/` and `tuios` in `packages-tui.nix`. Then run `tuios kill-server` and
`rm -rf ~/.ai/aidev_test ~/.ai/cache/aidev_test`.
