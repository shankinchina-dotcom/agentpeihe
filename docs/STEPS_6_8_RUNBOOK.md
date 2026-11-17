# 步骤 6–8 RUNBOOK（Win10 + WSL2 本机）

> 生成日期：2026-07-23
> 最后更新：2026-07-23（**运行面快照**）
> 适用机：Windows 10 + WSL2 Ubuntu 24.04（NAT）
> 原则：**不手改** `~/.omnigent/agents/controller/**` YAML；换池 = 重跑 `gen_controller_bundle.py`
> 前置：步骤 1–5 已完成；代理 WSL 三活（见 `WIN10_DEPLOY_PROGRESS.md`）

**相关：**

| 文档/脚本 | 用途 |
|-----------|------|
| `WIN10_DEPLOY_PROGRESS.md` | 进度三拆与本机运行面台账 |
| `WIN10_PITFALLS_SOLUTIONS.md` | Win10 坑→解法总册 |
| `../scripts/check_win10_wsl.sh` | WSL 一键自检（网关、代理、PATH、登录、Claude 壳、现有 bundle、UI） |

---

## 0. 当前本机快照（2026-07-23 运行面步骤 1–8）

| 项 | 状态 |
|----|------|
| 平台 | Win10 19045 + WSL2 Ubuntu 24.04 **NAT** |
| 网关 | 示例 `172.30.176.1`（**以 `ip route` 默认网关为准**） |
| Clash | `0.0.0.0:7897`；运行面已通，当前宽防火墙规则仍待绑定唯一的已连接 WSL IPv4 接口收紧 |
| WSL 代理 | `nc` 通；`generate_204=204`；`github=200` |
| claude / codex / pi / kimi | 二进制均有（kimi：`~/.kimi-code/bin`） |
| Codex | WSL **`Logged in using ChatGPT`** |
| Kimi | **credentials 存在** |
| `~/.claude/settings.json` | DeepSeek Claude 壳：`ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`；默认 **`ANTHROPIC_MODEL=deepseek-v4-flash-vision-exp[1M]`**（vision-exp 图片输入 + 1M 上下文；无 `[1M]` 则 TUI 常显示 200k） |
| controller bundle | **已生成**：大脑 `codex`；工人 `exec_deepseek`、`exec_openai`（`gpt-5.6-sol`）、`exec_moonshot` |
| Server | tmux 会话 **`omnigent`**；`:6767` → **200** |
| 缺 | **无 Grok CLI / `exec_xai`**；**8/8 业务验收未做** |

**状态三拆：**

- 文档：修订后可提 PR
- 运行面：步骤 1–8 已通
- 验收：未完成

**说明：** 本机若已达上表，**步骤 6（登录/DeepSeek）可跳过**；换机或重装 WSL 后按下列命令重做。

---

## 1. 生成器逻辑摘要（只读，勿手改产出）

**输入（检测）：**

| 来源 | 路径/方式 | 作用 |
|------|-----------|------|
| CLI | `shutil.which(claude/codex/pi/kimi/grok)` | 有无决定是否入池 |
| CC Switch | `~/.claude/settings.json` → `env.ANTHROPIC_BASE_URL` / key 前缀 | 真实 vendor（deepseek/moonshot/anthropic/…） |
| API keys | 环境变量 `DEEPSEEK_API_KEY` / `GROK_API_KEY` / `ZHIPU_API_KEY` / `DASHSCOPE_API_KEY` | 仅当 `pi` 在 PATH 时生成 pi 工人 |
| cooldown | `~/.agent-collaboration/model-capability-registry.md` 中 `cooldown-until:` | 未到期模型不进 tools |
| CLI 参数 | `--brain claude-sdk\|codex\|pi`、`--out`、`--dry-run` | 覆盖默认大脑/输出路径 |

**嗅探规则（`sniff_claude_vendor`）：**

- URL 含 `kimi.com` / `moonshot` 或 key 前缀 `sk-kimi-` → `moonshot`（**禁止入池**，备注走 kimi-native）
- URL 含 `deepseek` → `deepseek` → 生成 `exec_deepseek`（`claude-native` + `permission_mode: auto`）
- 无 URL 或 anthropic.com → `anthropic` → 可选 `exec_anthropic`
- 无 settings 文件 → `unknown` → **不生成** Claude 壳工人

