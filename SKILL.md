---
name: agentpeihe
description: Use when a task involves multiple agents, named executor models, staged gates, model capability reuse, production-like changes, deployment, cross-repository work, or unclear ownership. 中文名：agent配合。
---

# Agent 配合（agentpeihe）

**中文名称**：agent配合

## Purpose

Coordinate one approved gate at a time. Project risk rules come from the current project, while model qualification comes from the shared registry.

## Required Startup

Before planning or execution:

1. Read every applicable `AGENTS.md` and `CLAUDE.md` from project root to the target path.
2. If they conflict materially, list the exact conflict, stop and set Next Owner to Boss.
3. Extract current project red lines.
4. If named models or historical capability reuse is involved, read `/Users/shankluo/.agent-collaboration/model-capability-registry.md`.
5. Define one gate, a Todo list, allowed actions, forbidden actions, validation and stop conditions.

## Roles

- Owner / Boss: approves gates and resolves rule conflicts.
- Controller Agent: plans, audits evidence, assigns qualified models and updates the registry.
- Executor Agent: executes one approved gate, reports facts and stops.
- Specialist Agent: performs a bounded review or domain task; it cannot silently become controller.

## Model Capability Registry

Use `/Users/shankluo/.agent-collaboration/model-capability-registry.md` as the only qualification source. Do not copy its model table into this Skill or a project plan.

When assigning a model:

1. Identify provider, exact modelId, versionMode, toolProfile, policyVersion, identityEvidence, taskClass and requested risk.
2. Missing exact identity, identityEvidence or toolProfile means Candidate regardless of reputation.
3. Reuse qualification only for the same taskClass and equal-or-lower validated risk.
4. Run one targeted real-task canary when the registry says a canary is due.
5. Otherwise define one bounded calibration gate with automated validation.
6. Executors submit evidence but cannot promote themselves.
7. The controller updates qualification only after spec-compliance and code-quality review.
8. Re-read registryRevision before writing; if it changed, stop and merge instead of overwriting.

Qualification removes repeated model benchmarking only. It never removes project tests, task review, red-line approval or high-risk independent review.

If the registry cannot be read, report the exact failure and set Next Owner to Boss or Paused. Do not infer qualification from memory.

## Manual Relay Mode

Use this mode when the controller cannot directly invoke the selected model or the user prefers to copy prompts. Missing API, CLI or subagent routing is not a blocker and must not be presented as one.

The controller must output the recommended next model, bounded responsibility, selection reason, qualification status, `调用方式：人工中继，不声称已实际调用`, one self-contained `可复制提示词`, and the return requirements.

The copyable prompt names the project and rule paths, role, one gate, goal, allowed actions, forbidden actions, exact file scope, validation, stop conditions, report format, Runtime Identity and Next Owner. `Runtime Identity` reports the actual platform, exact visible model label and tool access; unknown fields are `unresolved`. It requires the external executor to stop after one gate and return both `Gate Execution Report` and:

```text
## Next Handoff Proposal
- Suggested model:
- Responsibility:
- Reason:
- Copyable prompt:
- Authority: proposal only; controller approval required
```

The executor's proposal never authorizes the next gate. The controller audits identity, scope, evidence, differences, risks and red lines, then approves, rewrites or rejects the proposal. A manual-relay task may run as a Candidate calibration when identity is unresolved, but it cannot create qualification evidence until the Boss confirms the model label shown by the target UI. Do not rename a local subagent to impersonate the selected external model.

## Gate Contract

Every gate contains:

```text
Gate name:
Goal:
Allowed actions:
Forbidden actions:
Validation:
Stop conditions:
Expected report format:
Next Owner after completion:
```

Only one gate may execute per approval. The executor stops after reporting and does not continue automatically.

## Controller Workflow

1. Review the plan and project rules.
2. Resolve model qualification from the shared registry.
3. Give one executor one gate.
4. Audit scope, validation, differences, red lines and rollback.
5. Reject any open Critical or Important issue.
6. Update project progress and, only when evidence is accepted, the registry.
7. Name Next Owner.

## Executor Workflow

1. Read project rules and the assigned gate.
2. Write a Todo list.
3. Execute only allowed actions.
4. Stop on unknown differences, permission problems, red lines or ambiguity.
5. Report actions, results, differences, omissions, risks and recommendation.
6. Name Next Owner and stop.

## Report Contract

```text
# Gate Execution Report

## Scope
- Approved gate:
- Allowed:
- Forbidden:

## Todo
- [x] completed item
- [ ] incomplete item

## Actions Taken
- factual actions

## Results
- commands and observed results

## Differences
- Whitelisted:
- Blacklisted:
- Unknown:

## Not Executed
- explicitly omitted actions

## Risks / Blockers
- current risks

## Recommendation
- Continue / stop / needs controller audit

## Next Owner
Current turn: Claude / Executor Agent / Boss / Other / Paused
Next action: one concrete action
Stop condition: one observable condition
```

## Next Owner Rule

Every non-short collaboration response ends with Next Owner naming both the actor and required action. Never use Next Owner to authorize an unapproved next gate.
