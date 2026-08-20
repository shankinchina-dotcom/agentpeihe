# Prompt 编译器 + 执行者会话池（Sticky Executor）设计说明

> **目标读者：** 后续维护者。本文解释这套机制为什么长这样、依赖 omnigent 的哪些机制事实、怎么验收。
> 协议契约见 SKILL.md；生成逻辑见 `gen_controller_bundle.py` / `compile_gate_prompt.py` / `gen_repo_map.py`。

---

## 背景与问题

旧派发模型是「一关一个新会话」：每个关卡新派一个子会话，执行者进来先重读一遍项目规则、AGENTS.md、相关源码，读完才开始干活。问题有三个：

1. **重复读文件**。同一项目同一角色，G1 到 G5 读的是同一批文件，每关的输入都从零开始。
2. **前缀缓存浪费**。模型 API 的前缀缓存按「逐字节相同的最长前缀」命中；每关新会话 + 每关现场手拼 prompt（措辞、顺序、内容漂移），可缓存前缀几乎为零。
3. **无法审计**。prompt 靠 Controller 现场拼，同一关卡换个时机拼就不一样，事后无法复盘「当时到底给执行者喂了什么」。

省钱的因果关系要摆正：**主力是「减少输入总量 + 前缀纪律」**——输入 token 总量下降是硬省钱；逐字节稳定的固定头让可缓存前缀尽量长。**缓存命中只是打折不是免费**（命中部分折扣计费，未命中全价，且缓存有 TTL），只能当前缀纪律的副产品，不能当设计支柱。

另一个要掰正的观念：**复核者的独立性来自「不喂执行者推理过程」，而不是「另开一个会话对象」**。新开一个会话但把执行者的汇报全文、思路过程贴进去，独立性照样归零——评审者被锚定，复核退化成复读。反过来，只要评审输入里只有契约和产物路径，会话对象是新建还是复用，与独立性无关。这决定了 Reviewer 侧的极简上下文设计（见下文）。

## 依赖的 omnigent 机制事实

会话池不是新框架功能，是对 `sys_session_send` 既有语义的利用。以下每条都有源码实锤（以嵌套副本 `agentcenter/omnigent-zh-cn` 为准，见 PITFALLS.md 坑 26）：

- **create-or-continue**：同一 `(agent, title)` 组合再次调用 `sys_session_send` = 续跑同一子会话（带完整对话历史）；不同 title = 新建。查找逻辑：`omnigent/runner/tool_dispatch.py` 的 `_find_existing_child_session`（:902）与 `_send_to_existing_session`（:1891）；schema 描述原文「Lets later turns reuse the same conversation via another sys_session_send call with the same title」（`omnigent/tools/builtins/spawn.py:225`）。
- **参数名是 `title`**，不是业务文档旧称 `session_name`（PITFALLS.md 坑 27）。
- **续发不能改配置**：`model` / `harness` / `file_ids` / `cost_budget` 仅创建时有效，续发传了核心硬报错。想换模型 = 换名字开新会话。
- **忙碌保护 = 天然串行**：同会话有 turn 在跑时续发被拒。同一会话的关卡序列不需要任何外加锁，等子会话完成通知再续发即可。
- **close 是 tombstone**：`sys_session_close` 内部改写存储 title 释放名额（spawn.py:50 注释），同名之后可重建——「清零重来」= close + 同名重派。
- 辅助手段：Controller 可用 `sys_session_list` / `sys_session_get_info` / `sys_session_get_history` 查会话状态与历史长度（compact 监测的数据源）。
- 子会话**继承父会话 workspace**，所以「产物指针」就是契约文本里写共享文件路径，无需任何新机制。

## 三段式 Prompt 结构

每份关卡 prompt 固定三段，顺序不可变：

```text
[固定头]     角色纪律要点 + <project>/AGENTS.md 全文 + <project>/.agentpeihe/repo_map.md 全文
[本关契约]   9 字段（字段名、顺序、措辞由 compile_gate_prompt.py 钉死）
[产物指针]   每个前置关卡 ≤3 条，格式 `路径: 一句话说明`
```

- **固定头零动态字段**：不含日期、时间戳、随机 ID、关卡号——任何会变的字节都不许进固定头。引用的文件缺失时输出**固定占位行**，保证缺文件场景下输出同样确定。
- **两种模式**：
  - `initial`（默认）：三段全输出。用于新会话首发（含 close 后重建）。
  - `followup`：只输出 [本关契约] + [产物指针]。用于 sticky 会话续关——固定头已在会话历史里，重发既浪费输入又截断可缓存前缀。
- **编译必须走 `compile_gate_prompt.py`，禁止手拼**。脚本保证同输入逐字节同输出；手拼必有措辞/空白漂移，前缀缓存立即失效，也无法审计。逐字稳定性是缓存策略的地基，只能靠代码保证，不能靠纪律自觉。
- **产物指针纪律：每个前置关卡最多 3 条**。指针是路标不是搬运——超了说明前置关卡的产物没收敛，该让执行者先产出一份索引文件再指过来。

## 会话池策略（Sticky Executor）

