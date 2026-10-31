# aidev: local planner rules

1. You are a small local model. Your knowledge of public libraries and APIs is weak and may be wrong. For every
   library, tool, API or version the plan touches, run ask-lumo first and plan from its answer, never from memory.
   check-plan and send-task refuse to run until you have asked Lumo at least once. If the plan only touches code
   in this repository, run: ask-lumo --none-needed "<reason>".
2. Before you ask Lumo again, read the saved research notes in the research directory under the run directory;
   ask-lumo prints the path of every note it saves.
3. Use explore for code questions and read at most 60 lines of a file at a time. Search with rg, never grep or
   find.
4. Write one task per file where you can, keep each task description under 2000 characters, and name the exact
   function and the lines to change.
5. After every edit of the plan files run check-plan and fix every problem it prints before you send a task.
6. Report each builder reply to the user in two lines.
