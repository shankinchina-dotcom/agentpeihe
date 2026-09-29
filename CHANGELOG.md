# 变更日志（CHANGELOG）

本项目所有值得一提的变化，按日期倒序记录。格式：日期 · 类型（feat/fix/docs/score）· 内容。

---

## 2026-09-29

- **docs · 会话命名补通道消歧三段式（`法正·codebuddy·DS`）**：Boss 明令——CodeBuddy 通道的 DeepSeek 会话名一律 `<角色>·codebuddy·DS`（禁再用 `法正·DeepSeek-v4.1`）。规则：同一模型经多通道接入时用 `<角色中文名>·<通道>·<模型缩写>` 三段式，换通道视同换模型用新名新建会话。生成器模板「会话池」「立项关」两节 + SKILL.md Session naming + 会话池文档同步（两仓）。`--brain pi --no-codex` 重跑后池表不变（5 工人）；codebuddy 探测默认模型 deepseek-v4.1-flash → vendor 自动判 deepseek，与 Boss「codebuddy 即 DeepSeek」明令一致（v33 回正 hy4 后的再次切换正式烘入）。伏羲项目侧：旧会话「法正·DeepSeek-v4.1」（G96–G99 复核完成）已 tombstone。
- **docs · PITFALLS 坑 36/37 落笔（伏羲 G101 实证）**：坑 36＝harness 240s 空闲看门狗 × 长任务 → Executor 分段交棒是唯一正确模式，Controller 契约禁写「等完成才交棒」，棒间由 Controller 盯后台日志再派收尾棒；坑 37＝发布关契约漏版本面（changelog.test.ts 锁五处：package.json/tauri.conf.json/Cargo.toml/两 lock/changelog.ts 首条）＋ `build:desktop` 不产 dmg（发布构建是 `npx tauri build`）。两仓同步。

## 2026-09-28

- **feat · Grok 4.6 → 4.7（xhigh effort）**：`~/.grok/config.toml` 已是 `models.default = "grok-4.7"` + `default_reasoning_effort = "xhigh"`。exec_xai 模型与 effort 均取 CLI 默认，壳侧零改动；同步生成器 pi 备选、omnigent onboarding pin、部署文档 provider 示例（两仓 + ClaudeTeam），注册表 Grok 行补注（floating-alias 延续）。重跑 + 重启 controller v32。
- **docs · Grok /model 写全局实证**：tmux 真实 TUI 实验——`/model grok-4.6` 同步改写 config.toml [models] default（机制与 CodeBuddy 一致：TUI 切换即改派单默认）；差异是 grok vendor 恒为 xai，池表无需重跑。部署文档 Grok 行补机制说明（两仓）。实验后 config 已恢复 grok-4.7 xhigh。
- **fix · CodeBuddy 模型链路实证 + 池表回正（controller v33）**：实测 TUI `/model` 与 `config set -g model` 均写全局默认，exec_codebuddy 派单模型随之切换；`--model` 进程级、`session/set_model` 会话级。Boss 裁「跟随 CLI 默认」：TUI 切完须重跑生成器 + 重启保持池表/vendor 一致；本次切回 hy4-preview-f 后已回正（v33，exec_codebuddy | tencent）。
- **feat · CodeBuddy 默认模型切 deepseek-v4.1-flash（vendor tencent→deepseek）**：`codebuddy config set -g model deepseek-v4.1-flash`（实测对 ACP 生效，currentModelId 回显一致），交互/ACP/派单全局默认统一切换。生成器升级：`sniff_codebuddy_model` + `codebuddy_vendor`——exec_codebuddy 的 vendor 按默认模型实际后端自动判定，不再写死 tencent。重跑 + 带 `--agent` 重启（controller v31），烟测实回「收到」。注册表 DeepSeek V4.1 Flash 行补 CodeBuddy 通道路由。

## 2026-09-24

