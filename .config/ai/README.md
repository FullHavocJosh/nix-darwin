# ~/.ai

The one directory every AI tool on this machine writes to: ainfo, aidev, ai, Claude Code, OpenCode and pi
(RFC 0003 in `nix-darwin/.config/aistack/rfcs/`). `AI_HOME` moves it. This file and `rfc-template.md` are links into
the nix-darwin repo (`.config/ai/`); everything else here is local state and is never committed.

- `README.md`, `rfc-template.md`: this file and the RFC format.
- `rfcs/YYYY-MM-DD-slug.md`: RFCs, work saved for later or for another model or tool. Any model writes.
- `handoffs/YYYY-MM-DD-slug/`: `/aidev-handoff` plans (`prd.json`, `verify.json`). Any model writes.
- `ainfo/<project>-<hash>/`: ainfo state, transcripts and `advice-NNN.md`.
- `aidev/<project>-<hash>/`: aidev plans, runs, reviews, questions and progress.
- `ai/`: ai's pi agent dir and `claude-sessions.json`.
- `cache/<tool>/`: pi agent dirs, the local-edit server and locks, aider history.
- `guard/`: advisor on/off flags, the refusal log, edit-router counters. Only the hooks write here.

Models may write anywhere here except `guard/`. The advisor hook, Claude Code settings, OpenCode permissions and
ainfo's sandbox all refuse it: a model that could write there could switch off the hooks that restrict it.

## RFCs

Ask any session for an RFC and it lands in `rfcs/`:

- ainfo: "write an RFC for this"; the relay calls `ainfo_rfc` (Claude writes it, the bridge saves it).
- ai, Claude Code, OpenCode, pi: the model writes the file itself.

Start from one anywhere: point the session at the file, or run `aidev --rfc <name>` (a bare name is looked up here).
Format: `rfc-template.md`. Names are `YYYY-MM-DD-slug.md`; a taken name gets `-2`, `-3`. Move `status:` as the work
moves: `draft` (written, not checked), `ready` (checked, can be built), `in-progress`, `done`, `dropped`.

`python3 ~/.config/aistack/ai_home.py --write-rfc FILE --source <tool/model> --repo <path>` saves a file (or `-` for
stdin) as an RFC from any script, filling in the frontmatter it lacks.
