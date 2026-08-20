# 踩坑实录：omnigent + agentpeihe 部署

> 每条按「坑 → 为什么遇到 → 怎么解决 → 同类问题怎么避免」组织。
> 全部来自 2026-07-21/22 第一期真实部署，已在生产环境实锤，不是推测。
> 目标：后来者在全新机器上照文档走，不再踩这些坑。

---

## 一、Agent 注册与显示

### 坑 1：`~/.omnigent/agents/*.yaml` 放了 agent，Web UI 里却找不到

- **为什么遇到**：agents 目录只被 CLI `omnigent-zh run <file>` 直接读取；Web UI 的智能体列表走的是 **server 注册表**，文件落盘 ≠ 注册。
- **怎么解决**：前台模式带 `--agent` 参数注入：`omnigent-zh server --no-open --agent ~/.omnigent/agents/controller`。注意 `server start`（后台模式）**不支持** `--agent`。
- **同类避免**：**改了 bundle 里任何一个字，都要重启 server 重新注册**——server 手里拿的是启动时的快照，改完不重启，跑的还是旧配置（我们为此白跑了一整轮验收）。

### 坑 2：自定义 agent 在 Web UI 里显示成第二个 "Claude Code"，找不到名字

- **为什么遇到**：Web UI 把 agent 按 **harness** 归类——harness 是 native 系（claude-native/codex-native/kimi-native…）的一律进"执行器"区，显示 harness 品牌名，不显示你的 agent 名。
- **怎么解决**：自定义编排 agent（如 Controller）的大脑必须用**非 native harness**（`claude-sdk` / `codex` / `pi`），才能以本名出现在"智能体"区。
- **同类避免**：设计角色时就想清楚——**大脑（编排者）用 SDK 形态，工人（执行者）用 native 形态**。

### 坑 3：派发后子 agent 的干活过程在主聊天区"消失"

- **为什么遇到**：这是产品设计，不是故障——主聊天流只显示 Controller（老板视图），子 agent 是独立子会话。
- **怎么解决**：右侧"智能体"面板的**子代理图谱**（SubagentsGraphView）里有点名可点的节点，点进去看完整现场；native 工人还有可旁观的 tmux 终端。
- **同类避免**：Controller 派发时的会话名必须用**中文角色名**，别用英文 slug——这条已写进 controller prompt 模板和生成器。（2026-08 起命名规则改为稳定名 `<角色中文名>·<模型名>`、无关卡号，工具参数真名是 `title` 不是 `session_name`，见坑 27。）

---

## 二、子 agent 权限与审批（headless 死锁三连）

### 坑 4：claude-native 子 agent 卡住不动，像死机

- **为什么遇到**：Claude Code 默认权限模式会弹"是否允许写文件/执行命令"确认框，headless 子 agent 没有人替它点，永远等下去。表面看像"卡死"而非"失败"，最难排查。
- **怎么解决**：子 agent bundle 里配 `executor.config.permission_mode: auto`（polly 官方工人同款；managed settings 下 `bypassPermissions` 可能被禁，`auto` 是允许的最强档）。
- **同类避免**：**任何 native CLI 进自动化池之前，先确认它的审批模式能 headless 免确认**（codex 用 `yolo: true`）。

### 坑 5：kimi-native 子 agent 卡死（已解：omnigent 默认带 `--yolo`）

- **为什么遇到**：Kimi CLI 的 TUI 审批提示 omnigent 拦不了，headless 子 agent 没人点确认 → 死等。第一期据此判了 kimi-native"无解"。
- **怎么解决（2026-07-22 更正）**：omnigent 启动 kimi-native **默认带 `--yolo`**（源码 `_DEFAULT_KIMI_LAUNCH_ARGS`），审批自动放行——kimi-native 可以进自动化池，自动派活和手工（网页/`omnigent-zh kimi`）两条路径都烟测通过。**正确的隔离规则是：Kimi 只走 kimi-native，禁止经 CC Switch 套 claude 壳**（后者会造成"名 Claude 实 Kimi"的通道混乱）。注意 Host 的 PATH 须含 `~/.kimi-code/bin`。
- **同类避免**：判"无解"前先查 harness 的默认启动参数；native CLI 的审批问题有两类解——配置免确认（permission_mode/yolo）或换 headless 形态。另外手工 `omnigent-zh run -r` 续 kimi 会话在无 TTY 时会报 `open terminal failed: not a terminal`，那是姿势问题不是 kimi 挂了（用网页或 tmux 注入）。

### 坑 6：kimi harness 当 Controller 时"伪造"派发记录

