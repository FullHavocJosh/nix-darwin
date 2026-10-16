# Model routing

- Web research: use the `lumo_search` tool (Lumo, private and free). The built-in websearch is turned off. Use
  webfetch only to read one exact URL you already have, such as a link `lumo_search` returned. If `lumo_search` says
  its answer did not come from a web search, check the official source with webfetch.
- Library and framework documentation: the context7 tools (through mcp-lazy).
- Edits: make them yourself. `local_edit` (the on-device coder model) is there for a large mechanical edit the user
  wants kept on this machine.
- aidev (free builders: the on-device 30B, then Big Pickle; one Claude review). To hand off a feature you planned
  with the user, use the `/aidev-handoff` command: you write the plan and `aidev --handoff <dir>` builds it. For one
  self-contained edit a check can verify: `AIDEV_TEST_CMD="<check>" aidev -p "<exact change. Change nothing else.>"
<files>`, then review the diff. Plain `aidev` is the user's interactive planner: never run it yourself. In advisor
  mode, give the user the aidev command instead of running it.