- **feat · CodeBuddy 入池（exec_codebuddy，acp:codebuddy，vendor=tencent）**：hermes 火山额度尽后的新执行体。CodeBuddy CLI（2.157.0）原生 ACP（`codebuddy --acp`）实测全链路通过，omnigent 通用 acp harness 零代码接入（`~/.omnigent/config.yaml` acp.agents 加一行）。生成器新增 has_codebuddy 检测 + exec_codebuddy 工人块 + `--no-codex` 开关（Boss 裁：codex ChatGPT 登录不进池）；`ensure_acp_config` 改按条目幂等。模型跟 CLI 默认 hy4-preview-f；实测钉模型只有 `--acp --model <id>` 生效（session/new model 字段被忽略、session/set_model omnigent 不调用）。验证：AcpExecutor 直驱实回「派单成功」，`/v1/harnesses` 见 `acp:codebuddy`。
- **ops · GLM 5.2 冷却下架**：注册表 GLM 5.2 行加 `cooldown-until: 2026-12-31`（方舟 Plan 到期不续），重跑后 exec_zhipu 出池、bundle 目录 purge。重跑 + 带 `--agent` 重启：controller v30，池 = exec_deepseek / exec_moonshot / exec_xai / exec_codebuddy / exec_deepseek_hermes，大脑仍 pi(deepseek-flash)。

## 2026-09-11

- **feat · DeepSeek V4.1-Flash 切换（deepseek-flash）**：官方 2026-09-10 发布（原生视觉+原生 1M，Terminal-Bench 2.1 90.6），0731/vision-exp 下线暂时路由 V4.1。三通道切规范名：settings.json 全别名 `deepseek-flash[1M]`、hermes `default: deepseek-flash`、生成器两仓同步（prompt 9,042B）。注册表 rev→41：V4.1 继承 vision-exp 后端 60（Boss 钦定留痕），三旧身份 deprecated。重跑 + 带 `--agent` 重启（controller v28）。烟测：Anthropic 文本「收到」+ 图片「粉色」、hermes 实答 4，均无降级。G64 根修向新丞相（K3）重派 + G65 V4.1 校准关立项。

## 2026-09-09

- **feat · DeepSeek 模型池更新（官方 2026-08 版）**：Claude 壳主力默认 `deepseek-v4-flash-vision-exp[1M]`（Haiku/Fable/Sonnet/Opus 别名全统一；视觉 + 1M，Anthropic 端点文本+图片烟测无静默降级）；pi 直连备选 `deepseek-v4-flash`（官方已指向 V4-Flash-0731）；hermes 默认改直连 DeepSeek `deepseek-v4-flash`（0731），GLM 5.2 自动通道退出默认池（hermes 内 /model 可手选）。agentpeihe 生成器与部署/坑文档两仓同步，生成器 exec_zhipu 分支加 GLM 嗅探门。
- **ops · 线上池重建 + server 重启**：正式重跑生成器（删 exec_zhipu、重写 exec_deepseek/exec_moonshot/exec_xai/controller）；server 按原参数重启后 `/v1/agents` 确认 controller v23 注册、5 个在跑会话全部 reattach。注册表 rev 36→37：vision-exp 登记为默认身份，Boss 钦定继承 Flash 后端 60（备注留痕）。hermes_executor `--source tool` 不兼容疑点复核为误报（参数属 `chat` 子命令，实测正常），executor 不改。
- **feat · DeepSeek 第二通道 exec_deepseek_hermes 入池**：hermes 默认模型为 DeepSeek 时生成器自动生成（hermes-native 直连 api.deepseek.com，V4-Flash-0731）；注册表 rev→38 登记新身份（Candidate，未校准）。**修正**：server 重启必须带 `--agent` 才重新注册 bundle——裸参数重启后 controller 停在 v23/2026-08-20，带 `--agent` 重启后 v24（description 日期 2026-09-09）生效；新工人直发烟测实回「收到」。
- **feat · Grok 4.5 → 4.6 上线**：grok CLI 默认已是 grok-4.6（`~/.grok/config.toml` 核实），exec_xai（acp:grok-build）壳侧零改动；直发烟测实回「收到」，grok 会话记录坐实 `grok-4.6` / `grok-4.6-build`。生成器 pi 备选、omnigent onboarding pin（grok-3→4.6）、部署文档两仓同步；注册表 rev→39 填实 Grok 身份（floating-alias 延续，分数不动）。controller v25 注册生效，丞相派单链路实测可用。
- **feat · GLM 5.2 恢复自动派活 + omnigent hermes-native 模型钉住**：`_derive_terminal_launch_args_from_spec` 新增 hermes-native 分支（worker `executor.model` + `config.provider` → hermes TUI 启动参数 `-m/--provider`，两仓，`test_sessions_yolo_launch_args` 各 17 绿）；生成器嗅探方舟 plan 默认模型生成 exec_zhipu（不再随 hermes 全局默认漂移）。活体实证：子代理派发 → `terminal_launch_args` 落库 → 窗格页脚 `glm-5-2-260617 │ 1M` → 实答「收到」。注册表 rev→40。controller v26。
- **fix · controller prompt 撞 tmux 16KB 硬顶（坑 34/35）→ A 治标 + B 根修立项（G64）**：claude-native 子会话启动命令注入 controller 完整 prompt（runner/app.py:5909 按 session.agent_id 解 spec），prompt 涨至 10,718B → 命令包 ≈16.9KB 超 tmux 16KB imsg 硬顶（实测 16,000 过 / 16,384 拒），09-08 晚起 192 次 `command too long`，exec_deepseek 派发全挂（native_terminal_start_failed）。A：生成器 9 处修剪（模型池备注去重 + 各节冗词压缩，规则全保留）→ 9,091B；重跑 + 带 `--agent` 重启（controller v27）；tombstone 旧会话（105K tokens）后丞相按 G61 先例同名重派 G63——conv_ea740ec0 running、ctx 69K、零新增 command too long（vision-exp 首个正式关）。B：G64 立项（子会话改注入子 agent 自己 spec prompt；>12KB 降级 WARN 不硬失败），已派丞相排期。坑 34（子代理 runner 不换绑 + close 跨时代盲区）、坑 35 录 PITFALLS（两仓）。
- **docs · 部署文档新增 §4.7 日常操作卡**：UI 主路找丞相 / 异常三读数 / 复位=close+同名重派 / 变更三条纪律（`--agent`、`command too long` 盯梢、≤12KB）/ API 注入信封（`data`+content list）；§4.3 增 prompt 尺寸预算条、附录 A 踩坑表第 8 行（两仓同步）。

