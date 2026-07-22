# Omnigent + agentpeihe 双机部署指南（第一期）

> **目标读者：** 实施 Agent。按本文档顺序执行，每完成一步报告结果。
> **交付标准：** macOS 和 Windows 两台电脑各自独立可用。从 Omnigent Web UI 发任务，Controller 自动拆关卡、派发 Executor、审查结果——全程无需人工中继。

---

## 架构概览

```
┌─────────────────────────────────────────────────────┐
│                  Omnigent Web UI                     │
│           http://localhost:6767 (浏览器)              │
├─────────────────────────────────────────────────────┤
│              Omnigent Server (Python)                │
│       ~/.omnigent/config.yaml (provider 配置)         │
├─────────────────────────────────────────────────────┤
│             角色层（灵活分配，不绑定模型）               │
│   Controller ←→ Executor 池 ←→ Reviewer 池            │
│   任一模型可担任任一角色，修改 YAML 即可切换             │
├──────────┬──────────┬──────────┬────────────────────┤
│ Agent A  │ Agent B  │ Agent C  │ Agent D ...        │
│(Claude)  │(Codex)   │(Kimi)    │(DeepSeek/Grok/GLM) │
├──────────┴──────────┴──────────┴────────────────────┤
│                tmux 窗口矩阵                          │
│           (macOS 原生 / Windows WSL2)                 │
└─────────────────────────────────────────────────────┘
```

**角色定义（灵活分配）：**

| 角色 | 职责 | 谁担任 |
|------|------|--------|
| Controller | 拆任务→定关卡→派发→审查报告→决定下一步 | 用户选择：Claude / Codex / DeepSeek 均可（改 YAML 的 `executor.harness`） |
| Executor | 执行单个关卡，输出 Gate Execution Report | Controller 从模型池中按任务特征选择 |
| Reviewer | 复核结论、检查风险、提出反例 | Controller 选与 Executor 不同 vendor 的模型（无代码级强制，靠 Controller 派发时声明双方 vendor 并自检） |

**关键约束：**
- 角色与模型解耦——同一份 instructions，换 `harness`/`model` 即换角色
- Reviewer 必须和 Executor 不同 vendor。注意：omnigent **没有代码级校验**，该约束通过 Controller instructions 中的自检步骤落实（派发 Reviewer 时必须显式声明双方 vendor 并确认不同）
- 一次一个关卡，不跳步，不自动推进
- 任何执行 > 1 分钟的任务必须派发，Controller 不自己做
- 所有模型平等接入：原生 CLI 用 native harness，API 模型用 gateway provider + pi harness

---

## 第一步：macOS M1 部署

### 1.1 前置检查

```bash
python3 --version   # 需要 3.12+
node --version      # 需要 22+（安装期和运行时都必需：web UI 在 wheel 构建时现场 npm build）
npm --version
uv --version
tmux -V
```

缺什么装什么：

```bash
brew install python@3.12 node uv tmux gh
```

### 1.2 安装 Omnigent-zh-cn

```bash
uv tool install --force --python 3.12 "git+https://github.com/professoryu06/omnigent-zh-cn.git"
omnigent-zh platform-info
# 确认输出：native_tmux_supported=true, family=darwin
```

### 1.3 启动验证

```bash
omnigent-zh setup          # 交互式向导：检测本地 CLI、配置 provider、设默认 agent
omnigent-zh server start   # 后台启动服务器（默认 127.0.0.1:6767）
```

浏览器打开 `http://localhost:6767`，确认 Web UI 正常加载。

> **注意：** 无参 `omnigent-zh` 是 `run` 的别名——首次运行进入 setup 向导，之后启动默认 agent 并附着**终端 REPL**；它不是启动 Web UI 的命令。验证 Web UI 只需 `server start` + 浏览器。

**验证点：** `omnigent-zh platform-info` 输出截图 + 浏览器 Web UI 截图。

---

## 第二步：Windows + WSL2 部署

### 2.1 确认 WSL2 状态

在 PowerShell 中：

```powershell
wsl --status
wsl -l -v
```

如果没有 WSL2：

```powershell
wsl --install -d Ubuntu-24.04
```

### 2.2 WSL2 内安装依赖

```bash
sudo apt-get update
sudo apt-get install -y tmux bubblewrap git gh
gh auth login
gh auth setup-git
```

### 2.3 安装 Python/Node/uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.profile
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs

