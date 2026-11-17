# Windows 10 部署进度（第二期）

> 机器：Windows 10 19045 / WSL2 Ubuntu 24.04 / Clash Verge v1.19.x Mihomo
> 执行日期：2026-07-23
> 执行者：多 agent 并行
> 最后更新：2026-07-23（**运行面快照**，非 01:30 阻塞态）

---

## 状态三拆（结论先行）

| 面 | 状态 | 说明 |
|----|------|------|
| **文档** | 可提 PR | 本文 + `STEPS_6_8_RUNBOOK.md` + `WIN10_PITFALLS_SOLUTIONS.md` 已对齐终态 |
| **运行面** | **步骤 1–8 已通** | 代理 / 登录 / bundle / server `:6767=200` |
| **验收** | **未完成** | 8/8 业务验收未做；无 Grok CLI / `exec_xai` |

---

## 已完成（运行面步骤 1–8）

| 步骤 | 状态 | 备注 |
|------|------|------|
| 1. WSL2 确认 | **PASS** | Ubuntu 24.04, VERSION=2，NAT（非 mirrored） |
| 2. 网络与代理 | **PASS** | Clash `0.0.0.0:7897`；WSL `nc` 通、`generate_204=204`、`github=200` |
| 3. 依赖安装 | **PASS** | python3 3.12.3, node 22.x, uv, tmux, gh, bwrap |
| 4. omnigent 安装 | **PASS** | linux / WSL2=是 / tmux·PTY 可用 |
| 5. CLI 安装 | **PASS** | claude / codex / pi / kimi 在 PATH（kimi 需 `~/.kimi-code/bin`） |
| 6. 登录与 Claude 壳 | **PASS** | Codex WSL `Logged in using ChatGPT`；Kimi credentials 存在；DeepSeek 壳已配 |
| 7. controller bundle | **PASS** | 大脑 `codex`；工人见下表 |
| 8. 启动 server | **PASS** | tmux 会话 `omnigent`；`:6767` → **200** |
| 9. 业务验收 8/8 | **未做** | 见后续缺口 |

### Bundle 终态

| 角色 | 标识 | 备注 |
|------|------|------|
| 大脑 | `codex` | harness=codex |
| 工人 | `exec_deepseek` | Claude 壳，`BASE_URL=https://api.deepseek.com/anthropic` |
| 工人 | `exec_openai` | codex headless，`gpt-5.6-sol` |
| 工人 | `exec_moonshot` | kimi-native |
| 缺 | `exec_xai` | 无 Grok CLI，未入池 |

### 代理 / 防火墙现状

| 项 | 状态 |
|----|------|
| Clash 监听 | `0.0.0.0:7897`（mixed-port） |
| 网关 IP | 示例 `172.30.176.1`（**以 WSL `ip route` 默认网关为准**，NAT 段会变） |
| WSL 探针 | `nc` 通；经代理 `generate_204=204`；`github=200` |
| 防火墙 | 当前实测规则为 `RemoteIP=Any`、全 Profile/Interface；运行面已通，但**仍待绑定唯一的已连接 WSL IPv4 接口收紧** |

---

## 已解除的历史阻塞（勿再当当前阻塞）

以下曾在 **2026-07-23 01:30** 阻塞，**现已解除**，仅作时间线备忘：

| 旧阻塞 | 当时现象 | 终态 |
|--------|----------|------|
| A' 防火墙拦 WSL→7897 | WSL `nc` 超时 | 规则已加 + WSL 代理三活 |
| B CLI 未登录 | codex/kimi 未登录 | Codex / Kimi 已就绪 |
| DeepSeek 壳 | 无 settings | `ANTHROPIC_BASE_URL` 已指向 deepseek anthropic |

---

## 仍开放缺口

1. **Grok CLI / `exec_xai`**：未装、未入池；非最小运行硬依赖，补齐后重跑 `gen_controller_bundle.py`。
2. **8/8 业务验收**：Web UI 向 controller 发任务（拆关卡 → 异 vendor 互审 → 汇总）**未闭合**。
3. **防火墙范围收紧**：当前规则已确认过宽；应绑定**唯一的已连接 WSL IPv4 接口**，**禁止** `RemoteIP=Any` 兜底。

---

## 运维要点（硬约束）

### Clash 服务名

服务名**勿写死**。先查再操作：

```powershell
Get-Service *clash*
# 示例 Name：clash_verge_service（以本机输出为准）
# Restart-Service <实际 Name>
```

