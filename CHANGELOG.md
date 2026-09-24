# 变更日志（CHANGELOG）

本项目所有值得一提的变化，按日期倒序记录。格式：日期 · 类型（feat/fix/docs/score）· 内容。

---

## 2026-09-24

- **feat · CodeBuddy 入池（exec_codebuddy，vendor=tencent）**：背景是 hermes 连火山 Coding Plan 额度用尽。CodeBuddy CLI（2.157.0）原生支持 ACP（`codebuddy --acp`，stdio ndJson），实测 initialize → session/new（默认模型 hy4-preview-f，x0.00 credits）→ session/prompt 全链路通过；omnigent 通用 acp harness 零代码接入——`~/.omnigent/config.yaml` 的 acp.agents 加 `{name: CodeBuddy, command: "codebuddy --acp"}`（harness id `acp:codebuddy`）。生成器新增 has_codebuddy 检测 + exec_codebuddy 工人块（比照 exec_xai/Grok ACP 写法），通道隔离节加 CodeBuddy 行；`ensure_acp_config` 改按条目幂等补齐。模型跟 CLI 默认（不钉）。另加 `--no-codex` 开关（Boss 裁：codex ChatGPT 登录不进池），压住 exec_openai 工人与 codex 大脑候选。验证：AcpExecutor 直驱 `codebuddy --acp` 实回「派单成功」；`acp_agents()` / `harness_catalog()` 均见 `acp:codebuddy`；`--brain pi --no-codex` 重跑后池 = exec_deepseek / exec_moonshot / exec_xai / exec_codebuddy / exec_zhipu / exec_deepseek_hermes，大脑仍是 pi(deepseek-flash)。
- **ops · GLM 5.2 冷却下架（exec_zhipu 出池）**：火山方舟 Agent Plan 到期不续费，注册表 GLM 5.2 行加 `cooldown-until: 2026-12-31`（恢复时删除重跑即可）；重跑生成器后池不再含 exec_zhipu，bundle 目录同步 purge。controller v30。另实测 CodeBuddy 模型选择机制：session/new 的 model 字段被忽略、session/set_model 支持但 omnigent executor 不调用、`--acp --model <id>` 启动参数钉住生效（exec_codebuddy 如需钉模型改 acp command 即可）。

## 2026-09-11

- **feat · DeepSeek V4.1-Flash 切换（规范名 deepseek-flash，官方 2026-09-10 发布）**：0731 与 vision-exp 官方双双下线（旧名暂时路由 V4.1）——三通道统一切规范名：~/.claude/settings.json 全别名 `deepseek-flash[1M]`、~/.hermes/config.yaml `default: deepseek-flash`、生成器 docstring/pi 备选/通道隔离/pool 注释同步（两仓，prompt 9,091→9,042B）。V4.1 原生视觉 + 原生 1M（输出 384K）、Terminal-Bench 2.1 90.6（vision-exp 83.9）、输入价 2元/百万（高峰）。注册表 rev 40→41：V4.1 新身份继承 vision-exp 后端 60（Boss 钦定留痕，沿 vision-exp 继承 flash 先例），vision-exp / 0731 / hermes 直连三旧身份标 deprecated。重跑生成器 + 带 `--agent` 重启（controller v28，description 2026-09-11）。烟测：Anthropic 端点 `deepseek-flash[1M]` 文本实回「收到」+ 1x1 PNG 实回「粉色」（model 回显无降级）；hermes chat 实答 4。背景：旧纪元会话 09-10 15:15 经 UI 删除（G63 军报前提作废），Boss 改裁「现在就切」；G64 根修向新丞相（K3）重派 + G65 V4.1 校准关立项。

## 2026-09-09