# 验证
python3 --version && node --version && npm --version && uv --version
```

### 2.4 安装 Omnigent-zh-cn

```bash
uv tool install --force --python 3.12 "git+https://github.com/professoryu06/omnigent-zh-cn.git"
omnigent-zh platform-info
# 确认输出：native_tmux_supported=true, family=linux, WSL2=yes
```

### 2.5 安装原生 CLI 后端

```bash
cd ~/
git clone https://github.com/professoryu06/omnigent-zh-cn.git omnigent-zh-cn-src
cd omnigent-zh-cn-src
bash ops/cli-integration/install-wsl-cli-backends.sh
exec bash
bash ops/cli-integration/verify-wsl-cli-backends.sh
```

逐个登录 CLI：

```bash
claude        # Claude Code
kimi login    # Kimi Code
# Hermes、Qwen 等按各自文档登录
```

### 2.6 启动验证

```bash
omnigent-zh setup
omnigent-zh server start
```

在 Windows 浏览器访问 `http://localhost:6767`，确认 Web UI 正常加载。（同 1.3：无参 `omnigent-zh` 是终端 REPL，不是 Web UI 启动命令。）

**Windows 关键注意事项：**
- 仓库必须 clone 到 Linux 文件系统（`~/...`），不能放 `/mnt/c/...`
- 不要把 Windows 凭据复制进 WSL，每个 CLI 在 WSL 内独立认证
- 必须从 WSL2 终端启动 Omnigent，不能在 PowerShell 启动
- Windows 原生只能跑 Web UI 和 SDK harness，不能跑 tmux 原生 CLI

**网络与代理（WSL2 最易踩的坑，交接文档必须覆盖）：**
- macOS 侧方案：Shadowrocket 系统代理 `http://127.0.0.1:1082` + `NO_PROXY=api.deepseek.com,api.moonshot.cn`（国外 API 走代理、国内直连），已实测可用
- Windows+WSL2 侧**不能照搬**：WSL2 默认 NAT 网络下，WSL 里的 `127.0.0.1` 不是 Windows 的 `127.0.0.1`，Windows 上代理软件（Clash Verge / v2rayN 等）的端口从 WSL 里直接访问不到。两个解法任选：
  1. **mirrored 网络模式（推荐）**：在 Windows 用户目录的 `.wslconfig` 写 `[wsl2]\nnetworkingMode=mirrored`，重启 WSL 后 WSL 共享 Windows 的 localhost，`127.0.0.1:<代理端口>` 直接用
  2. **NAT 模式**：WSL 里用 `ip route show default | awk '{print $3}'` 取 Windows 宿主机 IP 作为代理地址，且代理软件必须开"允许局域网连接"
- WSL2 内同样设置 `HTTPS_PROXY` + `NO_PROXY`（国内 API 域名白名单），规则与 macOS 一致
- **本期第二步的执行方式：** 由 Windows 侧 agent 按交接文档执行（主公只负责在两台机器间传递文档和回报输出），交接文档需自带每步的预期输出与失败分支，不假设执行者看过本仓库

**验证点：** `omnigent-zh platform-info` 输出截图 + 浏览器 Web UI 截图。

---

## 第三步：配置 Provider

编辑 `~/.omnigent/config.yaml`（两台机器各自配置）：

```yaml
providers:
  # DeepSeek 官方 API
  deepseek:
    kind: gateway
    openai:
      base_url: https://api.deepseek.com/v1
      api_key: $DEEPSEEK_API_KEY
      models:
        default: deepseek-v4-pro

  # Grok (xAI)
  grok:
    kind: gateway
    openai:
      base_url: https://api.x.ai/v1
      api_key: $GROK_API_KEY
      models:
        default: grok-4.5

  # 千问 API（DashScope）
  dashscope:
    kind: gateway
    openai:
      base_url: https://dashscope.aliyuncs.com/compatible-mode/v1
      api_key: $DASHSCOPE_API_KEY
      models:
        default: qwen-max

  # GLM（智谱）
  zhipu:
    kind: gateway
    openai:
      base_url: https://open.bigmodel.cn/api/paas/v4
      api_key: $ZHIPU_API_KEY
      models:
        default: glm-4-plus
```

环境变量在两台机器的 shell 配置文件中设置（macOS: `~/.zshrc`，WSL2: `~/.bashrc`）：

```bash
export DEEPSEEK_API_KEY="你的 key"
export GROK_API_KEY="你的 key"
export DASHSCOPE_API_KEY="你的 key"
export ZHIPU_API_KEY="你的 key"
```

**密钥管理（可选）：** 除 `$VAR` 环境变量展开外，Omnigent 的 provider 配置还支持 `api_key_ref` / `keychain:` 引用，可避免在 shell 配置文件中明文存放 key。需要时查阅 `omnigent-zh setup` 向导中的 provider 配置项。