**通道硬规则（生成器内置）：**

- Kimi → 只 `kimi-native`（`exec_moonshot`）
- DeepSeek 主路径 → Claude 壳 `exec_deepseek`；若已有 Claude 壳 deepseek，**跳过** pi deepseek
- DeepSeek 默认模型 **vision-exp**（图片输入）+ 上下文 **1M**：壳侧 `ANTHROPIC_MODEL=deepseek-v4-flash-vision-exp[1M]`（见 PITFALLS 坑 21）；pi 直连备选稳定版 `deepseek-v4-flash`
- 大脑默认：`codex` → `claude-sdk`（仅真 anthropic）→ `pi`（有 pi + 任一 API key）
- 工人 `model`/`auth`（pi）写在 `executor` **顶层**；pi deepseek 模型 id 用 `deepseek-v4-flash`（无 `[1M]` 后缀）
- Codex 工人模型常量：`gpt-5.6-sol`（见生成器 `CODEX_WORKER_MODEL`）

**输出：**

```
~/.omnigent/agents/controller/
  config.yaml                 # 大脑 harness + 模型池表 + tools.agents
  agents/exec_*/config.yaml   # 各工人
```

可选副作用：若有 `grok`，向 `~/.omnigent/config.yaml` **追加** `acp.agents` 块（不写 deepseek gateway——那是步骤 6 人工配）。

**不写：** DeepSeek gateway provider、API key、登录态。

**本机 dry-run / 落盘预期：**

```text
大脑: codex
工人: exec_deepseek, exec_openai, exec_moonshot
# 无 grok → 无 exec_xai
```

---

## 2. 最小可用配置（至少两家不同 vendor）

### 方案 A — 零 API key（历史最小路径；本机已升级到 B）

| 角色 | 来源 | vendor |
|------|------|--------|
| 大脑 | codex（自动） | openai |
| 工人 1 | `exec_openai`（codex headless） | openai |
| 工人 2 | `exec_moonshot`（kimi-native） | moonshot |

### 方案 B — DeepSeek 主路径 + Codex（**本机采用**）

| 角色 | 来源 | vendor |
|------|------|--------|
| 大脑 | codex | openai |
| 工人 1 | `exec_deepseek`（claude-native ← settings） | deepseek |
| 工人 2 | `exec_openai`（`gpt-5.6-sol`） | openai |
| 工人 3 | `exec_moonshot` | moonshot |

**禁止：** 把 CC Switch / settings 指到 Moonshot/Kimi 占 Claude 壳。

### 方案 C — 仅 Codex + DeepSeek gateway（无 claude settings）

- 大脑 codex；工人 `exec_openai` + `exec_deepseek`（pi）
- 需要：`export DEEPSEEK_API_KEY=...`、`~/.omnigent/config.yaml` providers.deepseek、`OMNIGENT_RUNNER_ENV_PASSTHROUGH`
- 与红线「DeepSeek 主路径走 Claude 壳」不完全一致；作备用通道。

---

## 3. 步骤 6–8 命令清单（WSL bash，可复制）

> 全部在 **WSL Ubuntu** 执行。密钥用占位符，勿提交 git。
> **本机已完成后：6 可跳过；7/8 仅在换池、换机、重装后需要。**

### 3.0 前置自检（每次开干先跑）

优先一键脚本：

```bash
bash ~/agentcenter/agentpeihe/scripts/check_win10_wsl.sh
# 或（在 docs/ 旁）： bash ../scripts/check_win10_wsl.sh
```

手跑等价探针：

