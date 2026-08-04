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
- **同类避免**：Controller 派发时的 `session_name` 必须用**中文角色名**（`关二爷-G1-统计脚本`、`法正-G2-独立核验`），别用英文 slug——这条已写进 controller prompt 模板和生成器。

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

---

## 五、工程习惯（本次最大的两条元教训）

1. **先查 schema，再查 runtime。** 配置不生效时，parser 的字段定义是一手证据，运行时日志是二手。三层故障里有两层（model 层级、credential 白名单）都是"先读定义五分钟，胜过猜日志三小时"。
2. **配置生成化，不手改。** 换模型/换大脑/换机器 = 重跑 `gen_controller_bundle.py`（环境检测 + CC Switch 嗅探 + 注册表 cooldown 全部自动），手改 YAML 是技术债的源头。本仓库的快速启动就是用生成器，而不是给你一份静态 YAML。