## 2026-08-18

- **fix · Kimi Welcome 不再 Escape 刷屏**：`conv_87c12d` 实证——353471d 已加载仍刷 ~38 行 `Send /login`。根因不是再打 Enter：Welcome 被当成焦点遮挡，`context:` 先于 `>` 出现时 `_settle_pane` 每 0.8s Escape（30s ≈ 38 下），K3 无 chat session 时一键一行红字。Welcome 移出 `_FOCUS_BLOCKERS`；就绪改为必须 `context:` + `>`（冷启动静等，不按键）；只有 tip/trust/sign-in 才 Escape；空输入框不再 Backspace。`test_kimi_native_executor` 回归。**新开会话生效**（已刷过的 pane 清不掉历史红字）。
- **fix · Hermes 长粘贴收成 chip 后仍提交**：`conv_949c2666` 法正 G20 首条 37 行已进输入框（`[Pasted text #3]`），引擎只在 pane 里找原文末行，误报「未接收粘贴」不按 Enter。把 paste chip 视为已提交。`test_hermes_native_bridge` 39 绿。现场补 Enter 后 TUI 已 `Initializing agent`；G20 交卷与丞相 inbox **未在本条关闭**。
- **fix · K3 盒线输入框 `│ >` 算就绪**：`conv_8e588d8e` 新开会话欢迎栏 `Session:` 为空、输入框是盒线 `│ >`，旧检测只认行首 `>`，静等超时「输入框未就绪」、网页无反应。识别盒线 `>`；空盒不算草稿。

## 2026-08-14