- **为什么遇到**：omnigent 的 kimi（headless）harness **没有工具注入桥**（"no tool-injection bridge for the upstream kimi binary"），Controller 根本看不到 agent 工具，只能按协议"演"一遍——包括编造不存在的 vendor 标签。
- **怎么解决**：Controller 大脑只用工具桥完整的 harness（claude-sdk / codex / pi）。
- **同类避免**：验收多 agent 链路时，**不信叙事信证据**——查 runner 日志里的真实 spawn 记录和子会话，别信模型的"我已派发"。

---

## 三、pi harness（API 模型通道）

### 坑 7：pi 子 agent 报 "No API key found for the selected model"

- **为什么遇到**：两层叠加。
  1. `model` 写在了 `executor.config` 里——那是**不透明兼容层**，spawn 链路只读**顶层** `executor.model`（parser.py 实锤），`config.model` 静默忽略；
  2. 没有 `executor.auth` 显式绑定 provider，pi 不会自动兜底"第一个可用 provider"。
- **怎么解决**：
  ```yaml
  executor:
    type: omnigent
    model: deepseek-v4-pro        # 顶层，不是 config.model
    auth:
      type: provider
      name: deepseek              # ~/.omnigent/config.yaml 里的 provider 名
    config:
      harness: pi
  ```
- **同类避免**：**配置"写了不生效"类问题，先查 parser/schema 再查 runtime**——别学我们先去查 env 白名单和进程，绕了三圈。

### 坑 8：YAML 修好后 runner 报 "provider 'deepseek' configures no family whose credentials resolve"

- **为什么遇到**：host 守护进程 spawn runner 时只转发凭证白名单（`HARNESS_CREDENTIAL_ENV_VARS`：OPENAI/ANTHROPIC/GEMINI 等，**没有 DEEPSEEK_API_KEY**），runner 进程展开 `$DEEPSEEK_API_KEY` 失败。
- **怎么解决**：`export OMNIGENT_RUNNER_ENV_PASSTHROUGH=DEEPSEEK_API_KEY`，重启 **host daemon + server**（只重启 server 不够）。已写进本仓库快速启动。
- **同类避免**：`env_passthrough`（进子进程的白名单）和 runner 凭证转发是**两套机制**，gateway 路径的 key 走 models.json（AUTH_COMMAND 烘入），与 env 透传无关。新增 API provider 时三个地方都要想到：config.yaml、runner passthrough、子 agent auth 绑定。

### 坑 11：codex-native 子 agent 报 "Codex app-server never started a thread" 启动超时

- **为什么遇到**：codex-native 形态要在 tmux 里拉起 codex app-server 并等它建会话线程， omnigent 自己的代码注释就写了这条失败链——TUI 可能停在首次运行引导页，无人点确认，30 秒超时。单机 `codex exec` 却完全正常，极具迷惑性。
- **怎么解决**：工人别用 `codex-native`（TUI 形态），用 **`harness: codex`（headless exec 形态）**——`codex exec` 通道不经过 app-server 线程，debby 官方示例同款，一次通过。
- **同类避免**：**每个 native CLI 都有"TUI 形态"和"headless 形态"两个 harness**（claude-native/claude-sdk、codex-native/codex、kimi-native/kimi、pi-native/pi）。自动化池的工人优先 headless 形态；TUI 形态只在你确定它的审批/引导能在无人值守下通过时才用。

---

## 四、模型身份与代理（国区特供坑）

### 坑 9：以为在调 Claude，其实在调 DeepSeek/Kimi

- **为什么遇到**：CC Switch 会把 `claude` CLI 的后端切到任何 OpenAI 兼容端点（`~/.claude/settings.json` 的 `ANTHROPIC_BASE_URL`）——CLI 名字和实际 vendor 脱钩。按 CLI 名字做"Reviewer ≠ Executor vendor"校验会全错。
- **怎么解决**：vendor 一律按**实际后端**判定（读 settings.json 的 BASE_URL 嗅探，`gen_controller_bundle.py` 已内置），模型池表里标注"实际 vendor"。
- **同类避免**：订阅 key（SuperGrok、Kimi coding 的 `sk-kimi-`）≠ 平台 API key——订阅只配官方客户端用。有官方 CLI 的走 native harness（不要 key）；没有的才需要 platform API key（gateway）。

### 坑 10：国内外 API 混用，代理一刀切全断

- **为什么遇到**：omnigent 的 provider 没有代理字段，全局 `HTTPS_PROXY` 会让国内 API（deepseek/moonshot）也绕代理，慢甚至断。
- **怎么解决**：`HTTPS_PROXY=http://127.0.0.1:<port>` + `NO_PROXY=api.deepseek.com,api.moonshot.cn,localhost,127.0.0.1`，国外走代理、国内直连。代理变量加"端口活着才生效"的条件式 export，防止代理软件一关全机断网。
- **同类避免**：WSL2 里 `127.0.0.1` 不是 Windows 的 `127.0.0.1`——mirrored 网络模式或用宿主机 IP，详见部署文档第二步。

