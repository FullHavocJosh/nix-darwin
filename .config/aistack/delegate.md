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
2. Call `local_edit` once per file (one edit at a time keeps the model's context small), with:
   - `instruction`: the exact change in that region, with names, signatures and edge cases, ending with
     "Change nothing else."
   - `file`: the one file to change or create.
   - `start_line` / `end_line`: the lines to rewrite (1-based, inclusive). The model sees only those lines plus 5
     numbered lines of context on each side. Required for files over 200 lines; at most 250 lines per call. Omit
     both for a small whole file or a new file.
   - `test_cmd`: a command that exits 0 when the edit is right. A failure goes back to the model once.
3. Review what it returns: `changed` (file and lines), `test`, and `diff` (capped; `git diff` for the rest).
4. Fix small deviations yourself. If it went wrong, `git checkout -- <file>` and make the edit yourself; do not
   delegate the same thing twice.

If `local_edit` is unavailable (the model is not on hosts below 32 GB) or fails, send the same request to
`oczen_edit` (OpenCode Zen Big Pickle, where a Zen key exists; changes outside the range are reverted). With
neither, use `aidev -p "<spec>" <files>` from
the work directory (aider on the 9B), output redirected to a file. Same rules, same review.

A PreToolUse hook (`edit_router_hook.py`) enforces this: the third different file edited by hand in one request is
refused with a pointer to these tools, unless neither exists, the file is not in a gpr worktree, a delegation
already failed in this request, or the file is one a delegation already covered (fixing up its result).