- **稳定命名**：`<角色中文名>·<模型名>`，如 `关二爷·DeepSeek`、`法正·Grok`。同角色同模型**全程同名**，后续关卡用 followup 编译续发，复用同一会话的完整上下文。角色段仍限 SKILL.md 闭合集（关二爷/法正/马良/诸葛丞相/主公），禁止自创武将名。
- **并行例外**：同角色同模型需要并行跑两关时，名字追加 `-P2`/`-P3`（同名会撞忙碌保护）。这是唯一允许的名字后缀。
- **换模型/换角色 = 自然新会话**：名字变了就是新的 `(agent, title)`，无需任何额外操作。
- **清零上下文**：`sys_session_close` + 同名重派 = 全新会话（initial 编译重新首发）。适用场景：上下文逼近 compact 阈值（见下节）、任务方向大改、执行者状态可疑。
- 会话对象本身零成本——成本只在 turn 的输入输出，池子空转不花钱。
- 协议层硬规则全部不变：一次只批一个关卡、执行完汇报不自动推进、派发公布阵容 `角色=模型（agent id）`、阵容战报表、vendor 自检。会话池改的是运输层复用，不是审批纪律。

## compact 阈值

- 配置项：环境变量 **`AGENTPEIHE_COMPACT_THRESHOLD_TOKENS`**，默认 **80000**。`gen_controller_bundle.py` 读取它，把数值**烘进 controller prompt 并注明来源**。改阈值 = 改环境变量 + 重跑生成器 + 重启 server（server 拿的是启动快照，见 PITFALLS.md 坑 1）。
- **超阈值流程**（Controller 执行）：
  1. 令执行者产出 **State Summary（四段式事实状态）**：已完成事项、关键决策、在改文件清单、下一步（模板全文以生成器烘入 controller prompt 的文本为准；禁止推理过程流水账。设计意图是让下一棒不读全历史也能接手）。
  2. Summary 落盘到 `<project>/.agentpeihe/state/<角色>·<模型>.md`（子会话继承父 workspace，路径即指针）。
  3. `sys_session_close` 关旧会话。
  4. 同名重派：initial 编译 + 产物指针带一条 State Summary 路径。新会话从「固定头 + 契约 + summary 指针」冷启动，成本远低于带着几万 token 历史继续跑。
- **为什么只能 Controller 侧监测**：native TUI harness（kimi-native 等）的上下文在 CLI 进程内部，omnigent 管不到 CLI 内部的 token 计数与压缩行为。Controller 能拿到的只有自己发出去的 prompt 长度和 `sys_session_get_history` 的历史长度，所以阈值判断是**估算**——阈值要留余量，触发宜早不宜迟。

## Reviewer 极简上下文

Reviewer（法正）的编译输入只有：**固定头 + 本关契约 + 产物路径**。不给执行者的推理过程、工作日志、汇报全文。

- **论证**：见「背景与问题」——独立性来自信息隔离，隔离的是过程信息而不是会话对象。契约告诉法正「该做什么、红线是什么」，产物路径告诉他「去哪验」，这就够了；多看执行者的「我是这么想的」只会被锚定。
- **执行规则**：
  - 用 `compile_gate_prompt.py --role reviewer` 编译，同享会话池稳定命名（`法正·<模型>`）。
  - 复核是只读审查：读产物、跑验证命令、对照契约逐条核；不直接改执行者产物。
  - 既有硬规则不变：Reviewer 必须与 Executor 不同 vendor（派发时 Controller 声明双方 vendor 并自检）。
  - 法正确需背景细节时，指回 State Summary 文件，或由 Controller 转述**事实**（命令输出、diff）——不转述执行者的判断和推测。

## repo map 维护

- `python3 gen_repo_map.py <repo路径> [--out 路径]`，默认写 `<repo>/.agentpeihe/repo_map.md`。输出确定性排序、无日期，文件内注明「由 gen_repo_map.py 生成，仓库结构变化时重跑」。
- **何时重跑**：仓库结构变化（增删模块/顶层目录）、大重构之后、新项目首次接入。
- **何时不重跑**：不要每次编译前习惯性重跑。repo map 嵌在固定头里，map 一变固定头就变，全部会话的可缓存前缀作废。结构真变了要果断重跑（过期地图比缓存失效更害人），没变就别动。

## 验收自查方法

1. **固定头逐字稳定**：对同一项目用 `compile_gate_prompt.py` 连编 3 个不同关卡的 initial prompt，diff 三份的固定头段——必须逐字一致（空 diff）。
2. **输出确定性**：同一命令跑两遍，`diff` 为空；输出全文 grep 不到日期/时间戳/随机 ID。
3. **Reviewer 隔离**：reviewer 的编译输出里 grep 执行者汇报的特征字段（如「Actions Taken」「Differences」），应为零命中。
4. **会话池行为**：同名两次 `sys_session_send` 后，`sys_session_list` 里该 `(agent, title)` 只有一条会话；close 后同名重建成功，且新会话历史为空。

## 备选未采纳方案

**框架级强制粘性**——改 omnigent 核心 `tool_dispatch.py` 的会话查找键（例如忽略 title、按 agent 维度强制复用，或加 sticky 标志位）。暂不采纳，理由：

1. **bundle 层已够用**：稳定命名 + followup 编译 + close 重建，三件套拿到了粘性会话的全部收益，核心零改动。
2. **核心零改动 = 可 rebase**：omnigent 是跟随上游/monorepo 演进的外部依赖，核心每多一处私有补丁，升级就多一处冲突（本工作区双副本分叉的教训，见 PITFALLS.md 坑 26）。
3. **破坏面大**：查找键是全局行为，改动会影响所有靠 title 区分并行会话的现有用法（我们的 `-P2`/`-P3` 例外正是靠 title 区分）；bundle 层方案对核心语义零侵入。

若未来 bundle 层证明不够用（例如需要跨角色共享粘性上下文），再重新评估框架级方案——届时先补 `tool_dispatch.py` 的行为测试，再动查找键。
