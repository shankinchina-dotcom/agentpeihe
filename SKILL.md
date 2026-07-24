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

## Score Calibration and Renewal

The registry keeps **multi-dimensional 0–100 dispatch scores** per model in its `## Scores` section — one score per capability dimension, never a single flattened number. A high score in one dimension says nothing about other dimensions. All scores are subordinate to the Qualification States — they never waive project tests, review or red-line approval.

### Dimensions（维度参照 2026 权威 agent 评测标准）

| 维度 | taskClass | 参照 benchmark | 衡量什么 |
|---|---|---|---|
| 前端能力 | frontend-ui | WebArena / OSWorld | UI 实现、页面调试、界面理解 |
| 后端实现 | backend-integration | SWE-bench Verified / Terminal-Bench | API、服务、部署、脚本、配置 |
| Agent 协同 | agent-orchestration | τ²-bench / BFCL v4（Agentic） | 拆任务、派子 agent、契约纪律、工具调用正确率 |
| 修 bug | complex-debugging | SWE-bench Verified / Terminal-Bench | 根因定位、证据链、最小修复 |
| 架构设计 | architecture-final-review | GAIA（高阶推理） | 系统设计、权衡取舍、文档表达 |
| 检索与格式化 | retrieval-formatting | GAIA L1 / BrowseComp | 信息提取、格式契约遵守 |
| 安全与数据 | security-data | 项目内评审 | 密钥处理、数据合规、红线意识 |

注意：2026 年 4 月 Berkeley RDI 已证明主流公开 benchmark 均可被 reward hacking 刷分，因此**本项目只信实战关卡证据**，公开榜单仅作维度参照系，不直接记分。

### Rules

1. `score: 0` in a dimension means uncalibrated **in that dimension**. A 0-score dimension may only receive a calibration gate (bounded, low-risk, automated validation). Production gates require the dimension score ≥ 60.
2. Passing a dimension's calibration sets that dimension to 60. Each subsequently accepted gate in the same dimension: +5 (cap 95). Rejected: −10 (floor 0 — back to calibration for that dimension only).
3. Give new models a chance: a newly registered model gets a calibration gate in at least one dimension before its first production need. When building the candidate list for a low/medium-risk gate, include at least one model with score < 60 **in that gate's dimension** if available, marked as a new-model opportunity.
4. Give proven models a chance to re-prove: a dimension score goes stale 30 days after its last accepted evidence in that dimension. After every 10 accepted gates — or when a stale model is needed — the controller schedules one low-risk renewal gate. Passing restores the score; failing applies −10. Stale models may still be dispatched at a −10 candidate-rating penalty in that dimension.
5. Quota exhaustion or unavailability is not a failure: mark cooldown (machine-readable `cooldown-until: YYYY-MM-DD`), deduct nothing, and on return offer one low-cost gate to re-establish availability.
6. Provisional scores: when evidence is still open (e.g. a diagnosis whose final root cause is unconfirmed), record the score with a `暂记` marker and re-judge once the evidence closes. Never treat a provisional score as final.
7. All score changes follow the registry write protocol: re-read registryRevision, merge instead of overwriting, increment by exactly 1.
8. Long-horizon scoring: a multi-gate sequence declared at intake as one long-horizon unit (≥3 related gates toward one goal) is scored as a single unit, not per-gate +5. On final acceptance: base +5 plus +2 per additional accepted sub-gate, capped at +15 per unit. While the unit is open the dimension score carries a 暂记 marker and settles once on closure; final rejection applies the standard −10. When agents rotate mid-task (e.g. quota cooldown), each agent is scored only for the sub-gates it actually executed. The unit's controller settles in the agent-orchestration dimension under the same rule.

## Manual Relay Mode

Use this mode when the controller cannot directly invoke the selected model or the user prefers to copy prompts. Missing API, CLI or subagent routing is not a blocker and must not be presented as one.

The controller must output the recommended next model, bounded responsibility, selection reason, qualification status, `调用方式：人工中继，不声称已实际调用`, one self-contained `可复制提示词`, and the return requirements.

The copyable prompt names the project and rule paths, role, one gate, goal, allowed actions, forbidden actions, exact file scope, validation, stop conditions, report format, Runtime Identity and Next Owner. In manual relay mode the executor's `Next Owner` must name the controller **and** the transport, e.g. `Next Owner: Controller（Claude），经主公人工中继转交` — so the human relaying the report sees the loop close without protocol knowledge. `Runtime Identity` reports the actual platform, exact visible model label and tool access; unknown fields are `unresolved`. It requires the external executor to stop after one gate and return both `Gate Execution Report` and:

```text
## Next Handoff Proposal
- Suggested model:
- Responsibility:
- Reason:
- Copyable prompt:
- Authority: proposal only; controller approval required
```

The executor's proposal never authorizes the next gate. The controller audits identity, scope, evidence, differences, risks and red lines, then approves, rewrites or rejects the proposal. A manual-relay task may run as a Candidate calibration when identity is unresolved, but it cannot create qualification evidence until the Boss confirms the model label shown by the target UI. Do not rename a local subagent to impersonate the selected external model.

## Project Intake Gate（立项关）

When the Boss's message is a project-level task, the controller runs a one-shot intake **before opening the first gate**. Trigger is judged by three signal tiers, strongest first:

1. **Explicit (always triggers)**: the Boss says "this is a project / run the intake gate / follow the long plan" — a hard button, no judgment needed.
2. **Artifact (near-always)**: the message attaches a todo list, design doc, requirements list or analysis doc, or references an existing Project Charter or gate IDs ("continue G3").
3. **Shape (judgment call)**: the task is inherently multi-stage (fix several bugs, deploy multiple machines, build a feature area), spans many turns, or is high-risk (production change, cross-repo, needs red lines and acceptance criteria).

**Skip (negative signal)**: single-step tasks answerable in one action (typo fix, count rows, Q&A, read a file) go straight to the gate flow — no ceremony for small work.

The intake is ONE message with three questions (the Boss answers in one reply — never a questionnaire wall):

1. **Plan**: Do you already have a long plan / todo list? (Yes → controller maps it to a gate sequence; No → controller drafts one for Boss confirmation.)
2. **Casting**: Fully automatic (dimension scores + vendor rules) / semi-pinned (Boss names only the Controller brain or the Reviewer) / fully pinned (Boss names all; controller only validates vendor separation and cooldowns).
3. **Red lines & acceptance**: What is forbidden, and what counts as done?

Output: a **Project Charter** (draft gate sequence + role assignment + red lines + acceptance criteria). The first gate opens only after the Boss confirms the charter; every later gate cites it as the context anchor.

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
6. Update project progress — make sure the executor's `AGENT_LOG.md` entry is appended (or write it on their behalf) — and, only when evidence is accepted, the registry.
7. Name Next Owner.

## Executor Workflow

1. Read project rules and the assigned gate.
2. Write a Todo list.
3. Execute only allowed actions.
4. Stop on unknown differences, permission problems, red lines or ambiguity.
5. Report actions, results, differences, omissions, risks and recommendation.
6. Name Next Owner and stop.
7. Once the controller accepts the report, append one entry to the project-root `AGENT_LOG.md` following the format defined in that file's header. If the file does not exist, skip — never create it yourself.

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
