# ainfo: the read-only advisor

`ainfo` researches a question, error or URL and tells you how to fix it. It never changes anything: you are the hands and the brain.

```
ainfo "why did this terraform apply fail"      interactive: advice first, then follow-ups
terraform apply 2>&1 | ainfo                  pipe an error or log in
ainfo -p "question"                           one-shot: print the advice and exit
ainfo -c                                      continue this project's last session (after pi crashed)
```

## Who does what

| Part                | Does                                                                                                                                  | Never does                                                                               |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Qwen (local, in pi) | relays between you, Claude and Lumo; reports each hand-off; summarizes and shows which advice has a source                            | research, answer, edit, run commands (its only tools are the five `ainfo_*` relay tools) |
| Claude Code         | researches with every MCP server and read-only local reads; names the `path:line`; asks Lumo for every doc, manpage and best practice | edit, write, change state, browse the web                                                |
| Lumo (lumo-tamer)   | searches the web; returns links with quoted snippets                                                                                  | anything else (it has no tools)                                                          |

One question (one `ainfo_investigate`) is at most `AINFO_MAX_CLAUDE_CALLS` (3) Claude calls and `AINFO_MAX_LUMO_CALLS` (2) Lumo calls; the usual case is 2 Claude + 1 Lumo. Each Claude call is capped at `AINFO_CLAUDE_BUDGET_USD` (2.0). A follow-up in the same pi session is a new question with fresh counters; Claude resumes its session and Lumo keeps its last exchanges.

## How read-only is enforced (outside Claude Code)

A plain `claude` run is unaffected; none of this is in `~/.claude/settings.json`.

1. `ainfo_guard.py`: a default-deny `PreToolUse` hook passed with `claude --settings` for ainfo's calls only. Allows built-in Read/Grep/Glob/LS, a list of read-only shell commands (git, gh, terraform validate/show, kubectl get, ssh with a read-only remote command, curl GET, ...), and MCP tools whose names or `method` say they only read. Anything unknown is denied. Doppler secrets can be read (`secrets get/download`, MCP `secrets_get/list/download`) so Claude can authenticate to devices and MCP servers; they cannot be written or run (`set`, `delete`, `upload`, `run` are denied). Credential files on disk (`.env`, `*.tfvars`, keys) are denied. The `aws` CLI is allowed only with `--profile <name>-ro` whose SSO role is in `AINFO_AWS_RO_ROLES` (default `OpsReadOnly`, so IAM refuses writes too), and only for describe/get/list/lookup/search operations, `logs filter-log-events` and `s3 ls`; operations that return secret values, credentials or table/object data, `file://` arguments, `--debug` and `--endpoint-url` are denied. `aws sso login --profile <name>-ro` (no other flags) is allowed so Claude can refresh an expired SSO token; the user approves it in the browser. Secret-looking values are redacted from the event log, the advice and everything sent to Lumo.
2. `--disallowedTools Edit Write MultiEdit NotebookEdit WebFetch WebSearch Agent Task Skill`.
3. A `sandbox-exec` profile (`AINFO_SANDBOX=off` drops it) that refuses file writes outside cache and tool-state directories (including `~/.aws/sso/cache` and `~/.aws/cli/cache`, so the aws CLI can refresh its SSO token). `AINFO_SANDBOX_WRITE=/a:/b` adds more.

Change the policy in `ainfo_guard.py` and run `python3 -m unittest tests.test_guard` from this directory.

## Online research and sources

Claude lists what it wants documented as `lumo_lookups`; the bridge sends them to Lumo (credentials redacted first) and hands the answer back. Every URL in the final advice is checked: a link that neither Lumo nor a tool returned is reported as UNVERIFIED.

## Files

State and transcripts live in `~/.ainfo/<project>-<hash>/` (never inside a repository): `state.json` (Claude session id, Lumo history, cost), `events.jsonl` (hand-offs), `advice-NNN.md`, and `pi/` (pi's own session files, used by `ainfo -c`).
