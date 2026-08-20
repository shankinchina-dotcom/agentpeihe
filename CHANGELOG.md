# 变更日志（CHANGELOG）

本项目所有值得一提的变化，按日期倒序记录。格式：日期 · 类型（feat/fix/docs/score）· 内容。

---

## 2026-08-20

- **ops · 会话池 + Prompt 编译器上线并过金丝雀**：重跑生成器 + 重启 server 完成注册；三关连跑金丝雀（/tmp/ap_canary，G1→G2→G3 派 exec_deepseek）实测全过——Executor 子会话全程仅 1 个（稳定名「关二爷·DeepSeek」），首派 initial 编译含固定头、第 2/3 派 followup 只含契约段，法正（exec_xai）首条消息零执行者军报字段，战报表收尾；12 项 unittest 独立复跑全绿。
- **score · Codex 注册表 cooldown**：`Codex current model` 标 `cooldown-until: 2026-09-12`（usageLimitExceeded 实锤，额度耗尽不扣分）；registryRevision 35→36。
- **ops · 大脑临时切 pi**：codex cooldown 期间 `--brain pi`（deepseek API，headless 全工具桥）；codex 恢复后重跑生成器（不带 `--brain`）回默认优先级。
- **feat · 丞相大脑统一菜单（omnigent 前端一处补丁）**：`web/src/lib/agentLabels.ts` 的 `BRAIN_HARNESS_LABELS` 增加 `kimi-native`——丞相仍只有一个入口，大脑菜单内直接可选 Kimi（K3 TUI）/Codex/Pi 等；override→kimi-native 链路端到端实测通过（建空会话 + 首消息走 `/events` → turn 正常回包）。**同日取代**下方的「大脑变体 bundle」方案（变体已从生成器回退、已部署的 controller-k3 已清退）——变体改的是智能体清单，统一菜单改的是一行前端映射，后者才是 Boss 要的形态。
- **fix · 坑 31 harness_override 半拉子生效（omnigent runner 核心修复）**：override 到 kimi-native 的会话 turn 被 spec 默认大脑接走（TUI 空白、页面照跑）——runner `_session_harness_name` 只从 spec 反解。修复 = 会话级 override 缓存（create 时写入、turn 派发兜底、销毁清理）；回归测试 `tests/runner/test_session_harness_override.py` 3 项正反对照。改在嵌套副本 runner，新会话自动生效（runner 按会话新拉进程）。
- **fix · 坑 29 根因定位**：native 会话「create + initial_items」不自动起跑——runner 崩溃恢复保护（`runner/app.py:9906` 的 `is_native_harness` 分支）跳过首轮 kickoff；API 自动化绕法 = 先建空会话、首消息走 `/events`（UI 天然两步走，从未踩坑）。
- **~~feat · 大脑变体 bundle~~（同日被统一菜单方案取代，代码已回退）**：为每个可用大脑生成 `controller-<k3|...>` 变体 bundle 的思路保留在 git 历史（548b16d），如未来需要「同智能体不同提示词」变体可参考。
- **docs · 部署文档 §4.3.3 刷新**：丞相大脑菜单现为全量清单（Kimi K3 TUI 经 坑 31 修复后真实可选）；补 Codex 冷却期 pi 默认说明与「换脑验收看 TUI/runner 日志」锚点。
- **docs · PITFALLS 坑 28/29/30**：kimi 新目录信任引导卡死；纯 API 创建 kimi-native 顶层会话首轮注入 stalled（根因未定位，先记症状与绕法）；codex 配额冻结的「先记 cooldown 再换脑」处置流程。

## 2026-08-19

