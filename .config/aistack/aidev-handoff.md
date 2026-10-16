---
description: Hand the build of the work discussed in this session to aidev (free builders, one Claude review)
argument-hint: "[what to build, if not obvious from the conversation]"
---

Hand off the build to aidev instead of building it in this session. This session already holds the context, so it
writes the plan once; aidev's free builders (the on-device 30B where it exists, Big Pickle when it fails or there is
no 30B) build it task by task, a task counts as done only when its verify commands exit 0, and Claude Code reviews the
whole result once. No billed planning call. Works the same from Claude Code, OpenCode and pi.

What to build: $ARGUMENTS (if empty, the change agreed in this conversation).

1. Write the plan as two files in a new directory `~/.ai/handoffs/YYYY-MM-DD-<slug>/` (any model may write there,
   advisor mode included). In advisor mode you cannot run aidev: give the user the command in step 4 instead. When the
   work comes from an RFC in `~/.ai/rfcs/`, name it in `description` and set that RFC's `status:` to `in-progress`.
   - `prd.json`: `{"name": "short-slug", "title": "...", "description": "...", "userStories": [{"id": "T1", "title": "...",
"description": "...", "acceptanceCriteria": ["..."], "priority": 1, "passes": false, "dependsOn": []}]}`
   - `verify.json`: `{"T1": ["command"]}`
2. Rules (aidev rejects a plan that breaks them; the reason comes back as `problems`):
   - `title` is the PR title: imperative, at most 72 characters, no `feat:` prefix. `description` is the PR summary,
     two to four sentences.
   - Each task fits one agent session of a weaker model. Its description names the files to create or change and the
     exact behavior: function names, signatures, where they are called from, edge cases. Do not leave it to guess.
   - `acceptanceCriteria`: concrete and testable. `priority` 1 runs first; `dependsOn` lists task ids that must finish
     first. `passes` is always false. Ids use letters, digits, `-` or `_`.
   - `verify` maps EVERY task id to at least one command that exits 0 only when that task is really done and does not
     pass on unrelated or empty state (tests, a linter, a build, a check script). Commands run without a shell: no
     `; & | < >`, backticks or `$()`. For a multi-step check, have the task create a script and run that.
   - At most 6 tasks. Only plan what you have checked in the code during this session.
3. Show the user the tasks and verify commands, and wait for a clear yes. Nothing starts before that.
4. From the repository's main checkout (or the directory the agents should work in), run:
   `aidev --handoff <plan dir>`
   In a main checkout this creates a git worktree and a draft PR through `gpr`, then starts the run in the
   background. It prints one JSON object: `started`, `run_id`, `work_dir`, `pr_url`, `events`, or `problems` /
   `problem` when it refused. On `problems`, fix the plan files and run it again.
5. Tell the user the run id, the work dir and PR, and that `aidev` in the project follows the run (pi offers to follow
   the active run). Then stop: do not watch the run from this session, that is what the handoff saves.