### 坑 12：飞书卡片按钮写了 `{tag:"action"}`，schema V2 直接拒收

- **为什么遇到**：卡片 v1 文档里按钮是 `{tag:"action", actions:[...]}` 包装，照搬到 v2（`schema: "2.0"`）后 message API 报 `cards of schema V2 no longer support this cap`（ErrCode 200861，路径 `body -> elements -> [i](tag: action)`）；`action_set`/`form` 也不支持。回复静默 400，看板像死了一样。
- **怎么解决**：schema V2 的按钮**直放** `body.elements`（`{"tag":"button","text":{...},"type":"primary","value":{...}}`），不要任何包装。拿不准就用最小卡片在真实 API 上二分试：纯 markdown 通过 → 加包装被拒 → 直放通过。
- **同类避免**：卡片回调 `card.action.trigger` 在控制台「**回调配置**」页，不在「事件订阅」页——查订阅状态时两页都要看（我们就曾只查事件页，误判"未订阅"去白做一轮重注册）。

### 坑 13：守护进程带着 proxy 环境跑，飞书请求被 TLS 劫杀

- **为什么遇到**：macOS 全局 `HTTPS_PROXY=127.0.0.1:1082` 且 `NO_PROXY` 不含 `open.feishu.cn` 时，ClaudeTeam router/sidecar（axios/node 也吃 proxy env）把飞书 API 请求送进 Clash，上游抖动时 `Client network socket disconnected before secure TLS connection was established`——发送失败 → 重试耗尽 → router 崩溃循环 → watchdog 进 600s 冷却，整套系统死亡且难以察觉（我们的一套死了 29 天才发现）。
- **怎么解决**：守护进程用**净环境**启动（`env -u HTTP_PROXY -u HTTPS_PROXY`），或给 `NO_PROXY` 加 `open.feishu.cn,.feishu.cn`。健康检查 `claudeteam health` 会把"HTTPS_PROXY 无 LARK_CLI_NO_PROXY=1"标成警告——看到就处理，别跳。
- **同类避免**：omnigent runner 曾中同款（httpx trust_env 读 macOS 系统代理，loopback mint 被劫 503，见 `efe8209`）——**凡是用 httpx/axios 的本地守护进程，loopback 和国内 API 都要显式绕代理**，不能指望环境干净。

### 坑 14：native harness 的 turn 级 instructions 全被 del，角色 prompt"发了但没到"

- **为什么遇到**：所有 `*_native_executor` 的 `run_turn` 都 `del tools, system_prompt, config`（kimi_native_executor.py:85、hermes_native_executor.py:82 等），runner 侧 kimi/hermes 的终端创建函数还曾 `del agent_spec`。现象极具迷惑性：runner 日志 `GET /agent/contents 200 OK`、spec 明明取到了，但 kimi TUI 拿的是原厂 system prompt——"丞相"零命中，模型把"关二爷"当成自己的昵称亲自下场干活。
- **怎么解决**：turn 级通道已死，**launch 级投递才是活路**，且每个 CLI 的原生通道不同：kimi = 会话级 `$KIMI_CODE_HOME/AGENTS.md`（读全局合并、解 symlink 写实文件）；claude = `--append-system-prompt`；grok = `--agent-profile <file>.md`（frontmatter 必填 name+description，body append 进默认 system prompt）；hermes = per-session `HERMES_HOME/SOUL.md`（主 identity 槽，只从 HERMES_HOME 读）。2026-08-04 全部接通（agentcenter `ab43288`/`deef41a`）。
- **同类避免**：审计一条 harness 通道时 launch 路径和 turn 路径都要查——turn 路径的 `del` 是静默丢弃，日志零报错。共享 helper 的隐式契约同理（`post_external_session_status` 用相对 URL，httpx client 必须带 `base_url`——docstring 没写，kimi idle poster 曾因此永远 POST 失败刷警告）。

### 坑 15：父子 kimi 会话同 workdir，forwarder 按 mtime 必锁错 wire

