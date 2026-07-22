# 变更日志（CHANGELOG）

本项目所有值得一提的变化，按日期倒序记录。格式：日期 · 类型（feat/fix/docs/score）· 内容。

---

## 2026-07-22

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