- **fix · 父会话有未读 inbox 时不 reap 原生 pane**：法正 idle 交卷后 丞相 Kimi 仍被 1800s 收割，wake 注入落空。`parent_should_keep_native_pane`：有未完成工人、inbox 未抽空、或终态未投递，都不收；pane 自愈重建后补一次 wake。
- **fix · Kimi 首条提交失败后禁止连打 Enter**：0.36/K3 首条常回 `No active session. Send /login`，草稿还在输入框，旧逻辑 8 秒内每 0.5s 再 Enter（约 16 行刷屏）。见到该错误立即停手。这是空 `Session:` 刷屏的主因，503f83d 没盖住这条路径。
- **fix · Kimi K3 不再死刷 TUI `/login`**：欢迎栏已有 `Session: session_…` 或滚动区已堆 `Send /login` 时禁止再注入 `/login`；bridge 目录落一次性标记，inject 重试也不打第二下。修选 K3 后同一错误刷十几行。
- **docs · PITFALLS 坑 24 + 登录分流**：TUI `/login`（进程内 session）≠ `kimi login` CLI（OAuth）。坑 23 登录条改指向坑 24；WINDOWS_HANDOFF / STEPS_6_8 / W15 / 部署登录段同步。
- **fix · Kimi 冷启动自动 TUI `/login`**：0.36 每次新 pane 都打 `No session yet` / `Send /login to login`，OAuth 其实已登录（`kimi login` CLI 直接 Logged in）。网页第一条贴不进进程内 session，红字还把「请执行 kimi login」误注入成用户消息。引擎在冷启动屏只打一次 TUI `/login`（你手动斜杠的那个），成功后再贴真任务；已有 `N messages` 或 Already logged in 不打。真设备码授权才红字要浏览器。
- **fix · Kimi 登录闸误杀就绪输入框**：首条消息前 TUI 会留下 `Error: No active session. Send /login to login.`，但 `>` + `context:` 已可贴。整屏扫描会误判为必须 `kimi login`。改为输入框已就绪则不当登录失败。token 本身有效时直接重发即可。
- **fix · 派工唤醒/注入四连**：① Hermes usage 不再 POST 仅含 `model` 的 `external_session_usage`（服务端 400 死刷），改为 `external_model_change`，4xx 不再每轮重试。② Hermes `state.db` 无 `sessions` 表时从 `messages.session_id` 发现会话，终态仍上报 `idle` 唤醒父 inbox。③ 父会话有未完成工人时 native pane reaper 不收割（等回报时 TUI 被 1800s 杀掉导致注入无处落）。④ Kimi 终端出现 `No active session` / `run /login` 立即中文失败、禁止重试死刷。⑤ Hermes 清草稿改 End+Backspace，禁止 C-a/C-k 泄露为 `^A^K`。相关 pytest 覆盖 usage/discovery/login/reaper/clear。**需重启 host/runner**。
- **fix · hermes-native 长关卡提示词冷启动丢贴**：法正 GLM 等首条 9 字段契约过长、TUI 未就绪时粘贴失败。≥4000 字改为写入 `omnigent_injected_task.md`、只注入短指针；粘贴等待按体积加长；大文案首次 settle 至少 45s。`test_hermes_native_bridge` 37 绿。**需重启 host**。

## 2026-08-11

- **fix · kimi-native 首条真投递**：不只红字，修 tip 抢焦点导致粘贴丢——就绪须 `context:` 且非 tip 独占（无 `>` 时 Escape 驱离 Welcome/Use Kimi K…）；投递前 dismiss + Backspace 清草稿（不靠 C-a/C-k）；bracketed paste 失败后对短单行（如 `/swarm on`）回退 `send-keys -l`；最多 3 轮整包重投。`test_kimi_native_executor` 42 项通过。**需重启 host**。

## 2026-08-10