```bash
source ~/.bashrc
export PATH="$HOME/.kimi-code/bin:$HOME/.local/bin:$PATH"

echo "=== CLI ==="
which claude codex pi kimi omnigent-zh
claude --version; codex --version; pi --version; kimi --version 2>/dev/null | head -1
omnigent-zh platform-info

echo "=== 代理（NAT；网关以 ip route 为准）==="
GW=$(ip route show default | awk '{print $3; exit}')
echo "GW=$GW"
nc -z -w 2 "$GW" 7897 && echo "proxy TCP OK" || echo "proxy TCP FAIL → 查 Clash 0.0.0.0:7897 + 防火墙（见 WIN10_PITFALLS_SOLUTIONS.md W05/W06）"
curl -sS -o /dev/null -w "generate_204=%{http_code}\n" --connect-timeout 5 -x "http://${GW}:7897" https://www.google.com/generate_204 || true
curl -sS -o /dev/null -w "github=%{http_code}\n" --connect-timeout 8 -x "http://${GW}:7897" https://github.com/ || true
# 国内直连探针（401 也算通）
curl -s -o /dev/null -w "deepseek:%{http_code}\n" --connect-timeout 5 https://api.deepseek.com/v1/models || true

echo "=== 登录态 ==="
codex login status 2>&1 | head -3
test -f "$HOME/.kimi-code/credentials/kimi-code.json" && echo "kimi credentials: OK" || echo "kimi credentials: MISSING"

echo "=== Claude 壳 ==="
python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / ".claude" / "settings.json"
if not p.exists():
    print("NO_SETTINGS")
else:
    print(json.loads(p.read_text(encoding="utf-8"))["env"].get("ANTHROPIC_BASE_URL", "NO_URL"))
PY

echo "=== 生成器 dry-run ==="
python3 ~/agentcenter/agentpeihe/gen_controller_bundle.py --dry-run

echo "=== UI ==="
curl -s -o /dev/null -w "ui=%{http_code}\n" http://127.0.0.1:6767 || true
```

**运行面预期：** 代理 OK；codex ChatGPT；kimi credentials OK；BASE_URL 含 `deepseek`；工人三家；ui=200。

**Windows 侧辅助（pwsh）：**

```powershell
# Clash 服务名勿写死
Get-Service *clash*
# 示例 Name：clash_verge_service —— 以本机输出为准

netstat -ano | findstr ":7897" | findstr "LISTEN"
# 期望含 0.0.0.0:7897

# 防火墙收紧：先取 WSL 别名，再筛选已连接的 IPv4 接口；必须唯一
$wslAliases = @(Get-NetAdapter -IncludeHidden |
  Where-Object { $_.Name -match 'WSL' -or $_.InterfaceDescription -match 'WSL' } |
  Select-Object -ExpandProperty Name -Unique)
$wslIPv4 = @(Get-NetIPInterface -AddressFamily IPv4 |
  Where-Object { $_.InterfaceAlias -in $wslAliases -and $_.ConnectionState -eq 'Connected' })
$wslIPv4 | Format-Table InterfaceAlias, InterfaceIndex, ConnectionState
if ($wslIPv4.Count -ne 1) { throw '必须人工确认且只能选中一个 WSL IPv4 接口；禁止 RemoteIP=Any 兜底' }
```

---

### 步骤 6 — provider / Claude 壳配置

> **本机配置已完成，可跳过。换机 / 清 HOME / 轮换 key 后重做。**

#### 6A 方案 A（无 DeepSeek key）

```bash
# 无需 ~/.omnigent/config.yaml 的 deepseek 段
# 仅确保登录（浏览器 OAuth，须 WSL 交互终端）：
codex login
# kimi login（OAuth 设备码；按本机 kimi 文档）
# ~/.kimi-code/bin/kimi login
# 预期：Logged in to managed:kimi-code
# 网页 TUI 冷启动「Send /login」≠ 这条 CLI，见 PITFALLS 坑 24
# 无反应 / 输入框未就绪见坑 24（盒线 │ >）；Hermes「未接收粘贴」见坑 25
```

#### 6B 方案 B（DeepSeek Claude 壳，主路径）— **本机已用**

```bash
# 1) Claude settings（CC Switch 等价物，仅 DeepSeek）
mkdir -p ~/.claude
# 将 <DEEPSEEK_API_KEY> 换成主公提供的 key（勿提交 git、勿写进对话日志）
cat > ~/.claude/settings.json <<'EOF'
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_API_KEY": "<DEEPSEEK_API_KEY>"
  }
}
EOF

# 2) 验证 sniff 会认出 deepseek
python3 - <<'PY'
import json
from pathlib import Path
p = Path.home() / ".claude" / "settings.json"
print(json.loads(p.read_text(encoding="utf-8"))["env"].get("ANTHROPIC_BASE_URL"))
PY
# 应含 deepseek

# 3) （可选备用）gateway provider + runner 透传
mkdir -p ~/.omnigent
# 若文件已存在，用编辑器合并，不要盲目覆盖 acp 等块
cat > ~/.omnigent/config.yaml <<'EOF'
providers:
  deepseek:
    kind: gateway
    openai:
      base_url: https://api.deepseek.com/v1
      api_key: $DEEPSEEK_API_KEY
      models:
        default: deepseek-v4-flash
EOF

# 4) bashrc 追加（仅一次；已有则跳过）
grep -q 'DEEPSEEK_API_KEY' ~/.bashrc || cat >> ~/.bashrc <<'EOF'

# omnigent DeepSeek（步骤 6）
export DEEPSEEK_API_KEY="<DEEPSEEK_API_KEY>"
export OMNIGENT_RUNNER_ENV_PASSTHROUGH="DEEPSEEK_API_KEY"
EOF
source ~/.bashrc
# 把 bashrc 里的占位符改成真 key 后再 source

# 5) 验证
omnigent-zh config list
# 应看到本地 🎟️ CLI + 🌐 deepseek（若写了 gateway）
```