**注意：** 已登录的本地 CLI（Claude Code、Codex、Kimi）Omnigent 会自动检测，不需要在 config.yaml 中配置。

**验证点：** `omnigent-zh config list` 能看到所有 provider。（`setup` 没有 `list` 子命令。）

---

## 第四步：创建 Agent 配置（角色灵活分配）

**设计原则：** 所有 agent 使用同一份 agentpeihe 关卡协议 instructions。角色差异仅由 Controller 派发关卡时在消息中指定的 `Role` 字段决定。切换角色只需改 YAML 中的 `harness`/`model`，instructions 不变。

### 4.1 自动调配：跑生成器，不手改 YAML

**设计原则：** 角色与模型解耦，所有工人共用同一份关卡协议 prompt，角色由 Controller 派发时指定。模型池不写死在 YAML 里，而是由 `gen_controller_bundle.py` 按**本机实际环境**生成——换模型、换大脑、换机器，重跑一次脚本即可。

```bash
python3 gen_controller_bundle.py            # 生成 ~/.omnigent/agents/controller/
python3 gen_controller_bundle.py --dry-run  # 只看计划不落盘
python3 gen_controller_bundle.py --brain codex   # 指定大脑（默认自动择优）
```

生成器自动做的事：

- 检测本机 CLI（claude / codex / kimi / pi / grok）与 API key
- **嗅探 claude CLI 的真实后端**（读 `~/.claude/settings.json` 的 `ANTHROPIC_BASE_URL`，CC Switch 壳按实际 vendor 算，不按 CLI 名）
- 读注册表 `~/.agent-collaboration/model-capability-registry.md` 的 `cooldown-until:`，冷却期模型不出现在工人池
- 按 harness 特性配好工人参数：claude-native 配 `permission_mode: auto`（headless 免确认）、codex-native 配 `yolo: true`、kimi-native **不生成**（TUI 审批 headless 死等，已知无解）、pi 工人的 `model`/`auth` 放 `executor` 顶层并显式绑定 provider、grok CLI 生成 `acp:grok-build` 工人并补 `~/.omnigent/config.yaml` 的 acp 配置块
- 生成 Controller prompt：可用池表（含实际 vendor）、异 vendor 互审规则、9 字段契约、中文会话命名规则

### 4.2 第一期实测阵型（供对照）

| 组件 | Harness | 实际 Vendor | 说明 |
|------|---------|------------|------|
| 大脑 controller | claude-sdk | moonshot（Kimi K3 经 CC Switch） | 大脑必须非 native harness，否则 Web UI 显示成 harness 名 |
| exec_moonshot | claude-native（permission_mode: auto） | moonshot | executor/reviewer |
| exec_deepseek | pi（model/auth 顶层 + provider 绑定） | deepseek | executor/reviewer |
| exec_xai | acp:grok-build | xai | Grok Build CLI，SuperGrok 订阅，executor/reviewer |
| codex | codex-native | openai | cooldown 至 2026-07-25（额度尽，解封后重跑生成器自动入池） |
| kimi-native | — | — | **排除**：TUI 审批 omnigent 无法代答，headless 死等 |

### 4.3 注册与重载（两个必记动作）

1. **注册**：`omnigent-zh server --no-open --agent ~/.omnigent/agents/controller`（前台模式）。`server start` 后台模式不支持 `--agent`；`~/.omnigent/agents/` 下的文件**不会**被自动注册。
2. **改后必重启**：server 拿的是启动时的 bundle 快照，改了 bundle 或重跑了生成器，必须重启 server 重新注册，否则跑的还是旧配置。

**schema 硬约束（手改时必看，生成器已内置）：**
- 大脑 harness 用非 native（claude-sdk / codex / pi），才能以本名进 Web UI"智能体"区
- pi 工人：`model` 和 `auth: {type: provider, name: <provider>}` 必须在 `executor` **顶层**——`executor.config` 是不透明兼容层，spawn 链路不读
- gateway provider 的 key：`export OMNIGENT_RUNNER_ENV_PASSTHROUGH=<KEY名>`，否则 runner 进程拿不到（`env_passthrough` 是另一套，进子进程的，别搞混）
- 子 agent 共用 `guardrails.blast_radius`（headless 无法回答审批，灾难性命令 deny、其余放行）

### 4.4 角色中英文命名

角色内部用英文 key，显示用中文名（三国主题）。映射关系：

| 英文 Key（协议） | 中文显示名 | 角色说明 |
|-----------------|-----------|---------|
| `boss` | 主公 | 最终决策者，批准关卡 |
| `controller` | 诸葛丞相 | 制定计划、调度关卡、分配模型 |
| `executor` | 关二爷 | 执行单个关卡，汇报后停止 |
| `reviewer` | 法正（御史中丞） | 独立核验，检查风险，提出反例 |
| `specialist` | 马良 | 领域专家，专项深度审查 |

