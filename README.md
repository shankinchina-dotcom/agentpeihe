# Agent 配合（agentpeihe）

多 Agent 协作的关卡（Gate）制度 —— 一次只批一个关卡，执行完汇报，不自动推进。

## 解决的问题

多个 Agent 协作时常见的问题：

- Agent A 干完活，Agent B 不知道，直接接着干，结果跑偏
- 没人审查中间结果，错到后面才发现
- 多个 Agent 同时改文件，冲突了没人管
- 不确定哪个模型适合干哪个活，每次都从头试

agentpeihe 用**关卡制度**解决这些问题：每个关卡明确定义能做什么、不能做什么、怎么验证、什么时候停。执行者干完一个关卡必须停下来汇报，由 Controller 审查后再决定下一步。

## 角色

| 角色 | 职责 |
|------|------|
| **Boss（老板/你）** | 批准每个关卡，解决规则冲突 |
| **Controller（控制器）** | 制定计划、审查证据、分配模型、更新模型能力注册表 |
| **Executor（执行者）** | 执行单个关卡，汇报事实后停止，不自行推进 |
| **Specialist（专家）** | 执行有边界的审查或领域任务，不能悄悄变成 Controller |

## 核心流程

```
Boss 提出任务
    ↓
Controller 读项目规则，定义关卡
    ↓
Boss 批准关卡
    ↓
Executor 执行 → 提交 Gate Execution Report
    ↓
Controller 审查差异和风险
    ↓
指定 Next Owner → 循环或结束
```

**关键原则：一次一个关卡，不跳步，不自动推进。**

## 安装

将 `SKILL.md` 放到 Claude Code 的 skills 目录：

```bash
mkdir -p ~/.claude/skills/agentpeihe
cp SKILL.md ~/.claude/skills/agentpeihe/
```

重启 Claude Code 或重新加载会话即可使用。

触发方式：
- 输入 `/agentpeihe`
- 或在对话中说「用 agent 配合」

## 关卡契约

每个关卡必须包含以下字段：

```text
Gate name:        关卡名称
Goal:             目标
Allowed actions:  允许的操作
Forbidden actions: 禁止的操作
Validation:       验证方式
Stop conditions:  停止条件
Expected report format: 期望的报告格式
Next Owner after completion: 完成后的下一个负责人
```

## Controller 工作流

1. 审查计划和项目规则
2. 从共享注册表确认模型能力
3. 给一个 Executor 分配一个关卡
4. 审查范围、验证、差异、红线和回滚方案
5. 拒绝任何未解决的 Critical 或 Important 问题
6. 更新项目进度；仅在证据被接受后更新注册表
7. 指定 Next Owner

## Executor 工作流

1. 阅读项目规则和被分配的关卡
2. 写 Todo 列表
3. 只执行允许的操作
4. 遇到未知差异、权限问题、红线或模糊情况立即停止
5. 汇报操作、结果、差异、遗漏、风险和建议
6. 指定 Next Owner 并停止

## 手动中继模式

当 Controller 无法直接调用选定模型，或你希望手动复制提示词时使用。

Controller 会输出：
- 推荐的下一步模型
- 职责边界
- 选择理由
- 能力认证状态
- **调用方式：人工中继，不声称已实际调用**
- 一份**可复制提示词**（自包含，可直接贴给另一个 Agent 执行）
- 返回要求

可复制提示词包含：项目和规则路径、角色、一个关卡、目标、允许/禁止操作、文件范围、验证方式、停止条件、报告格式、Runtime Identity 和 Next Owner。

Executor 执行完后必须返回：
1. **Gate Execution Report**（按下方模板）
2. **Next Handoff Proposal**（建议下一步模型和职责，仅建议，需 Controller 批准）

## 执行报告模板

```text
# Gate Execution Report

## Scope
- Approved gate:
- Allowed:
- Forbidden:

## Todo
- [x] 已完成
- [ ] 未完成

## Actions Taken
- 实际操作（事实陈述）

## Results
- 命令和观察到的结果

## Differences
- Whitelisted: 白名单差异
- Blacklisted: 黑名单差异
- Unknown: 未知差异

## Not Executed
- 明确跳过的操作及原因

## Risks / Blockers
- 当前风险和阻塞

## Recommendation
- Continue / stop / needs controller audit

## Next Owner
Current turn: Claude / Executor Agent / Boss / Other / Paused
Next action: 一个具体动作
Stop condition: 一个可观察的停止条件
```

## Next Owner 规则

每次非简短协作回复必须以 Next Owner 结尾，指明下一步由谁做什么。**绝不**用 Next Owner 来授权未经批准的下一关卡。

## 模型能力注册表

agentpeihe 使用共享的模型能力注册表（`~/.agent-collaboration/model-capability-registry.md`）来记录哪些模型在哪些任务类别上经过验证。

核心规则：
- 缺少精确身份、身份证据或工具配置的模型一律视为 Candidate，无论声誉如何
- 能力认证只在相同任务类别和同等或更低验证风险下复用
- Executor 可以提交证据，但不能自己提升自己的认证等级
- Controller 只在规格合规和代码质量审查通过后更新认证

## 适用场景

- 跨多个 Agent 的复杂任务
- 需要指定特定模型执行的任务
- 生产级变更或部署
- 跨仓库协作
- 任务所有权不明确的情况

## 不适用场景

- 简单单步任务（直接用普通对话）
- 纯信息查询
- 不需要多角色协作的日常开发