- **docs · DeepSeek 默认 1M 上下文**：Claude 壳主模型须带 `[1M]` 后缀。约定：`~/.claude/settings.json` 的 `ANTHROPIC_MODEL=deepseek-v4-flash[1M]`（默认仍为 **flash**，非 pro）；Haiku/Fable 别名同为 `deepseek-v4-flash[1M]`；Sonnet/Opus 别名 `deepseek-v4-pro[1M]`。仅写 `deepseek-v4-flash`（无后缀）时 TUI 常显示 **200k Ctx**。pi/OpenAI 兼容路径模型 id 仍用无后缀的 `deepseek-v4-flash`（与 Anthropic 兼容壳 id 不同）。见 PITFALLS 坑 21、WINDOWS_HANDOFF / STEPS_6_8 / W16 示例。
- **fix · kimi-native 投递减假阴**：粘贴等待按内容加长（8–20s）；就绪后短 pause 再贴；粘贴未见则 Escape 后整包重投 1 次（仅未见草稿时，不双提交）；针尖前缀匹配；`/swarm on` 与用户消息分开失败文案。针对 G3「未接收粘贴」红字假阴。`test_kimi_native_executor` 40 项通过。**需重启 host/runner**。
- **fix · 派工交付闭环（问题 1，多 harness）+ 中文红字**：丞相 `sys_session_send` 工人侧首条任务「假成功」收紧——TUI paste 族就绪/粘贴/提交校验失败才 `TurnComplete`，失败 `ExecutorError` 中文红字（可带终端末尾）。覆盖：`kimi-native`（硬等 context: + Enter 重试）、`claude-native`（DeepSeek 壳；禁 blind submit + 中文）、`hermes-native`（GLM；store 确认 + 粘贴未见不 Enter + 中文）、`goose-native`（硬 settle + 单 Enter 禁止二次）、`cursor-native`（硬就绪 + 草稿校验 + Enter 重试）、`qwen-native` inject 中文；`acp:grok-build` 超时/进程/启动失败中文。各 native executor 空消息统一「…本轮没有可发送的用户消息」。相关 inject/bridge 回归 79+ 绿；claude MCP subprocess 3 项环境超时与本次无关。**需重启 host/runner**。并发闸（问题 2）未做。
- **fix · kimi-native 注入闭环（就绪→粘贴校验→Enter 重试）+ 中文红字**：`inject_user_message` 不再在 Welcome/冷启动时软超时后静默 TurnComplete。硬等 `context:` 就绪；粘贴后校验草稿进输入框；提交后若草稿仍在则重发 Enter；失败 `ExecutorError` 全中文（含终端末尾摘要）。修关二爷 G1 空 TUI 假成功。`pytest tests/inner/test_kimi_native_executor.py` 38 项通过。**需重启 host/runner 加载**。
- **fix · 丞相切换大脑时 labels 跟随 effective harness**：G7 只让模型列表跟 `pickedHarness`，创建会话时 `omnigent.wrapper` 仍按 agent 默认 harness 落盘。现象：网页选丞相+Codex+gpt-5.6-*，仍 stamp `kimi-native-ui` → ensure Kimi TUI → 报 `Model "gpt-5.6-terra" is not configured in config.toml`。`handleCreate` 的 labels/能力 knobs 统一用 effective harness；默认 kimi-native 仍 stamp Kimi。vitest harness-switch + nativeWrapperLabels 回归通过；web-ui 已 rebuild。
- **fix · Codex GPT-5.6 推理档位对齐本机目录**：静态选择器与 `CODEX_EFFORTS`/`EFFORT_VALUES` 补 `max`/`ultra`；sol/terra = low→ultra，luna = low→max（无 ultra）；去掉 5.6 目录已下架的 `minimal`。依据 `~/.codex/models_cache.json`。`pytest` reasoning_effort 5 项 + modelPicker/flow 相关 vitest 通过。
- **verify · 丞相+Codex 真实任务 PASS（Boss）**：修复后新建会话 harness=`codex`、终端为 Omnigent REPL（`omnigent attach`，首启 dark/light 主题选择属预期），后台 `codex app-server`；Boss 确认真实任务已跑通。说明：菜单「Codex」= 大脑 harness `codex`（非 `codex-native` TUI）；真·Codex TUI 走执行器预设 `codex-native-ui`。
- **docs · PITFALLS 坑 17 + 部署 §4.3.3**：记录 labels/harness 分叉、大脑 UI 壳对照（kimi-native→Kimi TUI / codex→Omnigent REPL / codex-native→Codex TUI）、推理档位表。
- **feat · 关二爷关内多 Agent 纪律（生成器 prompt，不 force_swarm）**：工人 `EXECUTOR_PROMPT` 写入 Kimi 集群硬约束（本关内可用满内部多 Agent；主 Executor 整合；禁并发改同文件；军报子 Agent 清单；禁 commit/push/部署等）；Controller 验收提示；`SKILL.md` + 部署 §4.3.4。重跑 `gen_controller_bundle.py` 后生效。
- **fix · 角色表闭合**：Controller 禁止自创三国名（赵云等）；Executor 派发必须「关二爷=…」；SKILL / 部署 §4.4 / 生成器同步。
- **docs · PITFALLS 坑 18/19 + 启动纪律**：Host `config.server` 与 Server 端口必须一致（常见 8000 vs 6767 → `runner_disconnected`）；server+host 双进程；侧栏子 agent 非 OS 僵尸说明；kimi-native `kind=none` / `.kimi` vs `.kimi-code` 标观察中（G0B 待修引擎）。README 三分钟启动与部署 §1.3 同步。
- **fix · G0B kimi-native catalog 读数（`kind=none` 误杀）**：`model_catalog` 对 kimi CLI 解析为 `subscription` + 静态 `kimi-code/*` 模型列表；无 CLI 时 note 指向 `~/.kimi-code` 而非「cannot run here」。spawn 行为不变。pytest `test_model_catalog`（含新增 kimi 用例）通过。**需重启 runner** 加载。
- **chore · Codex 模型策略：仅 GPT-5.6**：catalog 静态 codex 列表由 `gpt-5.5/5.4/5.4-mini` 改为 `gpt-5.6-sol/terra/luna`；ClaudeTeam 默认 worker 模型同步；部署文档写明禁止 5.5/5.4（避免 `effort=max` + mini 触发 `unsupported_value`）。池子 `CODEX_WORKER_MODEL` 本就为 `gpt-5.6-sol`。

