---
title: <short, specific title of the change>
status: draft
author: <who is writing this RFC>
date: YYYY-MM-DD
touches: <comma-separated repo-relative paths this RFC covers, e.g. .zshrc_functions_tuios>
---

<!-- status is one of: draft, review, approved, implemented -->

## 1. TL;DR

One or two sentences: what changes and why. Someone should be able to read only this and know whether the RFC is
relevant to them.

## 2. Problem

What is wrong or missing today. Concrete symptoms, not abstractions. Say who is affected and how often it happens.
Include the evidence you have (log lines, observed behaviour, cost figures).

## 3. Proposed solution

What we will do, in enough detail to implement. Name the files, tools and functions that change. Describe the
behaviour before and after. If the change has parts that can land separately, say in what order.

## 4. Alternatives considered

The other options and why they were not chosen. At least one real alternative. "Do nothing" counts when it is
genuinely on the table. For each: what it would look like, and the reason it loses.

## 5. Cost and billing impact

Which calls this change adds, removes or changes.

- Billed Claude calls: what is billed, how many calls per interaction, and how that changes.
- Free calls: local model calls, Lumo, and any other free path, and how those change.

State the expected effect in calls, not adjectives. If the effect is "none", say so and why.

## 6. Backwards compatibility and rollout

What breaks for existing plans, runs, configs or users, and what we do about it. Migration steps if any. Whether the
change can be reverted, and how. Any feature switch or staged rollout.

## 7. Success criteria

How we know it worked, in checks that pass or fail. Prefer observable signals: verify commands, log output, cost
figures, test results. Say what would make us reconsider or roll back.

## 8. Open questions

What is still undecided, and who decides. If there are none, write "None". Do not leave the list implied.

## When an RFC is required

An RFC is required for changes to:

- the research budget or the tools' file handling limits (for example the 16-call cap, the file size and line-range
  rules);
- billed-call patterns (when and how often a billed Claude call happens);
- tier assignment (which model serves which tier);
- verify / harness rules (what makes a task count as done);

An RFC is NOT required for bug fixes, tests, docs, and wording-only prompt edits.

## Process

RFCs live in `.config/aistack/rfcs/NNNN-slug.md`, numbered in order and named with a short slug (for example
`.config/aistack/rfcs/0003-research-budget.md`). Start from `../rfc-template.md`.

Status moves `draft -> review -> approved -> implemented`. Only an approved or implemented RFC counts;
a draft or review RFC does not gate anything. Move the status in the frontmatter as the RFC progresses.