关卡契约的 `Role` 字段写英文 key，Web UI 和报告显示中文名。**子代理会话命名必须用中文角色名**（Web UI 子代理图谱直接显示它）：`session_name` 格式 `<角色中文名>-<关卡号>-<简述>`，例：`关二爷-G1-统计脚本`、`法正-G2-独立核验`——禁止英文 slug（生成器已写进 Controller prompt）。

### 4.5 模型能力动态评分（多维度）

评分数据存在共享注册表 `~/.agent-collaboration/model-capability-registry.md` 的 `## Scores` 表，**7 个维度独立记分**（0–100）：前端 / 后端实现 / Agent 协同 / 修 bug / 架构 / 检索格式化 / 安全数据（维度参照 2026 权威 agent 评测标准，详见 SKILL.md）。只信实战关卡证据，不信公开榜单。规则（逐维度独立）：

- **某维度 0 分 = 该维度未校准**：只能接校准关（低风险、可自动验证），过了拿 60 基准分
- 同维度过关 +5（上限 95），被拒 −10（归零该维度重新校准）
- **给新模型机会**：低风险关候选列表里至少带一个该维度 60 分以下的模型
- **定期复证**：某维度 30 天无新证据即 stale，排低风险复证关刷新；stale 候选评级 −10
- 没额度/不可用不扣分，标记 `cooldown-until: YYYY-MM-DD`（生成器读它自动摘人），恢复后给低成本关卡复证
- 证据未闭环的分数标 `暂记`，闭环后重判

当收到项目设计文档时，Controller 输出推荐矩阵（候选评分取对应维度的注册表 score）：

```
| 板块 | 推荐 Agent | 模型 | 候选评分 | 评分依据 |
|------|-----------|------|---------|---------|
| 代码实现 | 关二爷 | deepseek-v4-pro | 82 | 后端维度 70，任务契合 |
| 故障诊断 | 关二爷 | grok-4.5 | 85 | 修bug维度 65，最高 |
| 安全审查 | 法正 | 与 executor 异 vendor 中维度最高者 | — | vendor ≠ executor |
```

### 4.6 模型更新触发

老板说"XX 更新了"即可触发模型池更新。流程：

1. 搜索该厂商最新模型信息
2. 确认准确模型名（区分官方名和社区别名）
3. 旧模型标记 `deprecated`，不出现在推荐中
4. 新模型以 `Candidate` 等级加入注册表（0 分，先过校准关）
5. **重跑 `gen_controller_bundle.py` 并重启 server**（不要手改 bundle 里的模型池表）

---

## 第五步：核心验收 —— agentpeihe 自动中继测试

### 前置检查（验收前必须全部满足，否则 8 项标准无法判定）

1. `omnigent-zh config list` 确认**至少两个不同 vendor** 的 provider/harness 真实可用（本地 CLI 已登录，或 gateway key 已配）。验收第 6 项要求 Reviewer 与 Executor 不同 vendor，只有一个 vendor 可用时该条必然失败。
2. 在 Omnigent server 的工作目录放置测试用 `data.csv`（含若干数值列，例如 3 列 × 10 行随机数），供 Executor 读取。测试任务引用该文件，文件不存在会导致 Executor 关卡失败。
3. server 必须从 tmux 可用的终端启动（native harness 子 agent 依赖 tmux）。

### 测试任务

在 Web UI 中向 Controller 发送以下测试任务：

> 请帮我写一个 Python 脚本，读取 data.csv 文件，计算每列的平均值和标准差，输出到 result.json。按 agentpeihe 关卡协议执行。

### 验收标准（8 项全部通过才算合格）

1. [ ] Controller **不自己写代码**，而是输出关卡计划
2. [ ] 第一个关卡包含完整的 9 字段关卡契约
3. [ ] Controller 使用 agent 工具（`claude_agent` / `deepseek_agent` 等）将关卡派发给 Executor
4. [ ] Executor 执行后输出 Gate Execution Report（按模板格式）
5. [ ] Controller 审查报告，确认满足 Validation 条件后才推进
6. [ ] Reviewer 审查实现结果（与实现者不同 vendor，以 Controller 派发消息中的 vendor 自检声明为准）
7. [ ] Controller 汇总并向用户报告完成
8. [ ] **全程不需要人工复制粘贴任何内容**

### 扩展验证

- [ ] 连续执行 3 个不同类型任务，Controller 能根据不同任务选择不同 Executor
- [ ] Reviewer 确实和 Executor 不同 vendor
- [ ] 注册表 Scores 表（model-capability-registry.md）有更新

