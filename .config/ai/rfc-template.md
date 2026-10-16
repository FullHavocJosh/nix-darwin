---
title: <short, specific title of the change>
status: draft
date: YYYY-MM-DD
source: <tool/model that wrote it, e.g. ainfo/claude-sonnet, ai/claude-sonnet, opencode/big-pickle>
repo: <absolute path of the project it is about, or none>
touches: <comma-separated paths or resources it changes>
---

<!-- status: draft (written, not checked) | ready (checked, can be built) | in-progress | done | dropped -->
<!-- Write for a reader with none of this session's context: another model, another tool, or you next month. -->

## 1. TL;DR

One or two sentences: what changes and why.

## 2. Problem

What is wrong or missing today. Concrete symptoms and the evidence found (log lines, file:line, ticket keys, URLs).

## 3. Proposed solution

What to do, in enough detail to implement without this session: the files, functions, resources and commands that
change, the behaviour before and after, and the order of steps when parts can land separately.

## 4. Alternatives considered

At least one real alternative, and why it loses. "Do nothing" counts when it is genuinely on the table.

## 5. Risks and cost

What can break, the blast radius, billed calls or cloud cost it adds, and how to undo it.

## 6. Verification

How to know it worked: commands, tests or observable signals that pass or fail.

## 7. Open questions

What is still undecided, and who decides. "None" if there are none.