## 2026-08-04

- **fix · 丞相+kimi-native 角色注入 + 强制多 agent 协同（`ab43288`）**：根修「丞相+K3 会话不派活、自己动手」——kimi-native 通道三层丢弃 instructions（executor `del system_prompt`、runner `del agent_spec`、无 --append-system-prompt 等价物）。① port 会话级 AGENTS.md 注入（角色 prompt 写入 `$KIMI_CODE_HOME/AGENTS.md`，进 system prompt）；② 新增 `tools.agents` 机器标记（harness 无关，不绑 K3）触发的强制 swarm：terminal create 写 `force_swarm` marker，首条用户消息前向 TUI 提交 `/swarm on`，失败保留重试，普通 kimi 会话零影响。端到端实测：新会话启动即 swarm，丞相 AgentSwarm 派两路斥候完成 G1 军报；相关 77 项 pytest 全绿。其余大脑通道（codex/pi/claude-sdk/claude-native/grok）审计确认注入与调度工具本就到位。
- **feat · kimi-native 接通 omnigent MCP 调度面（`597fe5c`）**：Kimi 丞相从「内置 AgentSwarm 派同 vendor 斥候」升级为「`sys_session_send` 派 exec_* 真工人」——tools.agents/spawn 的 kimi 会话 launch 前起 serve-mcp relay + 会话级 mcp.json materialize（读全局合并、只写会话 home），`mcp__omnigent__*` 增量进入且 kimi 原生 Agent/AgentSwarm 零影响，force_swarm 降为兜底。连带三修复：forwarder 错 wire（同 workdir 父子会话按 mtime 必锁错，改 state.json createdAt nearest-after-launch）、kimi 无 turn 完成上报（新增 kimi_native_status idle poster，wire 推导终态 step.end → POST idle，posted-count 幂等）、idle POST client 缺 base_url。端到端全链实证：丞相派 exec_moonshot（「关二爷·Kimi-G1-…」挂侧栏）→ 工人 9 字段 Gate Report → 丞相唤醒验收 **G1 PASS 呈军报**；相关 111 项 pytest 全绿。
- **feat · exec_xai/exec_zhipu 工人角色注入修复（`deef41a`）**：两个工人侧角色保真降级修复。① Grok 工人从「角色折叠进首条消息」升级为原生 `--agent-profile` 注入（frontmatter+body append 进默认 system prompt，grok 0.2.117 冒烟实证）；② GLM(hermes-native) 工人角色 prompt 完全断裂修复——per-session `HERMES_HOME/SOUL.md` 注入（SOUL.md 只从 HERMES_HOME 读，主 identity 槽）。端到端全制度实测：丞相(Kimi) 派 关二爷·Grok 执行 + 法正·DeepSeek 异 vendor 核验，法正 PASS，G1 验收呈军报+阵容战报表。

## 2026-08-01

- **release · v1.2.1**：07-31 晚间增量——G6/G7（丞相 harness 切换菜单 + 模型选项跟随有效 harness）、Codex 模型目录纠正为 GPT-5.6 家族三档（sol/terra/luna）+ 思考强度、DeepSeek 默认 → flash（G0d 校准上岗）、ClaudeTeam 审批模式三件套（approval-mode 开关 / 看板显示 / 完成自动通知）、飞书通道修复确认。omnigent 会话历史同日清空重置。
- **feat · 审批模式飞书按钮端到端打通**：看板卡片三按钮（boss/manager/auto）点击直切模式并重发看板；slash `/审批` 命令上线。排障四项：ClaudeTeam 守护进程全灭 29 天重建、proxy 环境致 TLS 断连崩溃循环（守护进程改净环境运行）、双 router 冲突清理、卡片按钮 `{tag:"action"}` 被 schema V2 拒绝改直放（`fe832af`）。
- **docs · PITFALLS 新增坑 12/13**：卡片 schema V2 按钮结构、守护进程 proxy 环境。