- **feat · 三段式 Prompt 编译器 `compile_gate_prompt.py`**：派关消息标准化为 固定头（角色纪律＋项目 AGENTS.md＋repo map）＋本关契约＋产物指针；initial/followup 双模式，同输入逐字节同输出（无时间戳）；Controller prompt 硬规则「派关必须用 sys_os_exec 调编译器、输出逐字作 sys_session_send 的 args，禁止手拼」。
- **feat · repo map 生成器 `gen_repo_map.py`**：产出 `<project>/.agentpeihe/repo_map.md` 作固定头组成部分，确定性排序、无日期，仓库结构变化时才重跑。
- **feat · 会话池命名新规（Sticky Executor）**：会话名改稳定名 `<角色中文名>·<模型名>`（去掉旧的关卡号和简述）——`sys_session_send` 同名 title = 续跑同一子会话（带完整历史），不同名 = 新建；续发禁传 model/harness/file_ids/cost_budget；并行关卡例外追加 `-P2`/`-P3`；换模型/换角色自然新会话；清零先 `sys_session_close` 再同名重派。生成器 Controller prompt 与 SKILL.md 同步。
- **fix · Controller prompt 去动态化**：正文删「于 {date} 生成」与 pool_table 的 cooldown 截止日期（cooldown 名单只打生成器 stdout，不进 bundle），同输入 prompt 逐字节稳定、可缓存；config.yaml `description` 的日期保留（不进 prompt，无害）。
- **feat · compact 阈值纪律**：环境变量 `AGENTPEIHE_COMPACT_THRESHOLD_TOKENS`（默认 80000）由生成器烘进 Controller prompt；超阈值流程 = Executor 写 State Summary（`<project>/.agentpeihe/state/<角色>·<模型>.md`，四段事实状态）→ 军报确认 → close → 同名重派 initial 编译，State Summary 作产物指针第一条。
- **feat · Reviewer 极简上下文**：法正派发消息只能是编译器 `--role reviewer` 输出（关卡契约＋产物路径），禁止转发 Executor 对话历史、禁止粘贴 Gate Execution Report 全文（Controller 留存审计）；Executor prompt 增续关语义（续关复用上下文、禁止重读已知文件）、State Summary 输出格式、军报 Results「上下文用量自报」。
- **docs · PITFALLS 坑 26/27 + 设计文档**：坑 26 双副本分叉（生产从嵌套副本 uv tool 安装，顶层 fork 已冻结并加 README 警示）；坑 27 `sys_session_send` 真名 `title` + create-or-continue 语义。新增 `docs/PROMPT_COMPILER_SESSION_POOL.md` 设计说明。
- **docs · PITFALLS 坑 22/24/25**：坑 24 补 K3 盒线 `│ >`（无反应 / 输入框未就绪）；禁止对 Welcome Escape。新坑 25：Hermes 长粘贴收成 `[Pasted text #N]` 不是没贴进去。坑 22 的「Escape 清 Welcome」改为只对 tip。

## 2026-08-18

- **docs · PITFALLS 坑 24 再修**：红字主因是 Welcome 被当成模态后 Escape 连打，不是 OAuth、也不是再打 `/login`。引擎改为静等 `>`、禁止对 Welcome 按键。

## 2026-08-14

- **docs · PITFALLS 坑 23/24 + 登录分流**：坑 23 收法正 inbox / Hermes 400 / `^A^K`；坑 24 写清 Kimi 0.36 冷启动 `No session yet` / TUI `/login` ≠ `kimi login` CLI。WINDOWS_HANDOFF、STEPS_6_8、W15、部署 §2 登录段同步。引擎提交 `f28777b`（新开会话生效）。

## 2026-08-10

