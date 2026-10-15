---
description: Delegate a large, mechanical file edit to the free OpenCode Zen model (Big Pickle) and only review the result
argument-hint: "[the edit to delegate]"
---

Delegate this edit instead of writing it yourself: $ARGUMENTS

Every Edit or Write you make is billed output, and it stays in the conversation, re-read on every later turn. A free
model can do the typing, as long as the change is easy to specify and cheap to verify. Measured on 2026-10-15: Big
Pickle made a 10-line, spec-exact edit in 83 s; local Qwen (llama.cpp) took 152 s and missed part of the spec, so
it is not offered here.

Delegate only when ALL of these hold; otherwise make the edit yourself:

- It is big: roughly 5+ edits, several files, or a new file of 100+ lines.
- It is mechanical or fully specified: a rename or migration across files, repetitive changes, boilerplate, a new
  file from an exact spec. Not subtle logic, security-sensitive code, or anything you must read closely anyway.
- You can verify it cheaply: a test, linter, build or check command, or a short `git diff --stat`.

Steps:

1. `git status --short`: the files the delegate will touch must have no uncommitted changes of yours, so the diff shows
   only its work. Commit through gpa first if needed.
2. Write the spec as one prompt: the exact files, the behavior, function names and signatures, edge cases, and
   "Change nothing else." Add the verify command it should run when done.
3. Run it from the work directory, keeping its transcript out of this conversation:
   `zsh -i -c 'aidev -p "<spec>"' > "$TMPDIR/delegate.log" 2>&1; echo "exit=$?"; tail -5 "$TMPDIR/delegate.log"`
4. Verify: run the verify command, then `git diff --stat`. Read only the hunks you need to check. OpenCode
   auto-formats every file it edits (ruff, prettier, nixfmt, shfmt, ...), so a file that was not already formatted
   shows extra format-only hunks; `git diff --ignore-all-space` hides most of them.
5. Fix small deviations yourself. If it went wrong, `git checkout -- <files>` and make the edit yourself; do not
   delegate the same thing twice.