## 2026-07-31

- **release · v1.2.0**：自 v1.1.0 以来的全部内容——omnigent 内核修复 8 项（#3012 登录续期、#3016 session snapshot、#2967 reactive compaction、#2853 native 丢 prompt、#2854 harness_override kickoff、#3003 policy 读取合并、#3004 事件 ACL 缓存、#2702 idle 退避）+ 本地新发现修复 2 项（runner 系统代理劫持、kimi forwarder 错 wire）；制度 4 项（AGENT_LOG 工作日志、长程计分规则 8、阵容可见性、生成器 hermes/kimi 扩展）；模型池 2 项（GLM 5.2 入池：前端 70/后端 65；K3 丞相上线：kimi-native + thinking high + 1M）；Web UI 三连修（选择器分类、「丞相」显示、kimi 网页选模型）。
- **feat · G6/G7**：模型选择器 harness 回退扩展到 codex（G6）；丞相 harness 切换菜单修复——自定义 agent 自身 harness 合入选项、模型选项跟随 pickedHarness（G7）。
- **fix · Codex 模型目录**：静态目录从过时的 gpt-5.5/5.4 纠正为 GPT-5.6 家族（sol/terra/luna），每个模型挂思考强度（minimal→xhigh），create 带 reasoning_effort。
- **score · DeepSeek 默认 → flash**：`~/.claude/settings.json` ANTHROPIC_MODEL=deepseek-v4-flash + 生成器同步；G0d 校准一次过（后端 60）；新身份不继承 Pro 分数（注册表 rev→35）。
- **feat · ClaudeTeam 审批三件套**：`approval_mode = boss|manager|auto` 配置化 + `claudeteam task approval-mode` 显示/切换命令；看板标题显示审批模式、需审批行标等老板/等主管；任务完成自动群发通知卡片。全套 1159 项测试 0 失败。
- **score · GLM 5.2**：前端 70→80（G6/G7 连过，注册表 rev→34）。
- **score · Codex 本轮总结认定**：修bug 75→80（#2853 实现+测试经 controller 复验视同验收）；连续两轮额度尽死于 runner_disconnected，排班须预设接管人；后续 omnigent 修复改派 Kimi+子代理群（注册表 rev→33）。
- **verify · 6 路并行验证**：#2904 本机不可复现（tmux 3.6b）；#2539 单用户不可复现（升级条件=多用户）；#2854 确认可复现；#3003 属实降级 P2；#3004 确认属实（~13k 查询/turn）；#2702 属实（~3.6% 单核/terminal）。
- **fix · #2854**：runner crash-recovery 重放的 kickoff turn 现在正确消费 harness_override（`c7a7073`）。
- **perf · #3003**：policy engine 每次 build 的会话读取 6 次→1 次、全树扫描 2 次→1 次，评估输出逐项比对不变（`b8c2e95`）。
- **perf · #3004**：streamed event POST 加 1.5s TTL ACL/会话缓存，实测 13.0→0.65 SQL/POST（-95%），拒绝路径 fail-closed 不变（`26199b0`）。
- **perf · #2702**：native idle watcher 退避 5Hz→0.2Hz（25×），failed 会话 watcher 不再泄漏（`b6994fd`）。

## 2026-07-27

- **feat · G2-D 闭合（#2967 reactive compaction）**：generic/headless harness 上下文溢出后轮询快照确认空闲→服务端 compact→重载重试一次；/compact 使用 session model_override；262 项测试通过（`0d9c7d1`）。
- **score · G2 长程单元结算**：Codex Agent协同 60→75（规则 8，6 子关 +15 封顶，注册表 rev→29）。
- **feat · Web UI 三连修**：选择器分类修复（自定义 agent 不再消失/撞名，G4）→ controller 显示「丞相」（G4）→ kimi-native 网页选模型（G5/G5b，k3/kimi-for-coding/kimi-for-coding-highspeed，自定义 agent 经 harness 回退同享）。
- **score · GLM 5.2 前端开疆**：G4 校准 60 → G5/G5b 生产关 70（注册表 rev→32）；连续两关撞 hermes 迭代上限需收尾，后续派关缩小单关体量。
- **feat · 阵容可见性（Cast Visibility）**：派发消息必须写 `角色=模型（agent id）`；会话命名 `角色·模型-关卡-简述`；多关任务收尾必出阵容战报表。SKILL.md + 生成器 Controller prompt 同步，线上生效。