- **docs · DeepSeek 默认 flash + 1M 上下文**：壳侧 `ANTHROPIC_MODEL=deepseek-v4-flash[1M]`；无 `[1M]` 时 TUI 常显示 200k。PITFALLS 坑 21；WINDOWS_HANDOFF / STEPS_6_8 / W16 示例 / 部署通道表同步；生成器 Controller prompt 与模块注释写明约定。
- **docs · PITFALLS 坑 17**：丞相网页改 Codex 时 labels 仍 stamp kimi-native-ui → 错起 Kimi + 模型 id 串台（与 agentcenter 前端 labels 跟 effective harness 修复同步）；并写清大脑壳对照（kimi-native / codex / codex-native）。
- **docs · 部署文档 §4.3.3**：丞相换大脑界面对照表 + GPT-5.6 推理档位（sol/terra 含 max/ultra）+ Boss 真实任务验收锚点。
- **feat · 关二爷关内多 Agent 纪律（prompt only，不 force_swarm）**：`gen_controller_bundle.py` 的 `EXECUTOR_PROMPT` + Controller 验收提示；`SKILL.md` Executor 节与军报 Results「子 Agent 清单」；部署 §4.3.4。允许 Kimi 等在本关内用内部集群加速，禁止破协作边界。
- **fix · 角色表闭合（禁自创赵云等）**：Controller prompt 固定 主公/诸葛丞相/关二爷/法正/马良；派发写「赵云=」等视为不合格须重写；`SKILL.md` Roles + Cast Visibility、部署 §4.4 同步。
- **docs · PITFALLS 坑 18/19 + 部署 §1.3**：Host/Server URL 与 6767 对齐纪律、`runner_disconnected` 根因；kimi catalog `kind=none` 观察项；双进程启动与自检命令。
- **docs · 坑 19 闭合（引擎 G0B）**：monorepo `model_catalog` 已将 kimi-native 读为 subscription（见 agentcenter CHANGELOG 同日）；部署/编排侧仍须重启 runner。

## 2026-08-04

- **docs · PITFALLS 新增坑 14/15/16**：native harness 的 turn 级 instructions 全被 del（launch 级投递才是活路：kimi=会话级 AGENTS.md、grok=--agent-profile、hermes=SOUL.md、claude=--append-system-prompt）；父子 kimi 会话同 workdir 时 forwarder 按 mtime 必锁错 wire（改 createdAt nearest-after-launch）；kimi 无 turn 完成上报致父子唤醒链断头（新增 kimi_native_status idle poster）。随 agentcenter `ab43288`/`597fe5c`/`deef41a` 端到端实测落地。
- **docs · 部署文档新增 §4.3.2（kimi-native 全功能）**：丞相可挂 kimi-native 大脑——AGENTS.md 角色注入 + 会话级 mcp.json/serve-mcp relay 调度（`mcp__omnigent__*`，可派全部五个 exec_* 工人）+ idle poster 唤醒链；同步修正 §4.2 生成器描述中"kimi-native 不生成"的过时表述。

## 2026-07-22

- **feat · 通道清乱（另一 agent 执行，Claude 审查通过）**：最终选型定版——丞相=Codex（harness: codex）；DeepSeek 经 CC Switch 套 Claude 壳（exec_deepseek / claude-native，借 Claude 底座）；Kimi 只走 kimi-native（omnigent 默认 `--yolo`，自动派活+手工双路径烟测 PASS）；官方 Anthropic 不进池。生成器同步：嗅探 deepseek 壳→生成 exec_deepseek、禁止 moonshot 占 Claude 壳、跳过同 vendor pi 工人、purge 残留目录。烟测证据：DeepSeek 壳落盘 `deepseek-cc-switch-ok`、Kimi 自动 `kimi-native-auto-ok`、Kimi 手工 `kimi-native-manual-ok`
- **fix · PITFALLS #5 更正**：kimi-native 并非"无解"——omnigent 默认启动参数含 `--yolo`（`_DEFAULT_KIMI_LAUNCH_ARGS`），此前"kimi 走 CC Switch 套壳"方案作废，改为通道隔离规则（Kimi=kimi-native，禁止占 Claude 壳）
- **docs · 部署文档新增 §4.3.1 通道隔离表**；交接文档 omnigent-channel-cleanup-handoff-2026-07-22.md + omnigent-kimi-native-tmux-macos-guide-2026-07-22.md 归档
- **verify · Kimi 手工双路径实测通过**（Boss 确认）：真终端 `omnigent-zh kimi` + 浏览器手选 Kimi 均正常应答；`omnigent-zh kimi` 在伪终端下的 `terminal does not support clear` 为 TERM 环境问题非故障

