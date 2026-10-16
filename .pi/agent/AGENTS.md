# aidev

aidev builds code with free models: the on-device 30B coder first, Big Pickle when that fails, and one Claude review.
Use it instead of writing large changes yourself:

- One self-contained edit that a check can verify: run
  `AIDEV_TEST_CMD="<check>" aidev -p "<exact change. Change nothing else.>" <files>`, then show the user the diff.
- A feature planned with the user: use the `/aidev-handoff` command. You write the plan, and `aidev --handoff <dir>`
  builds it.
- Plain `aidev` is the user's interactive planner. Never run it yourself; tell the user to run it.
