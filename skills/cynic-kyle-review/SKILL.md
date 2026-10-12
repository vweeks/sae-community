---
name: cynic-kyle-review
description: Runs Cynicχl, an adversarial reviewer, on one decision, plan, or claimed result, as a helper agent that starts without this conversation. Use when the user asks for cynic-kyle or Cynicχl, when choosing between approaches, before calling work complete, and before writing up conclusions. Not for routine steps or style review.
license: MIT. See LICENSE.txt.
---

# Cynicχl review

Cynicχl is a reviewer that tries to break one decision, plan, or claimed result, and reports
only problems that would change a decision or a result. It works by not knowing how the
claim was reached: a reviewer that has seen the reasoning tends to agree with it. So it runs
as a separate helper agent, never in this conversation.

## Run it

1. Write the brief: the decision or claim, the goal and constraints it serves, what would
   count as done, and the paths to the evidence (files, code, data, results). Leave out how
   you reached the conclusion and why you think it's right.
2. If a subagent or custom agent named `cynic-kyle` is available (it may carry a plugin
   prefix, such as `sae-community:cynic-kyle`), give it the brief. Its own settings make it
   read-only. Start it without this conversation, as below.
3. Otherwise, start a helper agent without this conversation. Its message is the text of
   `references/prompt.md`, verbatim, then the line "You are a reviewer: read files only, and
   do not edit, create, or delete anything or run commands that change state.", then the
   brief.

How to start a helper without this conversation:

- Claude Code: a subagent started with the Agent tool begins with only the prompt you give
  it. Don't use a fork, which copies the conversation.
- Codex: call `spawn_agent` with `fork_turns: "none"`. The default copies this whole
  conversation into the helper, which defeats the review.
- Another tool: use its way of starting an agent with only the message you give it. If it
  can't start one that way, don't run the review in this conversation. Instead, give the
  user the text of `references/prompt.md` followed by the brief, and ask them to paste it
  into a new session and share the report back.

## Read-only

In step 3 the helper has this session's permissions, so read-only is an instruction, not a
setting the tool enforces. If its report says it changed anything, tell the user.

## After

Give the user the verdict line and the findings as the reviewer wrote them, without
softening them. Then decide with the user what to do about each one.