- **feat · Codex 归队**：额度恢复（Boss 确认，早于原 cooldown-until 2026-07-25），复证关通过（写中位数/极值脚本 + 法正 DeepSeek 独立复核全对），后端维度 0→60
- **feat · 池子 Codex 锁模型**：`gpt-5.6-sol [high]`（Boss 指定），pin 在 exec_openai 顶层 + 生成器常量 `CODEX_WORKER_MODEL`；注册表身份行同步（CLI 默认的 gpt-5.6-terra 记为另一身份）
- **fix · Codex 工人改 headless 形态**：codex-native（TUI/app-server）两次启动超时（"never started a thread"），单机 `codex exec` 正常 → 工人统一改 `harness: codex`（debby 官方验证形态），一次通过
- **feat · Grok Build ACP 接入（G3b）**：`grok agent stdio` ACP 握手成功，真实关卡通过；`exec_xai`（vendor=xai）入自动化池；生成器内置 grok 检测 + acp 配置块自动补全
- **feat · 立项关（Project Intake Gate）**：项目级任务启动前三问（长计划/角色偏好/红线验收），产出《项目章程》后开工；小任务跳过。已入 SKILL.md + 生成器模板 + 生产 prompt
- **docs · 子代理中文命名**：会话名强制 `关二爷-G1-...`/`法正-G2-...` 格式（Web UI 子代理图谱直接显示），禁止英文 slug
- **docs · PITFALLS 增至 11 条**：新增 #11（codex-native TUI 超时 → headless 形态）
- **score · 评分体系定稿**：单分制改 7 维度（前端/后端/Agent 协同/修 bug/架构/检索/安全）；G5diag 终审——Grok 65（两层根因全中）/ GPT-5.6 网页版 60（第一层）/ DeepSeek 0（未命中）；GPT-5.6 与 Codex CLI 拆分为两个身份
- **release · v1.0.0 定版**（agentcenter + agentpeihe 双仓）

## 2026-07-21

- **feat · G5 核心验收 8/8 通过**：Controller 拆关卡 → 异 vendor Executor/Reviewer 自动接力，全程无人工复制粘贴；阵型 = K3 壳（claude-sdk）→ executor_claude → reviewer_deepseek
- **fix · pi 路由双层故障实锤并修复**：① `model` 误放 `executor.config`（不透明兼容层）→ 移顶层 + `auth: {type: provider, name: deepseek}` 显式绑定；② host→runner 凭证白名单无 DEEPSEEK_API_KEY → `OMNIGENT_RUNNER_ENV_PASSTHROUGH`（Grok/GPT-5.6 两路独立诊断互证）
- **feat · controller 重构为 bundle**：照 polly 官方结构，子 agent 独立 config，`executor_claude` 配 `permission_mode: auto`（headless 免确认）
- **feat · 自动调配生成器**：gen_controller_bundle.py——环境检测 / CC Switch 真实 vendor 嗅探 / cooldown 摘除，换模型重跑不手改 YAML
- **feat · provider 配置**：DeepSeek gateway 实测 HTTP 200；Grok/Kimi 订阅 key 判定不适用 API（SuperGrok 无 API 额度、sk-kimi- 是 CLI 订阅 key），Kimi 改走 CLI、Grok 暂走人工中继（后于 07-22 ACP 接入）
- **feat · 国内外代理混用**：`HTTPS_PROXY=127.0.0.1:1082` + `NO_PROXY` 国内 API 白名单 + 端口存活条件式 export
- **feat · 模型校准制度**：Qwen（G0b 拒绝→G0b' 通过 60）/ DeepSeek（G0a 一次过 60），0 分只能接校准关规则首次实战
- **docs · 双机部署指南 + Windows 交接文档（G6）**：自包含 WSL2 协议（mirrored 网络/代理三活/8 项验收）
- **docs · PITFALLS.md 初版**：10 个实测坑（agent 注册/显示/headless 审批死锁/pi schema/runner 凭证/ CC Switch 换皮/代理混用）
- **chore · Monorepo 成型**：agentcenter = omnigent-zh-cn + ClaudeTeam + agentpeihe（subtree 合并，独立维护不跟上游）