## 2026-07-24

- **chore · 提交 07-23 已验证修复**：#3016（session snapshot 可靠性）与 #3012（登录续期）按语义拆分提交入库；提交前复跑相关回归 475 项 + Accounts/OIDC 集成 32 项全部通过，`ruff check omnigent tests` 零错误。
- **note · G2-D 残留未提交**：`server/routes/sessions.py`（/compact 使用 session model_override）、`tests/server/integration/test_sessions_compact.py`、`tests/runner/test_app_sessions_native.py`（reactive compaction 测试）属于 G2-D1/D2 关卡产物，该批关卡以 runner_disconnected 中断、未经终审，暂留工作树，待验证关跑完后再提交。
- **feat · AGENT_LOG 多 Agent 工作日志制度**：新建项目根 `AGENT_LOG.md`（每个 Agent 完成任务后末尾追加一条：做了什么/证据数字/涉及提交/遗留）；agentpeihe SKILL.md 的 Executor/Controller 工作流同步挂载（两仓一致）；全局事实源 `~/.agent-collaboration/agent-log-convention.md`，已挂载 Codex/Claude/Kimi/Grok/Hermes/Workbuddy 六家 CLI 全局配置，QoderWork 需手动粘贴。
- **score · GLM 5.2 入池（关二爷候选）**：经 Hermes + 火山方舟 Agent Plan 坐实身份（`glm-5-2-260617` dated-pin）；G0c 后端校准关一次过 PASS，后端实现 0→60（证据 `20260724-agentcenter-g0c-glm52`）；注册表 rev→26。
- **feat · 长程任务计分（SKILL 规则 8，Boss 批准）**：≥3 关联关卡的长程单元按单元结算——基础 +5 + 每个追加子关 +2、封顶 +15，未闭合记暂记，中途换人按实际子关分别记分，Controller 在 Agent协同 维度同规则结算；G2 长程单元（#3012 的 G2-B1/B2/B3 + G2-D/#2967）已登记暂记，G2-D 验证关保留给 Codex（注册表 rev→27）。
- **feat · 生成器 hermes 嗅探 + GLM 进自动池**：`gen_controller_bundle.py` 解析 hermes 配置自动出 `exec_zhipu`（hermes-native，显示名 hermes-GLM5.2（huoshan），与 pi zhipu 去重）；线上 bundle 重建 + server 重启完成；hermes-native 直发烟测 PASS（GLM 5.2 实答"收到。"）。controller 大脑 codex 额度未恢复，丞相全链路暂不可用。

## 2026-07-23

- **fix · Omnigent 会话可靠性**：修复 #3016 的瞬时 session snapshot 失败会把 worktree 永久回退到 runner 全局目录；恢复连接后会重新读取 session worktree。（07-24 已提交）
- **fix · Omnigent 登录续期**：修复 #3012。Accounts/OIDC 登录可安全轮换续期凭证；host/runner 遇 runtime token 过期或一次 401 时自动续期并仅重试一次，403 仍直接拒绝。续期拒绝后要求重新登录，绝不退回权限更宽的 session JWT；Databricks 流程不变。（07-24 已提交）
- **verify · G2-B3**：客户端相关回归 291 项、续期/权限边界 44 项与 61 项、Accounts/OIDC 集成 32 项均通过；静态检查和独立审查通过。下一关为 #2967 的只读立项审计，尚未授权实现。
- **fix · Ruff 历史遗留清零（Kimi 99 元版 执行）**：修复 HEAD 上遗留的 4 个 ruff 错误——`cli.py` platform-info 超长行拆行、`test_distribution_metadata.py` import 排序 + 超长行拆行、`test_platform_capabilities.py` 超长行拆行；`ruff check omnigent tests` 全部通过，受影响测试 8 项通过。另复核 G2-B3 改动：相关单元测试 382 项 + 集成测试 32 项复跑全部通过。

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