- **为什么遇到**：kimi 会话 home 的 `sessions` 目录是全局 symlink，父子两个 kimi 进程（丞相 + exec_moonshot 工人）同 workdir 时互相可见全部 wire。`_discover_wire` 按「同 workspace + mtime 最新」选——工人 forwarder 启动时丞相的 wire 刚跑完 turn、mtime 最新，于是工人会话镜像了丞相的消息，自己的执行内容全丢，丞相也等不到唤醒。
- **怎么解决**：加创建时间维度——`state.json` 的 `createdAt ≥ launch−skew` 的候选里取离 launch 最近的（nearest-after-launch）；`state.json` 缺失/损坏才降级 mtime 逻辑。2026-08-04 修复（agentcenter `597fe5c`）。
- **同类避免**：在共享存储上认领"我的资源"时，mtime 是最差判据（活跃资源的 mtime 永远在动）；创建时间 + 我的启动时刻就近匹配才对。symlink 共享一时爽，发现逻辑必须假设命名空间是混的。

### 坑 16：kimi 没有 turn 完成上报，子代理干完活父会话永远不醒

- **为什么遇到**：omnigent 的「子完成 → 父 inbox → 唤醒」链需要一个生产者 POST `external_session_status: idle`——claude 有 Stop hook、hermes 有 status poster、cursor 有 usage 上报，**kimi 什么都没有**（`KimiNativeExecutor.run_turn` 注入消息即 `TurnComplete`，那只是"粘贴成功"，不等于 kimi turn 真结束）。丞相派完关二爷就永远停在"待回报"，而工人其实早就干完了。
- **怎么解决**：新增 `kimi_native_status` idle poster——forwarder 从 wire 推导终态（`step.end` 且其区间内无 `tool.call`；新 `turn.prompt` 关闭悬置 turn 兜底），镜像追平后 POST idle，`posted-count` 落盘幂等。2026-08-04 修复（agentcenter `597fe5c`）。
- **同类避免**：接一条新 harness 时，"消息能进"不等于"事件能出"——turn 完成、审批、错误三类回程事件要逐个点名，缺一个就是断头路。

### 坑 17：丞相网页改 Codex，终端仍是 Kimi + 模型 id 被塞进错误 CLI（2026-08-10 已修）

- **为什么遇到**：G6/G7 让**模型列表**跟随 effective harness（`pickedHarness`），但 `POST /v1/sessions` 的 `labels`（`omnigent.ui` / `omnigent.wrapper`）仍按 **agent 默认 harness**（controller 默认 `kimi-native`）调用 `nativeWrapperLabelsForAgent`。结果：`harness_override=codex`、`model_override=gpt-5.6-terra` 已进会话，但 labels 仍是 `kimi-native-ui` → UI/ensure 路径起 Kimi TUI → Kimi 用 `-m gpt-5.6-terra` → 红字 `Model "gpt-5.6-terra" is not configured in config.toml`。侧栏标题也像「Kimi」。
- **怎么解决**：`handleCreate` 写 labels 与能力 knobs 时与 model_override 同源——一律用 effective harness（`pickedHarness ?? agent.harness`）。覆盖成非 native 的 `codex` 时不再 stamp kimi wrapper，runner 走 Omnigent REPL（`omnigent attach`）。默认不覆盖时仍 stamp kimi-native-ui。前端 flow 测试覆盖两种路径。
- **同类避免 / 产品语义**：
  1. 创建会话 body 里 **harness_override、model_override、labels、terminal_launch_args 必须同一套 effective harness**，任何一处只读 agent 默认都会串台。
  2. 菜单「Codex」对丞相 = 大脑 harness **`codex`（headless/SDK）** → 人机界面是 **Omnigent REPL**（首启可选 dark/light 主题，正常）；**不是** 真·Codex TUI。
  3. 真·Codex 交互终端 = 执行器预设 **`codex-native-ui`**（`codex-native`），与「丞相换大脑」不是同一入口。
  4. 丞相默认 Kimi 走 `kimi-native` TUI，是因为默认 harness 是 **native**；不是「Kimi 特殊、Codex 被降级」。

### 坑 18：Host 连 8000、Server 在 6767 → `runner_disconnected` / Host offline（2026-08-10）

- **为什么遇到**：
  1. **产品默认端口已是 6767**（`omnigent-zh server`、部署文档、AgentCenter README），但 **`~/.omnigent/config.yaml` 的 `server:` 可能仍写着旧值 `http://localhost:8000`**（早期 setup / FastAPI 习惯 / 部分 Electron·SDK 示例）。`omnigent-zh host` **默认读 config**，不自动对齐当前 UI 端口。
  2. Server 只负责 Web/API；**真正起 runner 的是 Host**。只开 server、Host 连错地址或 Host 进程被关/睡眠杀死 → UI 报 **`Runner disconnected unexpectedly`**，会话 `failed`，Host **offline**。
  3. Runner 日志末尾常见 `httpx.ReadError` / `turn cancelled` / `get_client called before start()`——多是 **断线连带**，根因在 Host/Server 链路，不一定是关卡业务代码。
