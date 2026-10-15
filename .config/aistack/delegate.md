---
description: Delegate a large, mechanical file edit to the free OpenCode Zen model (Big Pickle) and only review the result
argument-hint: "[the edit to delegate]"
---

Delegate this edit instead of writing it yourself: $ARGUMENTS

Every Edit or Write you make is billed output, and it stays in the conversation, re-read on every later turn. A free
model can do the typing, as long as the change is easy to specify and cheap to verify. `aidev -p` picks the model:
OpenCode Zen (Big Pickle) when this host has a Zen API key, otherwise aider on the local llama.cpp model, which never
leaves the machine (the work laptop). Measured on 2026-10-15 for one 10-line edit: Big Pickle 83 s, spec-exact; local
qwen3.5-9b through aider 134-152 s, logic right but it also changed text the spec said to keep. The local path is
slower and less exact, so give it a test command (`AIDEV_TEST_CMD`) whenever one exists: aider then feeds failures
back to the model before you review.

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
   `zsh -i -c 'AIDEV_TEST_CMD="<verify command>" aidev -p "<spec>" <files>' > "$TMPDIR/delegate.log" 2>&1; echo "exit=$?"; tail -5 "$TMPDIR/delegate.log"`
   Name the files to edit after the spec: aider (the local path) edits only files it is given or asks for.
4. Verify: run the verify command, then `git diff --stat`. Read only the hunks you need to check. OpenCode
   auto-formats every file it edits (ruff, prettier, nixfmt, shfmt, ...), so a file that was not already formatted
   shows extra format-only hunks; `git diff --ignore-all-space` hides most of them.
5. Fix small deviations yourself. If it went wrong, `git checkout -- <files>` and make the edit yourself; do not
   delegate the same thing twice.