---

## 附录 A：常见问题

### macOS

| 问题 | 解决 |
|------|------|
| `tmux: command not found` | `brew install tmux` |
| `omnigent-zh: command not found` | `uv tool list` 确认安装，检查 `~/.local/bin` 在 PATH |
| Web UI 空白 | 检查 Node 22+ 是否安装，重新 `uv tool install --force`（web UI 在 wheel 构建时现场 npm build，缺 Node 会构建失败或只装出 API） |
| 无参 `omnigent-zh` 占住终端 | 正常——它是终端 REPL，不是 Web UI 启动命令；Web UI 用 `omnigent-zh server start` 后开浏览器 |

### Windows/WSL2

| 问题 | 解决 |
|------|------|
| `native_tmux_supported=false` | 当前在 Windows 原生终端，切换到 WSL2 |
| WSL2 内装完 `omnigent-zh: command not found` | `source ~/.profile` 刷新 PATH |
| Windows 浏览器打不开 localhost:6767 | WSL2 端口转发问题，`wsl --shutdown` 后重启 WSL2 |
| Claude Code 在 WSL2 连不上 CC Switch | 需要 `netsh interface portproxy` 将 WSL IP 转发到 Windows 127.0.0.1:15721 |
| 启动后看不到原生 CLI 选项 | 确认是从 WSL2 终端启动，不是从 PowerShell |

### Provider

| 问题 | 解决 |
|------|------|
| DeepSeek/Grok/GLM 不显示 | 检查 `~/.omnigent/config.yaml` 格式，注意缩进；检查环境变量已 export |
| `api_key: $VAR` 未展开 | Omnigent 使用 `os.path.expandvars` 惰性展开，确认变量在启动 server 的 shell 中已 export |
| 本地 CLI 未被检测到 | 确保在安装 Omnigent 前已完成 CLI 登录，或重新运行 `omnigent-zh setup` |
| 想看已配置 provider 列表 | `omnigent-zh config list`（`setup` 没有 `list` 子命令） |

### 第一期实测踩坑清单（G5 调试实录，全部已实锤）

| # | 坑 | 正解 |
|---|---|---|
| 1 | `~/.omnigent/agents/*.yaml` 不被 server 自动注册，Web UI 看不到自定义 agent | 前台模式 `omnigent-zh server --agent <bundle目录>` 注入；改 bundle 后必须重启重新注册 |
| 2 | 自定义 agent 用 native harness（claude-native 等）会出现在"执行器"区并显示成 harness 名，找不到名字 | Controller 大脑必须用非 native harness（claude-sdk/codex/pi），才能以本名进"智能体"区 |
| 3 | headless 子 agent 被 Claude Code 权限弹窗卡死 | 子 agent bundle 配 `executor.config.permission_mode: auto`（polly 同款） |
| 4 | kimi-native 子 agent 被 Kimi CLI 的 TUI 审批卡死，omnigent 无法代为应答 | 目前无解，kimi-native 不进自动化池；kimi 模型走 CC Switch 套 claude 壳 |
| 5 | pi 子 agent 报 "No API key found"：`model` 写在 `executor.config` 里被静默忽略 | `model` 必须在 `executor` 顶层；另需 `executor.auth: {type: provider, name: <config.yaml 里的 provider 名>}` 显式绑定 |
| 6 | 修好 YAML 后 runner 仍报凭证无法解析 | host→runner 只转发凭证白名单（无 DEEPSEEK_API_KEY）：`export OMNIGENT_RUNNER_ENV_PASSTHROUGH=DEEPSEEK_API_KEY` 并重启 host+server |
| 7 | `env_passthrough` 加了 API key 也没用 | 那是进子进程的白名单；gateway 路径 key 走 models.json（AUTH_COMMAND），与 env 透传无关 |

---

## 附录 B：Phase 2 方向（本期不实现）

**场景：** Mac 上跑了一半的任务，回到家想用 Windows 继续。

**候选方案：**

| 方案 | 说明 |
|------|------|
| NAS/软路由做 Server | Omnigent Server 部署在常开 NAS，两台电脑只跑 Runner 连接。用户已有 NAS，最自然。 |
| 轻量云服务器 | 低配 VPS 跑 Server，两台电脑都不需要常开。月费约 30-50 元。 |
| Tailscale + 远程 Runner | Omnigent 已有 Tailscale 部署支持（`deploy/tailscale/`）。 |
| Git 同步 + 导入导出 | 项目文件 Git 同步，会话状态手动迁移。最简单但体验差。 |