- **怎么解决**：
  1. `~/.omnigent/config.yaml` 设 `server: http://127.0.0.1:6767`（与真实监听端口一致）。
  2. 两进程：`omnigent-zh server --no-open --agent ~/.omnigent/agents/controller`（已在跑可 reuse）+ **常驻** `omnigent-zh host`（或 `omnigent-zh host --server http://127.0.0.1:6767`）。
  3. 自检：`curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:6767` 与 `grep '^server:' ~/.omnigent/config.yaml` 端口一致；`omnigent-zh host status` 看 host/session。
  4. 可选本机脚本（非仓库必装）：`~/.local/bin/omni-up`（必要时起 server 再前台挂 host）、`omni-check`（config + HTTP + host 进程）。
- **同类避免**：改 Server 端口必须 **同时改 config.server**（或 host 显式 `--server`）；Host 终端勿随手关；睡眠后重开 host。侧栏「不活动」子 agent 多为图谱/DB 记录——**无 OS 僵尸进程时不必为内存狂清**；要腾资源则停止/归档父会话。失败父会话建议 **新开** 任务，勿在断链树上硬续。

### 坑 22：kimi tip/Welcome 与 footer 同屏时粘贴丢（2026-08-11 已修；Escape 范围见坑 24）

- **现象**：红字「未接收粘贴」；终端末尾有 `Use Kimi K3…` tip 框 + 可能已有 `context:`，工作区零改动。
- **根因**：只等 `context:` 就 paste，tip 仍占焦点；`C-a/C-k` 清草稿对 kimi 无效。
- **怎么解决**：就绪须 `context:` + 输入框（行首 `>` **或** K3 盒线 `│ >`）；**只有** tip/trust/sign-in 才 Escape，**禁止**对 Welcome 连打 Escape（会刷坑 24 红字）；空输入框不清 Backspace。短单行 paste 失败回退 `send-keys -l`。见 `kimi_native_bridge`。**新开会话** 加载。

### 坑 21：DeepSeek 壳模型 id 无 `[1M]` → 状态栏只显示 200k Ctx（2026-08-10）

- **现象**：`Model: deepseek-v4-flash/...` 且 `200k Ctx`，尽管 Haiku/Fable 别名已是 `deepseek-v4-flash[1M]`，老板认为模型支持 1M。
- **根因**：Claude Code / CC Switch 对 Anthropic 兼容壳用 **模型 id 后缀**区分上下文档。主开关 `ANTHROPIC_MODEL` 若只写 `deepseek-v4-flash`（无 `[1M]`），TUI 按 **200k** 窗显示；`ANTHROPIC_DEFAULT_*_MODEL` 里的 `[1M]` 只作用于对应别名，**覆盖不了**当前 `ANTHROPIC_MODEL`。
- **怎么解决**：`~/.claude/settings.json` 设  
  `ANTHROPIC_MODEL=deepseek-v4-flash[1M]`（默认 flash + 1M）。pro 用 `deepseek-v4-pro[1M]`。改后须 **新开** claude-native / `exec_deepseek` 会话（旧进程不重读 settings）。
- **注意**：pi / OpenAI 兼容 `api.deepseek.com/v1` 的 model id **不要**乱加 `[1M]`（与壳 id 约定不同）。通道仍是 DeepSeek 主路径 = Claude 壳，不是 pi。
- **验证**：新工人 TUI 底部 Ctx 为 **1M/1000k** 量级，而非 `200k Ctx`。

### 坑 20：native 工人冷启动注入假成功，子会话空转（2026-08-10 已修多 harness 闭环）

- **为什么遇到**：多数 `*_native_executor.run_turn` 在 inject 后即 `TurnComplete`。旧逻辑就绪 soft fall-through / blind Enter，paste 打进尚未就绪 TUI，父会话以为已派完，侧栏工人空白。
- **怎么解决（问题 1）**：各 harness 交付闭环 + 中文红字——`kimi`/`claude`/`cursor`：硬就绪 + 粘贴可见 + Enter 重试；`hermes`：粘贴可见 + state.db 确认 + 最多整包重投 1 次（禁双 Enter）；`goose`：硬 settle + 粘贴可见 + **仅一次** Enter；`acp`（Grok）：超时/进程/启动失败中文。空消息统一中文。
- **未做（问题 2）**：同 vendor 多路（如 20 个 kimi）引擎级 `max_inflight` 闸——遇限流再开。
- **同类避免**：「粘贴成功 ≠ 模型已开跑」；失败必须红字中文；改引擎后 **重启 host/runner**。

### 坑 19：kimi-native 在 model catalog 呈 `provider kind=none`（2026-08-10 已修 catalog 读数）

