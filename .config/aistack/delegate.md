---
description: Delegate a large, mechanical file edit to the free on-device coder model and only review the result
argument-hint: "[the edit to delegate]"
---

Delegate this edit instead of writing it yourself: $ARGUMENTS

Every Edit or Write you make is billed output, and it stays in the conversation, re-read on every later turn. The
`local_edit` tool hands the typing to Qwen3-Coder-30B on this machine (free, nothing leaves it), loaded on demand and
unloaded after 2 idle minutes. Measured on 2026-10-15: a 10-line edit in about 100 s including the model load, logic
right, but it also changed text the spec said to keep. So it pays only for big edits, and its result needs a review.

Delegate only when ALL of these hold; otherwise make the edit yourself:

- It is big enough: 3+ files or 5+ edits, or a new file of 100+ lines. (Measured: 7 edits in 6 files took 3
  turns and $0.09 through local_edit, 18 turns and $0.16 by hand.) A purely pattern-based replacement is cheaper
  still as one sed or python command.
- It is mechanical or fully specified: a rename or migration across files, repetitive changes, boilerplate, a new
  file from an exact spec. Not subtle logic, security-sensitive code, or anything you must read closely anyway.
- You can verify it cheaply: a test, linter, build or check command.

Steps:

1. `git status --short`: the files to edit should have no uncommitted changes of yours, so you can tell its work
   apart. Commit through gpa first if needed.
2. Call `local_edit` with:
   - `instruction`: the exact change, file by file, with names, signatures and edge cases, ending with
     "Change nothing else."
   - `files`: every file it may change or create; `read_only_files`: files it should only read.
   - `test_cmd`: a command that exits 0 when the edit is right. Failures go back to the model before it answers.
3. Review what it returns: `changed`, `test`, and `diff` (capped; `git diff` for the rest). Read only what you need.
4. Fix small deviations yourself. If it went wrong, `git checkout -- <files>` and make the edit yourself; do not
   delegate the same thing twice.

If `local_edit` reports the model is not on this machine (hosts below 32 GB), use `aidev -p "<spec>" <files>` from
the work directory instead, with its output redirected to a file: OpenCode Zen (Big Pickle) where a Zen key exists,
otherwise aider on the 9B. Same rules, same review.