**NO_PROXY 已在 bashrc 含 `api.deepseek.com` 时，DeepSeek 走直连，不依赖 Clash allow-lan。**

#### 6C 方案 C（仅 pi DeepSeek，无 Claude 壳）

同 6B 的 gateway + env，**不要**写 `settings.json` 指 deepseek；生成器会出 `exec_deepseek` harness=pi。

**登录验证（本机已通时可跳过）：**

```bash
codex login status
# 期望含：Logged in using ChatGPT

test -f ~/.kimi-code/credentials/kimi-code.json && echo kimi_ok
```

> Codex 若只在 Windows 登录成功、WSL 仍无 `~/.codex/auth.json`：优先在 **WSL 再 login**；应急同机从 `/mnt/c/Users/<你>/.codex/auth.json` 拷到 `~/.codex/`（**禁止跨机器复制凭据**）。见 `WIN10_PITFALLS_SOLUTIONS.md` W14。

---

### 步骤 7 — 生成 controller bundle

> **本机已生成三工人池。** 换 CLI / 改 settings / 补 Grok 后必须重跑；**禁止手改**产出 YAML。

```bash
source ~/.bashrc
export PATH="$HOME/.kimi-code/bin:$HOME/.local/bin:$PATH"

# 先 dry-run 看池
python3 ~/agentcenter/agentpeihe/gen_controller_bundle.py --dry-run

# 落盘（默认大脑自动；本机有 codex → codex）
python3 ~/agentcenter/agentpeihe/gen_controller_bundle.py
# 若要强制：  --brain codex

# 检查产出
echo "=== brain harness ==="
grep -A2 'config:' ~/.omnigent/agents/controller/config.yaml | head -20
echo "=== workers ==="
ls ~/.omnigent/agents/controller/agents/
echo "=== tools.agents ==="
grep -A20 '^tools:' ~/.omnigent/agents/controller/config.yaml
```

**本机预期工人：** `exec_deepseek` `exec_openai` `exec_moonshot`
（`exec_openai` model = `gpt-5.6-sol`）
**有 Grok 后额外：** `exec_xai`

**失败分支：**

| 现象 | 处理 |
|------|------|
| `没有可用的大脑` | 装并 PATH 到 codex，或真 anthropic，或 pi+API key |
| `--brain claude-sdk` 报 vendor 非 anthropic | 不要用 claude-sdk 当大脑；用 `--brain codex` |
| 无 `exec_moonshot` | `export PATH="$HOME/.kimi-code/bin:$PATH"` 后重跑 |
| 无 `exec_deepseek` | 查 settings.json URL 是否含 deepseek；或 export `DEEPSEEK_API_KEY` 走 pi |
| 出现 moonshot 的 claude-native | **违规**：settings 指了 Kimi，改回 deepseek 或删 settings 后重跑 |
| 无 `exec_xai` | 正常缺口：先装 Grok CLI 再 gen |

换池后：**必须重启 server**（步骤 8），否则仍是旧快照。

---

### 步骤 8 — 启动 server（前台注册 controller）

> **本机：** tmux `omnigent` 已跑，`:6767=200`。仅在进程挂掉 / 换池后重做。