### 防火墙：按 WSL 网卡收紧（推荐）

```powershell
# 1) 先取 WSL 适配器别名，再筛选已连接、承载 IPv4 的接口
$wslAliases = @(Get-NetAdapter -IncludeHidden |
  Where-Object { $_.Name -match 'WSL' -or $_.InterfaceDescription -match 'WSL' } |
  Select-Object -ExpandProperty Name -Unique)
$wslIPv4 = @(Get-NetIPInterface -AddressFamily IPv4 |
  Where-Object { $_.InterfaceAlias -in $wslAliases -and $_.ConnectionState -eq 'Connected' })
$wslIPv4 | Format-Table InterfaceAlias, InterfaceIndex, ConnectionState
if ($wslIPv4.Count -ne 1) { throw '必须人工确认且只能选中一个 WSL IPv4 接口；禁止 RemoteIP=Any 兜底' }
$ifAlias = $wslIPv4[0].InterfaceAlias

# 2) 收紧示例（端口按本机 mixed-port）
# New-NetFirewallRule ... -InterfaceAlias $ifAlias ...
```

**禁止**：找不到 WSL 接口时用 `RemoteIP=Any` 或全局放开当兜底。
细则与坑号见 `WIN10_PITFALLS_SOLUTIONS.md`（W05/W06）。

### 一键自检

WSL：

```bash
bash ~/agentcenter/agentpeihe/scripts/check_win10_wsl.sh
# 仓库相对路径：../scripts/check_win10_wsl.sh（相对本文件所在 docs/）
```

---

## 后续（业务验收、安全加固与可选补全）

| 序号 | 动作 | 预期 |
|------|------|------|
| 9 | Web UI 业务验收（`WINDOWS_HANDOFF.md` §9 清单） | 8/8 过 |
| 待加固 | 防火墙绑定唯一的已连接 WSL IPv4 InterfaceAlias | 仅 WSL 接口入站 7897 |
| 可选 | 代理规则 + 装 Grok CLI → 重跑 gen | 池中出现 `exec_xai` |

命令细节：`STEPS_6_8_RUNBOOK.md`。
踩坑总册：`WIN10_PITFALLS_SOLUTIONS.md`。

---

## 环境快照（运行面步骤 1–8）

```
# WSL 内
python3 / node / uv / tmux / gh / bwrap：已装
omnigent-zh：platform-info PASS（linux + WSL2 + tmux/PTY）
codex：Logged in using ChatGPT
kimi：credentials 存在（~/.kimi-code/credentials/…）
claude 壳：ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
controller：~/.omnigent/agents/controller/
  工人：exec_deepseek, exec_openai (gpt-5.6-sol), exec_moonshot
server：tmux session omnigent；127.0.0.1:6767 → 200
网关：示例 172.30.176.1（以 ip route 为准）
代理：条件式 HTTPS_PROXY → 网关:7897；nc / 204 / github 均通
~/agentcenter + ~/omnigent-zh-cn：在 Linux FS

# Windows 侧
Clash Verge：mixed-port 7897，LISTEN 0.0.0.0:7897
防火墙：WSL→7897 已放行；当前规则为 Any，仍待绑定唯一的已连接 WSL IPv4 接口
浏览器：http://localhost:6767 可达
仓库工作副本：本机 agentcenter / duoagents 工作区（勿写死完整用户路径）
```

---

## 关键文件位置

| 文件 | 路径 | 用途 |
|------|------|------|
| 步骤 6–8 RUNBOOK | `agentpeihe/docs/STEPS_6_8_RUNBOOK.md` | 登录/gen/server 可复制命令（已完成后可跳过，换机重做） |
| Win10 踩坑总册 | `agentpeihe/docs/WIN10_PITFALLS_SOLUTIONS.md` | 问题→解法全流程 |
| WSL 自检脚本 | `agentpeihe/scripts/check_win10_wsl.sh` | 代理/登录/bundle/UI 探针 |
| Clash 基础模板 | `%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\config.yaml` | allow-lan 根 |
| Clash 运行配置 | 同上 `clash-verge.yaml` | mihomo 实际加载 |
| 生成器 | `~/agentcenter/agentpeihe/gen_controller_bundle.py` | **唯一**配置来源 |
| 交接/全平台坑 | `WINDOWS_HANDOFF.md` / `PITFALLS.md` | 部署协议与跨平台坑 |