- **现象**：本机 Kimi CLI / OAuth / `kimi-code/k3` 正常，编排预检或 `sys_list_models` 仍把 `kimi-native` 工人解成 **`kind=none`**，note 含 **`dispatches to this worker cannot run here`**，导致 Controller 不敢派 `exec_moonshot`。
- **根因（G0A）**：`_HARNESS_FAMILY` 故意不含 kimi（无 per-spawn provider 注入）；legacy 无 kimi 分支 → `no model provider configured`。**spawn 并不依赖 catalog**（无 `args.model` 走 CLI `default_model`；kind=none 对 model override 透传）——是 **读数/文案误杀**，不是死 worker。真配置家目录是 **`~/.kimi-code`**，不是 `~/.kimi`。
- **怎么解决（G0B，agentcenter monorepo）**：`model_catalog` 对 `harness_type==kimi`：PATH 有 `kimi` → `kind=subscription` + `cli=kimi` + 静态列表（`kimi-code/k3` 等正确前缀）；无 CLI → none 且 note 说明装 Kimi Code / `~/.kimi-code`，**不再**用「cannot run here」口号。测试见 `test_kimi_native_*`。
- **生效**：改的是 Python 包；**需重启 runner（及必要时 server）** 才加载新 catalog。知识库任务侧改文件不会进 monorepo 记录。
- **仍非目标**：软链 `~/.kimi`；在业务仓修引擎；canary 资格自动写 registry。

### 坑 23：法正 GLM 跑完丞相收不到军报 + Kimi `/login` 死刷 + Hermes `^A^K`（2026-08-14 已修）

- **现象**：子会话 idle 且已有 PASS 军报，父会话停在「已派出，等回报」；Hermes 日志刷 `external_session_usage` 400；Kimi 工人/父会话反复出现 `No active session` / `/login`；Hermes 草稿里出现字面量 `^A^K`。
- **根因**：① usage POST 只带 `model`，服务端要求 token/window → 400 且每 0.4s 重试。② 新版 Hermes `state.db` 可能无 `sessions` 表，discovery 失败 → 永不 mirror、永不 `idle`、父 inbox 不醒。③ 父 TUI 等工人时被 1800s pane reaper 收割，wake 注入无处落。④ 见坑 24（TUI `/login` ≠ `kimi login` CLI）。⑤ Hermes 清草稿用了 readline `C-a/C-k`，TUI 当普通字符吃进去。
- **怎么解决**：usage 改 `external_model_change`；无 `sessions` 表从 `messages` 发现；父有未完成工人时不 reap；Hermes 改 End+Backspace。Kimi 冷启动见坑 24。**重启 host/runner**。
- **同类避免**：父 inbox 唤醒看子会话 `external_session_status: idle`，不要只看嵌入 TUI。

### 坑 24：Kimi Welcome 上的 `/login` 不是 OAuth 掉了（2026-08-18/19 再修）

- **现象**：① 新 kimi-native pane 欢迎栏已有或空着 `Session:`、OAuth 已登录，仍刷几十行 `Error: No active session. Send /login to login.`。② 修完 Escape 后网页「继续任务」无反应，会话 `failed`，红字「输入框未就绪」。
- **根因**：两套「登录」+ 按键误伤 + 盒线漏检。`kimi login` CLI = OAuth；TUI `/login` = 进程内 chat session。K3 冷启动固定打「No session yet，第一条消息才建 session」。Welcome 会一直留在滚动区，当成模态后每 0.8s Escape ≈ 38 行红字。禁止 Escape 之后若只认行首 `>`，会漏掉 K3 盒线 `│ >`（`conv_8e588d8e`），静等超时。连打 Enter、再注入 `/login` 是另两条已修路径（353471d / 503f83d）。
- **怎么解决（引擎）**：Welcome **不是** overlay；禁止对它 Escape / `/login` / 空 Enter；静等 `context:` +（行首 `>` 或盒线 `│ >`）再贴**第一条真用户消息**；只有 tip/trust/sign-in 才 Escape；空输入框不清 Backspace。已刷过的 pane 历史红字清不掉，**必须新开会话**。真设备码授权才要浏览器。提交 `a5c8858` + `711c0ee`。
- **人怎么判断**：CLI 已 Logged in → **不要**再跑 `kimi login`。Welcome 那两行、空着的 `Session:` 都可以留着。网页无反应先看 `last_task_error`，不要先当没登录。
- **同类避免**：iTerm 能开 ≠ 嵌入 TUI 已有 chat session；斜杠 `/login` ≠ shell `kimi login`；欢迎框 `Session:` 有 id ≠ 已经有一条可对话的 chat session。