```bash
source ~/.bashrc
export PATH="$HOME/.kimi-code/bin:$HOME/.local/bin:$PATH"
# 方案 B/C 时确保 key 在当前 shell
# echo "DS=${DEEPSEEK_API_KEY:+set}"

# 停旧实例
omnigent-zh server stop 2>/dev/null || true

# 前台启动（必须 --agent；server start 后台不注册 agent）
# 建议 tmux，避免关终端掉服
tmux new -A -s omnigent
omnigent-zh server --no-open --agent ~/.omnigent/agents/controller
# 日志应含：Starting omnigent server on 127.0.0.1:6767
```

**另开一个 WSL 终端验证：**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:6767
# 期望 200

omnigent-zh config list
ls ~/.omnigent/agents/controller/agents/
```

**Windows 浏览器：** `http://localhost:6767`
- 「智能体」区应有 **controller**（非第二个 "Claude Code"）
- 大脑 harness 必须是 `codex` / `claude-sdk` / `pi`（生成器已保证）

**失败分支：**

| 现象 | 处理 |
|------|------|
| 浏览器打不开 | `wsl --shutdown` 后重开 WSL + 再启 server |
| 无 controller | 是否用了 `server start` 而非 `--agent` 前台 |
| 子 agent 凭证错误 | 查 `OMNIGENT_RUNNER_ENV_PASSTHROUGH` + host daemon 是否也重启 |
| 子 agent 卡住 | runner 日志 `~/.omnigent/logs/runner/`；claude 工人应有 `permission_mode: auto` |

---

## 4. 风险与依赖清单

| 类别 | 项 | 影响 |
|------|----|------|
| 代理 | Clash `0.0.0.0:7897` + **防火墙按 WSL 网卡** | Codex/Kimi/x.ai OAuth 与国外 API；DeepSeek 直连通常不受影响 |
| Clash 服务 | `Get-Service *clash*` 得真实 Name | 勿写死服务名；示例 `clash_verge_service` |
| 防火墙 | WSL adapter alias → 已连接 IPv4 interface | **0 个或多个候选都停**；禁止静默取第一个或用 `RemoteIP=Any` 兜底 |
| 登录 | `codex login` / `kimi login` | 方案 A/B 验收依赖；**本机已完成** |
| Key | DeepSeek API key | 方案 B/C；**本机 Claude 壳已配** |
| PATH | `~/.kimi-code/bin` | 无则生成器不收录 kimi |
| 配置 | 手改 controller YAML | 技术债；被下次 gen 覆盖或与 prompt 池表不一致 |
| 启动方式 | 必须前台 `--agent` | 否则 Web UI 无 controller |
| 代理分流 | NO_PROXY 含 deepseek/moonshot | 国内 API 被代理劫持会超时 |
| 缺口 | Grok / `exec_xai`；8/8 业务验收 | 不挡运行面 1–8；挡完整 v1.1.0 阵容与闭环验收 |
| 文档债 | `omnigent-agentpeihe-deploy.md` §4.1 若仍写 kimi-native「不生成」 | **过时**；以 `gen_controller_bundle.py` 与 PITFALLS 为准 |

---

## 5. 建议执行顺序

### 本机（运行面已通，安全加固与业务验收未闭合）

```text
1. bash ../scripts/check_win10_wsl.sh（或 ~/agentcenter/.../check_win10_wsl.sh）→ 全绿
2. 待授权安全加固：防火墙绑定唯一的已连接 WSL IPv4 InterfaceAlias
3. 步骤 9：Web UI 8/8 业务验收（WINDOWS_HANDOFF.md §9）
4. 可选：装 Grok → gen → 重启 server → 池中出现 exec_xai
```

### 换机 / 从零（施工 agent）

```text
1. 主公：Clash allow-lan + 0.0.0.0:7897 + 防火墙（按 WSL 网卡，禁止 Any 兜底）
2. 主公：WSL 交互登录 codex（+ kimi）  → 验证: login status / credentials
3. （可选）主公提供 DEEPSEEK_API_KEY → 写 settings + 可选 gateway  → 验证: BASE_URL 含 deepseek
4. agent: dry-run gen → 确认 ≥2 vendor 工人（本机目标三工人）
5. agent: gen 落盘 → 检查 agents/ 与 tools
6. agent: tmux 内 server --agent → curl 200 + 浏览器见 controller
7. 步骤 9 验收任务
```

**红线提醒：** 不删文件、不改生产密钥文件除非主公已给 key 并确认；不手改 gen 产出 YAML；不跨机器复制凭据。
