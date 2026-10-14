# aifo: the read-only advisor

`aifo` researches a question, error or URL and tells you how to fix it. It never changes anything: you are the hands and the brain.

```
aifo "why did this terraform apply fail"      interactive: advice first, then follow-ups
terraform apply 2>&1 | aifo                  pipe an error or log in
aifo -p "question"                           one-shot: print the advice and exit
aifo -c                                      continue this project's last session (after pi crashed)
```

## Who does what

| Part                | Does                                                                                                                                  | Never does                                                                              |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| Qwen (local, in pi) | relays between you, Claude and Lumo; reports each hand-off; summarizes and shows which advice has a source                            | research, answer, edit, run commands (its only tools are the five `aifo_*` relay tools) |
| Claude Code         | researches with every MCP server and read-only local reads; names the `path:line`; asks Lumo for every doc, manpage and best practice | edit, write, change state, browse the web                                               |
| Lumo (lumo-tamer)   | searches the web; returns links with quoted snippets                                                                                  | anything else (it has no tools)                                                         |

One question (one `aifo_investigate`) is at most `AIFO_MAX_CLAUDE_CALLS` (3) Claude calls and `AIFO_MAX_LUMO_CALLS` (2) Lumo calls; the usual case is 2 Claude + 1 Lumo. Each Claude call is capped at `AIFO_CLAUDE_BUDGET_USD` (2.0). A follow-up in the same pi session is a new question with fresh counters; Claude resumes its session and Lumo keeps its last exchanges.

## How read-only is enforced (outside Claude Code)

A plain `claude` run is unaffected; none of this is in `~/.claude/settings.json`.

1. `aifo_guard.py`: a default-deny `PreToolUse` hook passed with `claude --settings` for aifo's calls only. Allows built-in Read/Grep/Glob/LS, a list of read-only shell commands (git, gh, terraform validate/show, kubectl get, ssh with a read-only remote command, curl GET, ...), and MCP tools whose names or `method` say they only read. Anything unknown is denied. Secret-value tools (`doppler secrets get/list/download`) and credential files (`.env`, `*.tfvars`, keys) are denied.
2. `--disallowedTools Edit Write MultiEdit NotebookEdit WebFetch WebSearch Agent Task Skill`.
3. A `sandbox-exec` profile (`AIFO_SANDBOX=off` drops it) that refuses file writes outside cache and tool-state directories. `AIFO_SANDBOX_WRITE=/a:/b` adds more.

Change the policy in `aifo_guard.py` and run `python3 -m unittest tests.test_guard` from this directory.

## Online research and sources

Claude lists what it wants documented as `lumo_lookups`; the bridge sends them to Lumo (credentials redacted first) and hands the answer back. Every URL in the final advice is checked: a link that neither Lumo nor a tool returned is reported as UNVERIFIED.

## Files

State and transcripts live in `~/.aifo/<project>-<hash>/` (never inside a repository): `state.json` (Claude session id, Lumo history, cost), `events.jsonl` (hand-offs), `advice-NNN.md`, and `pi/` (pi's own session files, used by `aifo -c`).