- **feat · DeepSeek 主力默认 → vision-exp（官方 2026-08 更新）**：CC Switch + Claude Code 壳 `~/.claude/settings.json` 主开关与 Haiku/Fable/Sonnet/Opus 别名全部 `deepseek-v4-flash-vision-exp[1M]`（图片输入 + 1M）；pi/OpenAI 直连备选仍为无后缀稳定版 `deepseek-v4-flash`（官方已指向 V4-Flash-0731）。烟测：Anthropic 端点文本 + base64 图片均实回 `deepseek-v4-flash-vision-exp`，无静默降级。PITFALLS 坑 21、部署通道表、WINDOWS_HANDOFF、STEPS_6_8、W16 示例、生成器注释与 Controller prompt 同步（两仓）。
- **feat · hermes 默认模型 → DeepSeek `deepseek-v4-flash`（V4-Flash-0731）**：`~/.hermes/config.yaml` model 块改直连 api.deepseek.com（火山方舟 Agent Plan provider 保留，GLM 5.2 等可 /model 手选）。生成器 exec_zhipu 分支加 GLM 嗅探门——hermes 默认非 GLM 时不再误生成「hermes-GLM5.2」工人，池注释如实标注；`--dry-run` 验证通过。GLM 5.2 自动通道随之退出默认池。
- **ops · 线上池重建 + server 重启**：Boss 确认后正式重跑生成器——删除 exec_zhipu，重写 exec_deepseek/exec_moonshot/exec_xai/controller；`omnigent-zh server stop` 后按原进程参数重启（127.0.0.1:6767）。`/v1/agents` 确认 controller v23 注册、新 prompt 含 vision-exp 规则；runner/host 自动重连，5 个在跑会话全部 reattach。
- **score · 注册表 rev 36→37**：vision-exp 登记为 exec_deepseek 默认身份（Candidate），**Boss 钦定继承** Flash 修改前的后端 60 分（覆盖「新身份不继承」默认规则，备注留痕）；旧 Flash 身份转 pi 直连备选备查；GLM 5.2 路由改 hermes `/model` 手选。
- **fix · 误报结案**：omnigent hermes_executor 的 `--source tool` 与 hermes v0.19.0 实际兼容（该参数属 `chat` 子命令），实测 `hermes chat -q … -Q --source tool` 正常应答并回 session_id；executor 与回归测试均不改。
- **feat · DeepSeek 第二通道入池（exec_deepseek_hermes）**：生成器新增分支——嗅探到 hermes 默认模型为 DeepSeek 时自动生成 `exec_deepseek_hermes`（hermes-native 直连 api.deepseek.com，model=deepseek-v4-flash 即 V4-Flash-0731，显示名 hermes-DeepSeekFlash（直连）），与壳 exec_deepseek（vision-exp）异构并存；头部注释/Controller prompt/部署通道表同步（两仓）。注册表 rev 37→38 登记新身份（Candidate，未校准，不继承——继承钦定仅限 vision-exp）。
- **fix · server 重启须带 `--agent` 才重新注册 bundle（PITFALLS 坑 33）**：裸参数重启只保会话不注册——`/v1/agents` 的 controller 停在 v23/2026-08-20；按生成器提示带 `--agent …/agents/controller` 重启后 v24、description 日期 2026-09-09 生效。exec_deepseek_hermes 直发烟测实回「收到」。
- **feat · Grok 4.5 → 4.6 上线**：xAI 官方文档确认 Grok 4.6 为当前旗舰（coding 推荐）。本机 grok CLI v1.0.24 的 `~/.grok/config.toml` models.default 已是 `grok-4.6`（stable auto_update 已跟进），`exec_xai`（acp:grok-build = `grok agent stdio`，模型取 CLI 默认）壳侧零改动完成升级；exec_xai 直发烟测实回「收到」，grok 会话记录 `current_model_id=grok-4.6` / `primaryModelId=grok-4.6-build` 坐实。生成器 PI_PROVIDERS pi 备选 `grok-4.6`、omnigent onboarding 兜底 pin `grok-3→grok-4.6`、部署文档 provider 示例同步（两仓 ×2）。注册表 rev 38→39：Grok 行填实身份（floating-alias 延续，分数不动，Direct route 改 available(exec_xai)）。丞相派单通道不变（exec_xai 一直在池）。
- **feat · GLM 5.2 恢复丞相可自动派活（exec_zhipu 回池）**：omnigent 服务端 `_derive_terminal_launch_args_from_spec` 新增 hermes-native 映射——worker 的 `executor.model` + `config.provider` → hermes TUI 启动参数 `-m/--provider`（两仓，`test_sessions_yolo_launch_args` 17 绿）；生成器改嗅探方舟 plan 块默认模型（`providers.volcengine-agent-plan.model`）生成 exec_zhipu，工人 YAML 钉住 model+provider，不再随 hermes 全局默认漂移。全链路实证：带 parent 的子代理派发 → `terminal_launch_args` 正确落库 → hermes 窗格页脚 `glm-5-2-260617 │ 1M` → 实答「收到」。注册表 rev 39→40（GLM 路由恢复）。注意：无 `parent_session_id` 的手工子代理创建不继承 runner，会报 `runner_failed_to_start`。
- **fix · controller prompt 撞 tmux 16KB 硬顶（坑 34/35）→ A 治标落地 + B 根修立项（G64）**：claude-native 子会话终端 `--append-system-prompt` 注入的是 controller 完整 prompt（runner/app.py:5909 按 session.agent_id 解 spec，子会话 agent_id=parent 的 controller）——prompt 随模型池备注涨至 10,718B，启动命令包 ≈16.9KB 超本机 tmux 16KB imsg 硬顶（实测 16,000 过 / 16,384 拒），09-08 晚起 192 次 `command too long`，关二爷·DeepSeek 派发全挂（native_terminal_start_failed）。A（Boss 裁决 A+B）：生成器 9 处修剪（模型池备注去重 + 通道隔离/角色表/编译器/会话池/compact/执行原则/立项关冗词压缩，规则逐条保留）→ 9,091B；重跑 + 带 `--agent` 重启（controller v27）；tombstone 旧会话 conv_dc43eb01（105K tokens 不可恢复）→ 丞相按 G61 先例同名重派 G63——新会话 conv_ea740ec0 status=running、ctx 69K、零新增 command too long（vision-exp 首个正式关开跑）。B：G64 根修立项（子会话改注入子 agent 自己 spec prompt；无 spec 且 >12KB 降级 WARN 不硬失败，两仓 + pre-commit + 活体复派验证）已派丞相排期（G63 军报先行）。坑 34（子代理 runner 一次绑定终身 → 重启后旧子会话 runner_failed_to_start；close 跨注册时代盲区）、坑 35 录入 PITFALLS（两仓）。
- **docs · 部署文档新增 §4.7 日常操作卡**：UI 主路（找丞相，固定主会话）/ 异常三读数鉴别（status、error code、runner 日志）/ 复位=close+同名重派 / 变更后三条纪律（带 `--agent` 重启、盯 `command too long`、prompt ≤12KB 预算）/ API 应急注入信封（`data` 包裹 + content 必须 list）+ §4.3 prompt 尺寸预算条、附录 A 踩坑表第 8 行。

## 2026-08-21

- **fix · kimi 0.37.2 TUI 适配（坑 32，omnigent 仓）**：多行粘贴被 0.37.2 折叠成 `[paste #N +M lines]` 占位符 → 草稿检测改认占位符；信任页改方向键菜单（默认 Don't trust、Esc=退出 TUI）→ `_settle_pane` 改读 `❯` 选中行 Up 导航 + Enter，绝不发 Esc。回归 6 项、executor 64 项 + kimi 全套 143 项绿，tests/inner 1752 过、tests/runner 1192 过（残留失败均 macOS 既有环境问题，干净树复现）；活体：/tmp 全新目录 46 行粘贴一次投递成功回 "OK"，Boss 真实会话重发链路确认恢复。

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