### 坑 25：Hermes 把长粘贴收成 `[Pasted text #N]` 被当成没贴进去（2026-08-18 已修引擎，待提交）

- **现象**：法正 hermes-native 首条长关卡红字「未接收粘贴」；网页 `failed`。嵌入终端底部其实是 `❯ [Pasted text #3: 37 lines → …/paste_3_….txt]`。
- **根因**：Hermes 0.19 把多行 bracketed paste 收成 chip，原文末行不在 pane 里。引擎只搜 needle，不按 Enter。`conv_949c2666` G20 现场：三次 paste 文件都在，chip 已在输入框。
- **怎么解决（引擎）**：composer 尾部出现 `[Pasted text #` 视为粘贴已提交，再 Enter。≥4000 字仍走 `omnigent_injected_task.md` 短指针。`test_hermes_native_bridge` 39 绿。现场已补按 Enter，TUI 进入 `Initializing agent…`；**网页 failed 与 TUI 是否在跑不是一回事**。G20 是否交卷 / 丞相是否收到 **未在本文档关闭**。
- **同类避免**：红字「未接收粘贴」先看输入框有没有 paste chip，不要立刻重派把 FIFO 再打乱。

---

## 五、工程习惯（本次最大的两条元教训）

1. **先查 schema，再查 runtime。** 配置不生效时，parser 的字段定义是一手证据，运行时日志是二手。三层故障里有两层（model 层级、credential 白名单）都是"先读定义五分钟，胜过猜日志三小时"。
2. **配置生成化，不手改。** 换模型/换大脑/换机器 = 重跑 `gen_controller_bundle.py`（环境检测 + CC Switch 嗅探 + 注册表 cooldown 全部自动），手改 YAML 是技术债的源头。本仓库的快速启动就是用生成器，而不是给你一份静态 YAML。

---

## 六、源码副本与会话派发语义

### 坑 26：工作区里有两个 omnigent-zh-cn 副本且严重分叉，改/读代码找错目录

- **为什么遇到**：本机同时存在顶层 `/Users/shankluo/AI/agentcenter/omnigent-zh-cn`（fork remote，HEAD `8159424`，停在 2026-07-19，**缺坑 14/15/16 的 launch 级修复**）和嵌套 `/Users/shankluo/AI/agentcenter/agentcenter/omnigent-zh-cn`（agentcenter monorepo，活跃）。两个目录同名，凭工作区表象或旧交接文档打开顶层副本，对照"源码"排查会看到修复"不存在"、行号全对不上。而生产 server 实际从**嵌套副本**经 uv tool 安装——`~/.local/share/uv/tools/omnigent-zh-cn/uv-receipt.toml` 实锤：`directory = ".../agentcenter/agentcenter/omnigent-zh-cn"`。已废弃副本的 README 顶部已加冻结警示。
- **怎么解决**：改核心一律改**嵌套副本**；改完 `uv tool install --reinstall` 重装 + 重启 server/host 才生效（重启快照逻辑同坑 1/坑 18）。读代码、引行号（如 `_find_existing_child_session`）同样以嵌套副本为准。
- **同类避免**：「源码在哪」一律查安装凭证——`uv-receipt.toml` 的 `directory` 或 `pip show <pkg>` 的 Location，别信工作区目录表象；任务交接文档里的路径会过时，接手先核对再动手。

### 坑 27：以为 `sys_session_send` 每发必新建会话，按 `session_name` 找参数还找不到

- **为什么遇到**：bundle 和业务文档一直把会话名参数叫 `session_name`，但工具 schema 的真名是 **`title`**（`omnigent/tools/builtins/spawn.py`，`_build_sys_session_send_schema`）——按 session_name 搜 schema 一无所获。更隐蔽的是语义：工具是 **create-or-continue**，同一 `(agent, title)` 再发不新建，而是自动续跑旧子会话（带完整历史）——schema 描述原文「Lets later turns reuse the same conversation via another sys_session_send call with the same title」；查找逻辑在 `omnigent/runner/tool_dispatch.py` 的 `_find_existing_child_session` / `_send_to_existing_session`。当"每发必新建"用，契约和规则被重复投喂，输入 token 翻倍还不自知。
- **怎么解决**：
  1. 会话命名改**稳定名** `<角色中文名>·<模型名>`（去掉旧规则的关卡号和简述），同角色同模型全程同名——会话池（Sticky Executor）正是利用 create-or-continue 复用上下文，续关只发 followup 契约段；并行关卡例外追加 `-P2`/`-P3`。完整设计见 `docs/PROMPT_COMPILER_SESSION_POOL.md`。
  2. 续发**别传** `model` / `harness` / `file_ids` / `cost_budget`——仅创建时有效，续发传了核心硬报错；要换模型就换名开新会话。
  3. 同会话有 turn 在跑时续发被拒（忙碌保护，天然串行）——等子会话完成通知（inbox）再发，别重试轰炸。
  4. 要清零上下文：`sys_session_close`（tombstone，内部改写存储 title 释放名额）后同名可重建。
