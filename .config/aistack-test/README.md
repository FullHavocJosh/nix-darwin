# aistack-test: the tuios test stack

A second copy of the terminal and AI stack, on tuios instead of herdr, with every aidev layer a live, interactive
model pane. RFC: `~/.ai/rfcs/2026-10-25-aidev-tuios-test.md`. Nothing here replaces `dev`, `devim`, `aidev` or `ai`;
those stay on herdr and are unchanged.

| Command                           | What it does                                                                                          |
| --------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `dev_test`                        | one tuios session per repo under `~` (`dev_test-<repo>`): workspace 1 nvim and tuicr, workspace 2 zsh |
| `devim_test [name]`               | that layout for the current directory, always a new session                                           |
| `nxvim_test`                      | the nix-darwin session only                                                                           |
| `aidev_test [task]`               | aidev with interactive layers, session `aidev_test-<repo>`                                            |
| `aidev_test --no-research [task]` | skip the local research layer and brief Claude in the plan pane yourself                              |
| `aidev_test --resume`             | rebuild the panes of an unfinished run after a daemon restart, conversations included                 |
| `aidev_test_status`               | the latest run's phase and tasks                                                                      |
| `ai_test [-c] [message]`          | one Claude Code pane in session `ai_test-<dir>` (`-c` continues the last one here)                    |

Run them from a plain Ghostty window, not inside herdr. Keys: `ctrl+b` is tuios's prefix. `ctrl+b 1`..`9` switch
workspaces, `ctrl+b s` sessions, `ctrl+b i` the agents and the Inbox, `ctrl+b d` detach. tuios's `opt+` keys never
arrive, because aerospace owns alt.

## aidev_test

One tuios session per project, one workspace per layer. Type into any pane at any time.

| Workspace  | Pane                               | Model                                                                 | Grants             |
| ---------- | ---------------------------------- | --------------------------------------------------------------------- | ------------------ |
| 1 research | `research`                         | pi on the local 9B: `repo_*` research (budgeted), then `handoff`      | read               |
| 2 plan     | `plan`                             | Claude Code, advisor mode: writes `plan/prd.json`, `plan/verify.json` | read               |
| 3 build    | `build`                            | pi on the on-device 30B, else OpenCode on a free Zen model            | read               |
| 3 build    | `build-pickle`, `build-claude`     | only when you pick escalation (Claude is billed, advisor off)         | read               |
| 4 review   | `review`                           | Claude Code, advisor mode: writes `reviews/<run>.md`                  | read               |
| 5 dev      | `dev-nvim`, `dev-tuicr`, `dev-zsh` | your editor and diff in the work dir                                  | default            |
| 9 driver   | `driver`                           | `aidev_test.py driver`, no model                                      | read, write, admin |

1. The research pane looks at the code and calls `handoff`, which writes `plan/brief.md`.
2. The driver sees the brief and opens the plan pane on it. You plan with Claude there. Claude writes the plan files,
   the driver checks them (the real stack's `validate`) and types any problems back into the plan pane.
3. A valid plan becomes a question in the Inbox: start the build, or keep planning.
4. On start, the driver creates the gpr worktree and draft PR (main checkout only) and opens the builder. It then
   types one task at a time (`tuios queue`), waits for the builder to come to rest, and runs the task's verify
   commands itself, without a shell. A failed check goes back to the builder once. After that, the Inbox asks you:
   retry (type guidance into the builder first), escalate, skip or abort.
5. The review pane reviews the whole change against the plan and the driver's check output. On `Verdict: FAIL` the
   Inbox asks: rework (the builder fixes the findings, the driver checks every task again), accept, or abort.
6. The changes stay uncommitted in the work dir. Commit with `gpa`.

How the layers talk:

- Only files carry content: everything is under `~/.ai/aidev_test/<project>-<hash>/` (`plan/`, `runs/<id>/`,
  `reviews/`).
- Only the driver types into panes. Every model pane holds the `read` grant alone, so no model can type into, mail or
  start another pane, and none holds `fan` (tuios's merge and push path, outside gpr/gpa).
- tuios mail goes only to you: notices, and the details behind each Inbox question. tuios keeps mail in memory only,
  so the run state on disk stays the source of truth.

Cost: the Claude panes are interactive, so no per-call budget cap applies. A plan or review costs what the
conversation costs. `AIDEV_TEST_CLAUDE_MODEL` and `AIDEV_TEST_CLAUDE_EFFORT` set the model and effort (default:
`AISTACK_CLAUDE_MODEL` / `AISTACK_CLAUDE_EFFORT`, else sonnet / medium). A billed builder starts only when you pick
it.

## Files

- `aidev_test.py`: the launcher (`start`, `ai`, `status`) and the driver (`driver`).
- `aidev_test_mcp.py`: the research pane's MCP server. It reuses `repo_tree`, `repo_read`, `repo_grep` and
  `ralph_save_rfc` from `~/.config/aistack/ralph_mcp.py` unchanged, and adds `handoff`.
- `layer-*.md`: each layer's system prompt.
- `tests/test_aidev_test.py`: `PYTHONDONTWRITEBYTECODE=1 python3 .config/aistack-test/tests/test_aidev_test.py`.
- `../tuios/config.toml`: tuios config (herdr variables off, strict pane grants). The `_test` functions set
  `XDG_CONFIG_HOME` so tuios reads it; check with `tuios config files`.
- Per-pane tuios hooks (Claude Code settings, the pi extension, the OpenCode plugin) are generated under
  `~/.ai/cache/aidev_test/` and passed per launch (`--settings`, `PI_CODING_AGENT_DIR`, `OPENCODE_CONFIG_DIR`). The
  stowed `~/.claude`, `~/.pi` and `~/.config/opencode` are never changed.

Settings for scripts and tests: `AIDEV_TEST_HOME` (state dir), `AIDEV_TEST_NO_ATTACH=1` (print the session, do not
attach), `AIDEV_TEST_ALLOW_NESTED=1` (allow a start from inside herdr), `AIDEV_TEST_WORKTREE_MODE=none`,
`AIDEV_TEST_REPO_PRIVATE=yes|no`, and `AIDEV_TEST_FAKE_HUMAN=<file>`. The last one is for tests only: tuios lets only
an attached client answer an Inbox question, so the driver reads its answers from lines in that file.

## Undo

Remove the `.zshrc_functions_test` line in `.zshrc`, then delete `.zshrc_functions_test`, `.config/aistack-test/`,
`.config/tuios/` and `tuios` in `packages-tui.nix`. Then run `tuios kill-server` and
`rm -rf ~/.ai/aidev_test ~/.ai/cache/aidev_test`.
