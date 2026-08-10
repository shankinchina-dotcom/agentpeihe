# 变更日志（CHANGELOG）

本项目所有值得一提的变化，按日期倒序记录。格式：日期 · 类型（feat/fix/docs/score）· 内容。

---

## 2026-08-10

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