- **同类避免**：改派发逻辑前**先读 `spawn.py` 的 schema，再读 `tool_dispatch.py` 的 `_execute_subagent_tool`**——「先查 schema 再查 runtime」（坑 7 同款）。业务文档俗名（session_name）与 schema 真名（title）脱节是常态，一律以 schema 为准。

---

## 七、会话池首航（2026-08-20 金丝雀验收实锤）

### 坑 28：kimi-native 进全新 workdir，被 "Trust this folder?" 首启引导卡死

- **为什么遇到**：Kimi Code 在**从未信任过的目录**首次启动时弹信任引导页（Trust / Don't trust 选项，默认高亮 Don't trust），omnigent 自动建会话时无人点选——headless 死等家族（坑 4/5/11）的新成员。画面静止在引导页，runner 侧零报错，和坑 4 一样"像卡死而非失败"。
- **怎么解决**：`tmux -S <sock> send-keys Up Enter` 选 "Trust this folder" 即放行；信任按目录记忆，同目录后续会话不再弹。批量/自动化场景：**先把目标目录跑一次手工 kimi 完成信任**，或复用已信任目录。
- **同类避免**：任何 native CLI 被引向**新 workdir** 前，先想"它在这个目录的第一次启动有没有引导页"——信任页、登录页、升级提示都是无人值守杀手（坑 24 的 `/login` 是同款）。排查顺序：先 `capture-pane` 看 TUI 实况，再查日志。

### 坑 29：纯 API 创建的 kimi-native 顶层会话，首轮消息注入 stalled（根因未定位）

- **为什么遇到**：2026-08-20 金丝雀中，`POST /v1/sessions`（agent=controller，spec 默认 harness=kimi-native，无 labels）创建的会话：runner 日志显示 terminal+forwarder 已建（`Auto-created kimi terminal + forwarder`）、消息已转换（`_convert_raw_items_to_input: 1→1`），**随后静默**——TUI 停在 "No session yet"，注入永不发生，无报错。同 stack 上 UI 手工创建的 kimi-native 会话（生产「继续任务」）工作正常，差异点疑似在 API 创建路径的 labels/首轮注入触发条件。**根因未定位，先记症状与证据**（runner 日志止于 items 转换；`inject_user_message` 是 tmux 粘贴路径，理论上不需要 wire 存在；坑 24 的 K3 盒线就绪检测疑似相关）。
- **怎么解决**：绕开——Controller 大脑改用 pi（或 claude-sdk）等 headless harness 后 API 路径一次跑通；kimi-native 大脑继续走 UI 手工创建（生产已验证）。要根治需查 runner 首轮注入的触发条件（`inner/kimi_native_executor.py:run_turn` 之前的那段调度），修在嵌套副本。
- **同类避免**：「能建会话」≠「能跑 turn」≠「消息能到 TUI」——接一条 harness 要逐段验收（坑 16 同款教训：消息能进不等于事件能出）。自动化链路创建会话后，**前两分钟盯一眼 TUI 画面或 items 流**，沉默即异常。

### 坑 30：Codex 配额冻结（usageLimitExceeded），Controller 大脑全线瘫痪

- **为什么遇到**：2026-08-20 金丝雀首次发起即 `failed`：`codexErrorInfo=usageLimitExceeded`，官方回复 9 月 12 日恢复。默认大脑 codex 死 = 所有新 controller 会话死；**发现晚**——不改派发就永远不会撞见。
- **怎么解决**（已固化为流程）：
  1. 注册表 Scores 表给 `Codex current model` 行加 `cooldown-until: 2026-09-12`（额度耗尽不扣分，到期后给一关低成本复证）——生成器 `read_cooldowns` 自动跳过 codex 大脑和 exec_openai 工人；
  2. `python3 gen_controller_bundle.py --brain kimi|pi` 换脑重生成 + 重启 server（坑 1：重启才重新注册）；
  3. 大脑恢复后重跑生成器（不带 `--brain`）回到默认优先级。
- **同类避免**：配额死不等于模型死，**先记 cooldown 再换脑**，别让生成器下次又把死脑选回来（cooldown 不进 prompt，只影响生成期选择，见坑 27 的设计文档）。排班预设接管人（注册表 2026-07-31 已有同款教训：连续两轮额度尽死于 runner_disconnected）。
