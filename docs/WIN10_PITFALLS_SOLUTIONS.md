# Windows 10 部署踩坑与解决方案（全流程实录）

> **定位**：把 AgentCenter / omnigent + agentpeihe 从「Mac 文档能跑」落到「Windows 10 + WSL2 能跑」的现场经验。
> **对照**：官方仓库 [agentcenter](https://github.com/shankinchina-dotcom/agentcenter) 以 **macOS 原生 Unix/POSIX 语义 + tmux/PTY** 为主路径；`WINDOWS_HANDOFF.md` 给了 WSL 骨架，但 **Win10 NAT、Clash 服务模式、防火墙、Win/WSL 双 HOME 凭据** 等必须在本文补齐。
> **机器基线（2026-07-23 第二期）**：Windows 10 19045 · WSL2 Ubuntu 24.04 · Clash Verge Rev 1.19.x / mihomo · 目标版本 AgentCenter **v1.1.0** 通道隔离定版。

相关文档：

| 文档 | 用途 |
|------|------|
| `WINDOWS_HANDOFF.md` | 官方 WSL 逐步部署协议（偏理想路径） |
| `PITFALLS.md` | 全平台踩坑（含 Mac 一期 + Win 特供 12–20） |
| `WIN10_DEPLOY_PROGRESS.md` | 第二期进度与阻塞台账 |
| `STEPS_6_8_RUNBOOK.md` | provider / gen / server 可复制命令 |
| **本文** | **Win10 从 0 到可用的问题→解法总册** |

---

## 状态（拆开写，勿混为一谈）

| 面 | 状态 | 说明 |
|----|------|------|
| **文档** | 修订验证后 **可提 PR** | 本文与进度/RUNBOOK 为 Win 特有增量；修订后即可回灌仓库 |
| **部署运行面** | 步骤 **1–8 已通** | 代理三活 → CLI 登录/DeepSeek 壳 → `gen_controller_bundle` → `omnigent-zh server` 在 `http://localhost:6767` 返回 **200** |
| **最终验收** | **未完成** | 缺 **8/8** 业务验收清单（见 `WINDOWS_HANDOFF.md` §9）；**Grok / `exec_xai` 为可选缺口**，非最小验收硬依赖 |

---

## 0. 先记住：Mac 文档与 Windows 的本质差异

| 维度 | macOS（原仓库主路径） | Windows 10（本机实战） |
|------|----------------------|------------------------|
| 运行面 | **macOS 原生 Unix/POSIX 语义** + tmux/PTY | **必须进 WSL2 Ubuntu**，禁止 Windows 原生当主战场 |
| 网络 | `127.0.0.1` 即本机代理 | WSL **NAT**：`127.0.0.1` ≠ Windows；要用 **网关 IP** |
| mirrored 网络 | Win11 可试 | **Win10 无效**，别写 `.wslconfig` 空耗 |
| 代理软件 | 常是用户态 + 易开 LAN | Clash Verge **服务模式** + 三层 yaml + 可能需 **防火墙入站** |
| 凭据目录 | 单一 `~` | **Windows HOME 与 WSL HOME 两套**，登录互不自动共享 |
| `omnigent setup` | 终端向导可用 | Windows 原生会因 **`termios` 崩溃**；WSL 内用 Web/配置文件 |
| 大仓库安装 | 直连 git 常可 | 宜 **Windows clone → cp 进 `~/` → 本地 uv install** |
| 验收入口 | 本机浏览器 | Windows 浏览器打开 `http://localhost:6767`（WSL 端口转发） |

**硬规则（与版本无关）：**

1. 业务命令一律在 **WSL**，代码放 **Linux 文件系统**（`~/...`），禁止长期跑在 `/mnt/c/...`。
2. 通道隔离（v1.1.0）：丞相 **Codex**；DeepSeek **只走 Claude 壳**；Kimi **只走 kimi-native**；禁止 Kimi 占 Claude 壳。
3. Controller 必须用 **前台** `omnigent-zh server --no-open --agent ~/.omnigent/agents/controller` 注册；`server start` 后台模式 **不注册** agent。
4. 配置以 `gen_controller_bundle.py` 为唯一来源，**不手改**生成 YAML。

---

## 1. 今日时间线（问题是怎么叠出来的）

```text
[阶段 A] Windows 原生试装 omnigent
   → setup/termios 崩；native tmux/PTY 不可用
   → 结论：只能 WSL 或纯 Web/SDK

[阶段 B] 进 WSL，按 HANDOFF 配代理
   → Win10 mirrored 无效（NAT）
   → Clash allow-lan 文件 true、runtime 仍 127.0.0.1
   → 热修成 0.0.0.0 后 WSL 仍超时 → 防火墙

[阶段 C] 依赖 / omnigent / CLI 装齐
   → apt 源、大仓 clone、PATH、非交互 shell 坑

[阶段 D] 登录与通道
   → Codex 在 Windows 登成功，WSL 无 auth → 同机同步 auth.json
   → Kimi 必须在 WSL 交互 `kimi login`（device-code）
   → DeepSeek key → ~/.claude/settings.json + gateway + passthrough

[阶段 E] 生成 + 启动
   → gen：大脑 codex + exec_deepseek/openai/moonshot
   → tmux 前台 server，Windows 侧 :6767 = 200
```

---

## 2. 坑与解法总表（按排查顺序）

### 2.1 平台选型

#### 坑 W01：在 Windows 原生装 omnigent，期望 Mac 同款 CLI 矩阵

| | |
|--|--|
| **现象** | `omnigent-zh platform-info` 显示 `family=windows`、tmux/PTY 不可用；`omnigent-zh setup` 因 `termios` 崩溃 |
| **根因** | 原生 Windows 没有 Unix PTY/tmux 路径；setup 交互依赖 termios。Mac 侧是 **macOS 原生 Unix/POSIX 语义**，不能照搬到 Win 原生 |
| **解法** | **全部工作进 WSL2 Ubuntu**。Win 原生最多当「浏览器看 UI / 中转 git clone」 |
| **验证** | WSL 内：`omnigent-zh platform-info` → `family: linux`、`WSL2: 是`、`原生 tmux/PTY: 可用` |
| **避免** | 不要在 PowerShell 里把 `omni-zh claude/codex` 当主路径验收 |
| **旧编号** | 无 |

#### 坑 W02：WorkBuddy / 沙箱安全删除导致 `uv tool install` 构建失败（早期）

| | |
|--|--|
| **现象** | setuptools 清理临时目录：`SAFE_DELETE_FAIL_CLOSED` / `windows-sandbox-recycle-bin-unavailable` |
| **根因** | 沙箱把 `shutil.rmtree` 改成丢回收站；回收站不可用则构建中断 |
| **解法** | 构建前 `unset CODEBUDDY_SAFE_DELETE_SANDBOX`（或等价关闭该 env）；在干净 pwsh/WSL 重装 |
| **验证** | `uv tool list` 可见 `omnigent-zh-cn`；`omni-zh --version` 有输出 |
| **旧编号** | 无 |

---

### 2.2 网络与代理（Win10 头号死亡区）

#### 坑 W03：照文档开 `networkingMode=mirrored`（Win10）

| | |
|--|--|
| **现象** | 写了 `%UserProfile%\.wslconfig` 仍是 NAT（`172.x.x.x`、独立 eth0） |
| **根因** | mirrored 需要 **Windows 11 22H2+** |
| **解法** | **直接走 NAT**：代理写 `http://$(网关IP):端口`，不要写 `127.0.0.1` |
| **验证** | `ip route show default` 有默认网关；`ip addr` 为 172.x 段即 NAT |
| **避免** | 部署前 `winver`；Win10 跳过 mirrored 整节 |
| **旧编号** | #12 |

#### 坑 W04：WSL 里 `127.0.0.1:7897` 当代理

| | |
|--|--|
| **现象** | WSL curl 代理失败；Windows 本机代理却正常 |
| **根因** | WSL NAT 命名空间与 Windows localhost 隔离；对 Clash 而言 WSL 源 IP 是局域网侧 |
| **解法** | 使用 WSL 默认网关作为代理主机；命令见下方。写入 `~/.bashrc` 时建议仅在端口存活（`nc -z "$GW" 7897`）时 export |
| **验证** | `nc -zv -w 3 "$GW" 7897`；经代理访问 Google `generate_204` → **204** |
| **旧编号** | #13 |

```bash
GW=$(ip route show default | awk '{print $3; exit}')
export HTTPS_PROXY="http://$GW:7897" HTTP_PROXY="http://$GW:7897"
export NO_PROXY="api.deepseek.com,api.moonshot.cn,api.moonshot.ai,localhost,127.0.0.1,.local"
curl -x "http://$GW:7897" -o /dev/null -w '%{http_code}\n' \
  --connect-timeout 5 https://www.google.com/generate_204
```

#### 坑 W05：Clash 磁盘已是 `allow-lan: true`，仍只监听 `127.0.0.1`

| | |
|--|--|
| **现象** | `config.yaml` / `clash-verge.yaml` / Merge 都是 true，`netstat` 仍是 `127.0.0.1:7897` |
| **根因** | Clash Verge **三层配置**（基础模板 → profile 合并 → 运行配置）；**runtime** 可能未加载；订阅 profile 仍可能带 `allow-lan: false`；服务重启会从模板重建 runtime |
| **解法** | 1）三处都写 true：`config.yaml`、当前 Merge、`clash-verge.yaml`，并建议 `bind-address: "*"`<br>2）**热修（可无 UAC）**：对命名管道 `\\.\pipe\verge-mihomo` 发 `PATCH /configs`，body `{"allow-lan":true}`<br>3）或托盘「重启内核」/ **先发现再重启服务**（见下） |
| **服务发现与重启** | 禁止把服务名写成跨版本常量；先查实际服务名，再按发现到的 `Name` 重启，命令见下方 |
| **验证** | `netstat -ano \| findstr ":7897" \| findstr LISTEN` → **`0.0.0.0:7897`**（不是仅 127.0.0.1） |
| **避免** | 改完配置只信 **runtime / netstat**，别只信 UI 开关 |
| **旧编号** | #19 |

```powershell
Get-Service *clash*
# 本机证据仅作示例：Name=clash_verge_service；以当前机器输出为准
Restart-Service -Name <发现到的 Name> -Force
```

#### 坑 W06：已是 `0.0.0.0:7897`，WSL `nc` 仍超时（防火墙）

| | |
|--|--|
| **现象** | Windows `127.0.0.1:7897` 代理 204；WSL → 网关 IP:7897 TCP 超时 |
| **根因** | WSL 经 **vEthernet(WSL)** 访问宿主机端口属于 **入站**；防火墙默认拦截。`allow-lan` 只解决 mihomo 监听地址，**不**解决防火墙 |
| **解法** | 见下方 **§2.2.1 防火墙规则（推荐 + 兼容）**。核心原则：**优先绑定 WSL 网卡**；**查不到 WSL 接口就停止并提示，禁止自动退化成 `RemoteAddress=Any`** |
| **验证** | WSL：`nc` 成功 + 经代理 `generate_204=204` + 视需要 `github=200` |
| **避免** | 排障分层：① 本机 127.0.0.1 ② netstat 是否 0.0.0.0 ③ **防火墙** ④ bashrc 网关 IP |
| **旧编号** | #20 |

##### 2.2.1 防火墙规则（管理员 pwsh）

**步骤 1：动态查找 WSL 网卡（必须先做）**

```powershell
# 先取得名称/描述含 WSL 的适配器别名
$wslAliases = @(Get-NetAdapter -IncludeHidden |
  Where-Object {
    $_.Name -like '*WSL*' -or
    $_.InterfaceDescription -like '*WSL*'
  } |
  Select-Object -ExpandProperty Name -Unique)

# 再限定为已连接、实际承载 IPv4 的接口，排除 vSwitch 等同名候选
$wslIPv4 = @(Get-NetIPInterface -AddressFamily IPv4 |
  Where-Object {
    $_.InterfaceAlias -in $wslAliases -and
    $_.ConnectionState -eq 'Connected'
  })

$wslIPv4 | Format-Table InterfaceAlias, InterfaceIndex, ConnectionState -AutoSize
if ($wslIPv4.Count -ne 1) {
  throw "已连接的 WSL IPv4 接口数量为 $($wslIPv4.Count)，必须人工确认且只能选中一个；禁止退化成 RemoteAddress=Any"
}

$ifAlias = $wslIPv4[0].InterfaceAlias
Write-Host "将使用 InterfaceAlias = $ifAlias"
```

**步骤 2（推荐）：按 InterfaceAlias 绑定 WSL 适配器**

```powershell
# $ifAlias 来自步骤 1；端口按本机 Clash mixed-port 改（示例 7897）
$ruleName = 'ClashVerge-LAN-7897-WSL'

if (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue) {
  Remove-NetFirewallRule -Name $ruleName
}

New-NetFirewallRule -DisplayName 'Clash Verge LAN 7897 (WSL iface)' `
  -Name $ruleName `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7897 `
  -InterfaceAlias $ifAlias `
  -Profile Any -EdgeTraversalPolicy Block
```

**步骤 3（兼容方案）：按 WSL 子网限制 RemoteAddress**

> 仅在「InterfaceAlias 绑定因驱动/别名异常无效」时使用。
> **注意**：`wsl --shutdown` / 重启后 **WSL 网段可能变化**，规则会失效，**必须复检** `ip route` / `ip addr` 后再改 RemoteAddress。

```powershell
# 在 WSL 内取网段示例（勿写死某次会话的 172.30.x.x）：
#   ip -4 addr show eth0   → 如 172.30.191.135/20
# 再在管理员 pwsh 里（把 <WSL_CIDR> 换成当次实测，如 172.30.176.0/20）：

$ruleName = 'ClashVerge-LAN-7897-WSL-Subnet'
if (Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue) {
  Remove-NetFirewallRule -Name $ruleName
}

New-NetFirewallRule -DisplayName 'Clash Verge LAN 7897 (WSL subnet)' `
  -Name $ruleName `
  -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7897 `
  -RemoteAddress <WSL_CIDR> `
  -Profile Any -EdgeTraversalPolicy Block
```

**禁止**：查不到 WSL 接口时，**不要**写 `-RemoteAddress Any` 或省略远程范围「先通再说」。那是扩大攻击面，不是兼容方案。

**回滚**：

```powershell
Remove-NetFirewallRule -Name 'ClashVerge-LAN-7897-WSL' -ErrorAction SilentlyContinue
Remove-NetFirewallRule -Name 'ClashVerge-LAN-7897-WSL-Subnet' -ErrorAction SilentlyContinue
```

**审计片段（可随时复跑，不替代 WSL 自检脚本）**：

```powershell
Write-Host '=== WSL adapters ==='
Get-NetAdapter -IncludeHidden |
  Where-Object { $_.Name -like '*WSL*' -or $_.InterfaceAlias -like '*WSL*' } |
  Format-Table Name, InterfaceAlias, Status, ifIndex -AutoSize

Write-Host '=== Clash-related firewall rules ==='
Get-NetFirewallRule -ErrorAction SilentlyContinue |
  Where-Object { $_.DisplayName -match 'Clash|WSL|7897' -or $_.Name -match 'Clash|WSL|7897' } |
  Format-Table Name, DisplayName, Enabled, Direction, Action

Write-Host '=== Listen on 7897 ==='
netstat -ano | findstr ':7897' | findstr 'LISTEN'
# 期望含 0.0.0.0:7897（或 [::]:7897），不是仅 127.0.0.1:7897
```

#### 坑 W07：国内外 API 一刀切代理

| | |
|--|--|
| **现象** | DeepSeek/Moonshot 变慢或断；国外站不通 |
| **根因** | 国内 API 不应走代理；国外必须走 |
| **解法** | `HTTPS_PROXY` + `NO_PROXY=api.deepseek.com,api.moonshot.cn,api.moonshot.ai,localhost,127.0.0.1`（NAT 下 PROXY 主机用网关 IP，见 W04） |
| **验证** | 直连 deepseek/moonshot 返回 **401** 即通路正常（无 key 时） |
| **旧编号** | #10 |

#### 坑 W08：x.ai / Grok DNS 污染

| | |
|--|--|
| **现象** | `x.ai` 解析到 Meta IP；Grok 装不上、exec_xai 进不了池 |
| **根因** | 国内 DNS 污染 + 订阅规则未覆盖 x.ai |
| **解法** | Clash Merge `prepend-rules: - "DOMAIN-SUFFIX,x.ai,<策略组>"`；代理通后再装 Grok CLI |
| **验证** | 经代理访问 x.ai 相关端点非 DNS 错（常见 401/403 也算通路） |
| **避免** | v1.1.0 完整阵容含 Grok，但 **最小验收可用 Codex+DeepSeek+Kimi 三 vendor**；**Grok/`exec_xai` 为可选缺口**，可后补 |
| **旧编号** | #16 |

---

### 2.3 系统依赖与安装

#### 坑 W09：WSL apt 官方源超时

| | |
|--|--|
| **解法** | Ubuntu 24.04 换阿里云（DEB822：`/etc/apt/sources.list.d/ubuntu.sources`） |
| **避免** | 装完 WSL **第一件事换源** |
| **旧编号** | #14 |

#### 坑 W10：在 WSL 内 `git clone` / `uv tool install git+https` 大仓卡死

| | |
|--|--|
| **现象** | agentcenter / omnigent-zh-cn（~1.2GB）fetch 挂起 |
| **解法** | Windows：`git clone --depth 1`（走系统代理）→ `wsl -- cp -r /mnt/c/Users/<你>/... ~/` → `uv tool install --force --python 3.12 ~/omnigent-zh-cn` |
| **验证** | 仓库在 `~/`（非 `/mnt/c`）；`omnigent-zh --version` 正常 |
| **旧编号** | #15 |

#### 坑 W11：非交互 `wsl` 会话 PATH 缺 `~/.local/bin` / kimi

| | |
|--|--|
| **现象** | agent 脚本里 `uv`/`omnigent-zh`/`kimi` command not found；交互终端却有 |
| **根因** | 非 login/non-interactive 不 source `~/.bashrc`；kimi 在 `~/.kimi-code/bin` |
| **解法** | 脚本开头显式 `export PATH="$HOME/.local/bin:$HOME/.kimi-code/bin:$PATH"`；需持久化时写入 `~/.profile` |
| **验证** | 用非交互 shell 验证：`bash -c 'command -v uv omnigent-zh kimi'` |
| **避免** | 不把 `bash -lc` 当 PATH 修复；生成器 `shutil.which("kimi")` 依赖启动进程实际收到的 PATH |
| **旧编号** | 无 |

#### 坑 W12：从 PowerShell 调 `wsl bash -c` 引号/括号被吞

| | |
|--|--|
| **现象** | `awk`/`$()` 被 PowerShell 解析；命令语法错误 |
| **解法** | **写临时 `.sh` 再** `wsl -d Ubuntu -- bash /mnt/c/.../script.sh`（脚本本身注意 W21 CRLF） |
| **避免** | 复杂逻辑不要单行嵌在 `wsl -- bash -c "..."` |
| **旧编号** | 无 |

#### 坑 W13：WSL 输出乱码 / sudo 非交互挂起

| | |
|--|--|
| **乱码** | 从 Windows 调 `wsl` 时输出经控制台可能变 UTF-16LE → 管道清理或重定向写文件再读（旧 #17） |
| **sudo 挂起** | 非交互 `wsl -- bash -c 'sudo ...'` 会等密码，命令永远挂起（旧 #18） |
| **解法（sudo）** | **不要**在文档/脚本里写 `echo <密码> \| sudo -S`（密码进管道、进日志、进历史，风险高）。可选：<br>1）**交互终端先** `sudo -v` 刷新票据，再跑短时需要提权的命令；<br>2）对可接受的机器配置 **NOPASSWD**（自行权衡安全边界，`sudo visudo`）；<br>3）**主公在交互终端**亲自执行 `sudo apt-get ...` 等提权步骤 |
| **避免** | 自动化默认假设已具备 sudo 票据或 NOPASSWD；agent 不要替用户在命令行塞密码 |
| **旧编号** | #17 + #18 |

---

### 2.4 登录与通道（v1.1.0 定版）

#### 坑 W14：Codex 显示 “Signed in”，WSL 里仍未登录

| | |
|--|--|
| **现象** | 浏览器已授权；WSL `~/.codex` 只有 sqlite/tmp，无 `auth.json` |
| **根因** | 登录发生在 **Windows** `C:\Users\<你>\.codex\`，与 **WSL** `~/.codex` 分离 |
| **解法** | 优先在 **WSL 交互终端** 再跑一次 `codex login`；应急时仅做同机同步（**不要跨机器拷贝**），命令见下方 |
| **验证** | `codex login status` 必须成功退出并明确显示 `Logged in using ChatGPT` 或 API key 登录成功文案；`omnigent-zh config list` 见 Codex subscription ✓ |
| **旧编号** | 无（Win 双 HOME 特供） |

```bash
mkdir -p ~/.codex
cp -f /mnt/c/Users/<你>/.codex/auth.json ~/.codex/auth.json
chmod 600 ~/.codex/auth.json
# 可选同步 config.toml
codex login status   # 预期：Logged in using ChatGPT
```

#### 坑 W15：Kimi 登录姿势

| | |
|--|--|
| **命令** | WSL：`export PATH="$HOME/.kimi-code/bin:$PATH"` → `kimi login` |
| **流程** | device-code：终端给 URL + 用户码 → 浏览器授权 → `Logged in to managed:kimi-code` |
| **验证** | 存在 `~/.kimi-code/credentials/`；生成器 dry-run 出现 `exec_moonshot` |
| **红线** | **禁止** 用 CC Switch 把 Claude 指到 Kimi；Kimi 只走 **kimi-native**（omnigent 默认 `--yolo`） |
| **不要混** | 嵌入 TUI 的「Send /login to login」是 **进程内 session**（斜杠 `/login`），不是这条 CLI 掉了。CLI 已 Logged in 就不要再跑 `kimi login`。见 monorepo PITFALLS **坑 24** |
| **旧编号** | #5 |

#### 坑 W16：DeepSeek 只 export 环境变量，生成器仍 vendor=unknown

| | |
|--|--|
| **现象** | 有 `DEEPSEEK_API_KEY` 但 dry-run 无 `exec_deepseek`；或 pi 路径 key 解析失败 |
| **根因** | ① 生成器嗅探的是 `~/.claude/settings.json` 的 `ANTHROPIC_BASE_URL`，不是只看 env；② pi 的 `model` 必须在顶层 `executor.model` 且 `auth.provider` 绑定；③ host 转发 runner 时默认白名单**没有** `DEEPSEEK_API_KEY`，需 `OMNIGENT_RUNNER_ENV_PASSTHROUGH` |
| **解法** | 配置 `~/.claude/settings.json`（示例见下方）；gateway 备用路径另需 runner 环境透传。改完后重启 host daemon + server |
| **验证** | `ANTHROPIC_BASE_URL` 规范化后必须等于 `https://api.deepseek.com/anthropic`；生成器 dry-run 显示实际 vendor 为 deepseek，且 `exec_deepseek` 为 `claude-native` + `permission_mode: auto` |
| **旧编号** | #7 + #8 + #9 |

```json
{
  "env": {
    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
    "ANTHROPIC_API_KEY": "<key>",
    "ANTHROPIC_MODEL": "deepseek-v4-flash-vision-exp[1M]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "deepseek-v4-flash-vision-exp[1M]",
    "ANTHROPIC_DEFAULT_FABLE_MODEL": "deepseek-v4-flash-vision-exp[1M]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-flash-vision-exp[1M]",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-flash-vision-exp[1M]"
  }
}
```

- **默认模型**：`deepseek-v4-flash-vision-exp`（2026-09-09 起，支持图片输入；pi 直连备选稳定版 `deepseek-v4-flash`）
- **默认上下文 1M**：模型 id **必须**带 `[1M]`；只写 `deepseek-v4-flash-vision-exp` 时 TUI 常显示 **200k Ctx**（见 monorepo PITFALLS 坑 21）
- 改 settings 后 **新开** `exec_deepseek` / claude-native 会话

若配置 deepseek gateway 备用路径，再执行：

```bash
export OMNIGENT_RUNNER_ENV_PASSTHROUGH=DEEPSEEK_API_KEY
```

#### 坑 W17：CLI 名字 ≠ 真实 vendor

| | |
|--|--|
| **现象** | 以为 Reviewer 是 Claude，实际是 DeepSeek |
| **解法** | vendor **只看** `ANTHROPIC_BASE_URL` / 实际后端；异 vendor 规则按后端判定 |
| **旧编号** | #9 |

---

### 2.5 生成 bundle 与启动 server

#### 坑 W18：Web UI 没有 controller

| | |
|--|--|
| **根因** | agents 落盘 ≠ server 注册表；`server start` 不带 `--agent` |
| **解法** | 在 tmux 中以前台 `--agent` 方式注册 controller；命令见下方 |
| **验证** | `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:6767` → 200；Windows 浏览器 `http://localhost:6767` 智能体区见 **controller** |
| **避免** | 改 bundle 后 **必须重启** server（启动快照） |
| **旧编号** | #1 |

```bash
omnigent-zh server stop 2>/dev/null
tmux new -A -s omnigent
export PATH="$HOME/.local/bin:$HOME/.kimi-code/bin:$PATH"
export DEEPSEEK_API_KEY=...   # 若用 deepseek gateway；勿把 key 写进 git/聊天
export OMNIGENT_RUNNER_ENV_PASSTHROUGH=DEEPSEEK_API_KEY
omnigent-zh server --no-open --agent ~/.omnigent/agents/controller
```

#### 坑 W19：controller 显示成第二个 “Claude Code”

| | |
|--|--|
| **根因** | 大脑用了 native harness，UI 按 harness 品牌归类 |
| **解法** | 大脑用 **codex / claude-sdk / pi**（生成器默认 codex）；工人用 native |
| **旧编号** | #2 |

#### 坑 W20：子 agent 卡住像死机

| | |
|--|--|
| **claude-native** | 缺 `permission_mode: auto` → 审批弹窗无人点（生成器已配）（#4） |
| **kimi-native** | omnigent 默认 `--yolo`；Host PATH 须含 kimi bin（#5） |
| **codex-native TUI** | 易超时 → 工人用 **headless `harness: codex`**（v1.1.0 已定）（#11） |
| **凭证** | runner 报 key 解析失败 → 查 `OMNIGENT_RUNNER_ENV_PASSTHROUGH` 并 **重启 host+server** |
| **旧编号** | #4 + #5 + #11 |

#### 坑 W21：PowerShell 写 bash 脚本带 CRLF

| | |
|--|--|
| **现象** | `ls .../agents/$'\r'`、here-doc 异常、`bash\r: bad interpreter` |
| **根因** | Windows 行尾 `\r\n`；**`Set-Content -Encoding utf8NoBOM` 只解决编码，不解决 CRLF** |
| **解法** | 在 WSL 内：`sed -i 's/\r$//' script.sh` 或 `dos2unix script.sh`。PowerShell 写文件后**默认再跑一遍**去 `\r` |
| **避免** | 尽量在 WSL 里用 `cat > script.sh <<'EOF'` 写脚本；路径拼接避免 Windows 行尾污染 |
| **旧编号** | 无 |

---

## 3. 推荐部署顺序（Win10 实战版，可当 checklist）

按这个顺序可少走 80% 弯路：

1. **确认 Win10 + WSL2 Ubuntu 24.04**（跳过 mirrored）
2. **Clash**：allow-lan 落盘 + runtime `0.0.0.0:端口`（`Get-Service *clash*` 后按实际 Name 重启/热修）+ **防火墙入站绑定 WSL 网卡**（§2.2.1）+ WSL 网关代理三活
3. **WSL 换 apt 源** → 装 tmux/bwrap/git/gh/curl、uv、Node 22+（sudo 用交互 `sudo -v` / 主公终端 / NOPASSWD，见 W13）
4. **Windows 浅克隆** agentcenter / omnigent → **cp 到 `~/`** → `uv tool install` 本地路径
5. 装 CLI：claude / codex / pi / kimi（PATH 含 `~/.kimi-code/bin`）
6. **在 WSL** 登录：`codex login`、`kimi login`；DeepSeek 写 `~/.claude/settings.json`
7. `python3 ~/agentcenter/agentpeihe/gen_controller_bundle.py`（先 `--dry-run`）
8. tmux 前台 `omnigent-zh server --no-open --agent ~/.omnigent/agents/controller`
9. Windows 浏览器验收 8 项（见 `WINDOWS_HANDOFF.md` §9）——**当前未闭合**
10. （可选）代理规则 + 装 Grok → 重跑 gen 得 `exec_xai`——**可选缺口**

---

## 4. 自检

### 4.1 WSL 端到端（唯一脚本入口）

在 **WSL** 执行：

```bash
bash ~/agentcenter/agentpeihe/scripts/check_win10_wsl.sh
# 若仓库在工作副本路径，按实际调整：
# bash /path/to/agentpeihe/scripts/check_win10_wsl.sh
```

脚本职责（**只做 WSL 侧**）：网关、代理 TCP/HTTP、国内直连、PATH、登录、Claude 壳、现有 bundle、`:6767` UI。
**不做** Windows 防火墙规则创建/审计——那在 PowerShell 侧（§2.2.1 审计片段）。

### 4.2 Windows 侧辅助（手动）

```powershell
# 监听与本机代理
netstat -ano | findstr ":7897" | findstr "LISTEN"
# 期望含 0.0.0.0:7897
curl.exe -x http://127.0.0.1:7897 -sS -o NUL -w "%{http_code}" --connect-timeout 5 https://www.google.com/generate_204

# 防火墙审计见 §2.2.1
```

---

## 5. 本机运行面快照（2026-07-23 · 步骤 1–8 已通）

| 项 | 状态 |
|----|------|
| WSL 代理 | 网关 IP:7897（**勿写死某次会话网段**），nc 通，proxy 204 |
| Clash | 监听 `0.0.0.0:7897`；运行面已通，当前宽防火墙规则仍待按 §2.2.1 绑定 WSL IPv4 接口收紧 |
| Codex | WSL `Logged in using ChatGPT` |
| Kimi | `Logged in to managed:kimi-code` |
| DeepSeek | Claude 壳 BASE_URL 已指向 `api.deepseek.com/anthropic` |
| Bundle | 大脑 `codex`；工人 `exec_deepseek` / `exec_openai` / `exec_moonshot` |
| Server | tmux 会话 `omnigent`；Windows `http://localhost:6767` → **200** |
| **文档** | 修订验证后 **可提 PR** |
| **部署运行面** | 步骤 **1–8 已通** |
| **最终验收** | **未完成**（缺 8/8）；**Grok/`exec_xai` 可选缺口** |

---

## 6. 给后续 Agent / 主公的元教训

1. **先网络后软件**：Win10 上 70% 时间死在 NAT + allow-lan + 防火墙，不要先折腾 bundle。
2. **分层验证**：本机代理通 ≠ WSL 通；yaml true ≠ runtime true；CLI 在 PATH ≠ 已登录。
3. **双 HOME 意识**：Windows 登录成功只算一半；以 **WSL `codex login status` / kimi credentials** 为准。
4. **Mac 文档是目标态，不是步骤态**：HANDOFF 的 mirrored、简单 127.0.0.1 代理在 Win10 上直接替换为本文 W03–W06。Mac 主路径是 **macOS 原生 Unix/POSIX 语义**，不是「原生 Linux」。
5. **防火墙先收窄再兼容**：优先 `InterfaceAlias` 绑 WSL 网卡；查不到就停；子网方案要写明 **重启后网段可能变、需复检**；禁止默默 `RemoteAddress=Any`。
6. **服务名先发现再操作**：`Get-Service *clash*`，再用实际 Name；不要把 `clash_verge_service` 当跨版本常量。
7. **配置生成化**：换模型/换机器只重跑生成器；手改 YAML 是技术债。
8. **密钥**：不写进文档、不写进 git、不贴聊天全文；写入 `settings.json` / 环境后轮换曾泄露过的 key。

---

## 7. 索引：本文坑号 ↔ 旧文档（完整映射）

| 本文 | `PITFALLS.md` / 其它 |
|------|----------------------|
| W01 | 无旧编号 |
| W02 | 无旧编号 |
| W03 | #12 |
| W04 | #13 |
| W05 | #19 |
| W06 | #20 |
| W07 | #10 |
| W08 | #16 |
| W09 | #14 |
| W10 | #15 |
| W11 | 无旧编号 |
| W12 | 无旧编号 |
| W13 | #17 + #18 |
| W14 | 无旧编号 |
| W15 | #5 |
| W16 | #7 + #8 + #9 |
| W17 | #9 |
| W18 | #1 |
| W19 | #2 |
| W20 | #4 + #5 + #11 |
| W21 | 无旧编号 |

---

*文档定稿：2026-07-23 · Windows 10 第二期 · 修订后可提 PR · 运行面 1–8 已通 · 最终 8/8 验收与 Grok 可选补完待续。*
