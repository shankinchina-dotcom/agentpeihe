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

### 坑 5：kimi-native 子 agent 同样卡死，且无法可解
- **为什么遇到**：Kimi CLI 的 TUI 审批提示 omnigent 拦截不了（源码注释明说："the yes/no is answered in the TUI, which Omnigent cannot intercept"）。
- **怎么解决**：kimi-native 不进自动化池。**kimi 模型的正确接法是 CC Switch 套 claude 壳**（`ANTHROPIC_BASE_URL=https://api.kimi.com/coding/`），既有 K3 的脑子又有 Claude 壳的完整工具协议。
- **同类避免**：接入新 CLI 前，先查 omnigent 源码里它 harness 的 docstring——审批模型写得很清楚，别等跑起来才发现。

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

---

## 五、工程习惯（本次最大的两条元教训）

1. **先查 schema，再查 runtime。** 配置不生效时，parser 的字段定义是一手证据，运行时日志是二手。三层故障里有两层（model 层级、credential 白名单）都是"先读定义五分钟，胜过猜日志三小时"。
2. **配置生成化，不手改。** 换模型/换大脑/换机器 = 重跑 `gen_controller_bundle.py`（环境检测 + CC Switch 嗅探 + 注册表 cooldown 全部自动），手改 YAML 是技术债的源头。本仓库的快速启动就是用生成器，而不是给你一份静态 YAML。
