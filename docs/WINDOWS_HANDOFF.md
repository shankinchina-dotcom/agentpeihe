# Omnigent + agentpeihe：Windows 部署交接文档（G6）

> **给谁看**：Windows 机器上的执行 agent（你没见过本项目的 Mac 侧，也不需要见过——本文自包含）。
> **怎么协作**：你（Windows 侧 agent）逐步执行 → 每步把输出交给主公（人类）→ 主公带回给 Controller（Mac 侧）审查。遇到与"预期输出"不符，**停下来把实际输出原样回报**，不要自己硬闯。
> **最终验收**：Windows 浏览器打开 `http://localhost:6767`，向 controller 发一个任务，它自动拆关卡 → 派 Executor → 异 vendor Reviewer 核验 → 汇总，全程无人复制粘贴。

---

## 0. 开始前必读（三分钟）

1. 所有工作都在 **WSL2（Ubuntu）里**进行，除非特别标注"PowerShell"。不要在 Windows 原生环境装 omnigent（跑不了 native CLI）。
2. 仓库/代码必须放在 **Linux 文件系统**（`~/...`），**禁止** `/mnt/c/...`（跨文件系统权限和性能都是坑）。
3. **代理是头号坑**：WSL2 里的 `127.0.0.1` ≠ Windows 的 `127.0.0.1`。第 2 步专门处理，别跳。
4. 本文每一步都有「预期输出」和「失败分支」。照做即可，不用理解原理；想知道为什么，读 `agentpeihe/docs/PITFALLS.md`。
5. 凭据各归各：不要把 Mac 上的任何登录态/凭据复制过来，每个 CLI 在本机独立登录。

---

## 1. 确认/安装 WSL2（PowerShell）

```powershell
wsl --status
wsl -l -v
```

- **预期**：已有 Ubuntu 且 VERSION 为 2 → 跳到第 2 步。
- **失败分支**：没有 WSL → `wsl --install -d Ubuntu-24.04`，装完重启电脑，设好 Linux 用户名密码后回来。

**以下全部在 WSL2 终端（Ubuntu）里执行。**

---

## 2. 网络与代理（最容易死的一步，先干这个）

### 2.1 推荐：mirrored 网络模式（WSL 共享 Windows 的 localhost）

在 **Windows 用户目录**（`C:\Users\<你>\`）新建/编辑 `.wslconfig`：

```ini
[wsl2]
networkingMode=mirrored
```

PowerShell 执行 `wsl --shutdown`，重开 Ubuntu。

- **预期**：WSL 里 `curl -s http://127.0.0.1:<Windows代理端口> ` 能通（代理在 Windows 上跑，WSL 也能用 127.0.0.1 访问它）。
- **失败分支**：mirrored 模式异常（老 Windows 版本不支持）→ 退回 NAT 模式：删掉 `.wslconfig` 那段，WSL 里用 `ip route show default | awk '{print $3}'` 取宿主机 IP 当代理地址，且 Windows 代理软件必须开"允许局域网连接"。

### 2.2 确认代理端口（Windows 侧）

问主公：Windows 上跑的是什么代理软件（Clash Verge / v2rayN / 其他），端口多少。把它记为 `<PROXY>`，形如 `http://127.0.0.1:7890`。

### 2.3 WSL 内配置代理环境变量（写进 `~/.bashrc`）

```bash
# 仅当代理端口活着才挂代理（代理软件关了不影响国内直连）
if nc -z 127.0.0.1 <端口> 2>/dev/null; then
  export HTTPS_PROXY="<PROXY>" HTTP_PROXY="<PROXY>"
  # 国内 API 直连白名单：不配代理的厂商都列进来
  export NO_PROXY="api.deepseek.com,api.moonshot.cn,api.moonshot.ai,localhost,127.0.0.1,.local"
  export no_proxy="$NO_PROXY"
fi
```

- **验证**（三活）：`curl -s -o /dev/null -w "%{http_code}\n" https://api.deepseek.com/v1/models`（直连，401 即通）、`curl -s -o /dev/null -w "%{http_code}\n" https://api.x.ai/v1/models`（走代理，401/403 即通）、`curl -s -o /dev/null -w "%{http_code}\n" https://api.moonshot.cn/v1/models`（直连，401 即通）。
- **失败分支**：国外域名不通 → 检查 mirrored/NAT 设置与代理软件"允许局域网连接"；国内域名不通 → 检查 NO_PROXY 是否生效（`env | grep -i proxy`）。

---

## 3. WSL2 内安装依赖

```bash
sudo apt-get update
sudo apt-get install -y tmux bubblewrap git gh curl
curl -LsSf https://astral.sh/uv/install.sh | sh && source ~/.profile
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt-get install -y nodejs
```

- **预期**：`python3 --version`（≥3.12，不够就 `uv python install 3.12`）、`node --version`（≥22）、`uv --version`、`tmux -V` 全有输出。
- **失败分支**： nodesource 脚本被墙 → 换 `sudo apt-get install -y nodejs npm` + `sudo npm i -g n && sudo n 22`。

## 4. 安装 omnigent 并验证平台

```bash
uv tool install --force --python 3.12 "git+https://github.com/shankinchina-dotcom/omnigent-zh-cn.git"
source ~/.profile   # 让 ~/.local/bin 进 PATH
omnigent-zh platform-info
```

- **预期输出必须同时满足**：`family: linux`、`WSL2: 是`、`原生 tmux/PTY: 可用`。
- **失败分支**：`omnigent-zh: command not found` → `source ~/.profile`；安装时 npm 构建失败 → 检查 Node ≥22 后 `uv tool install --force` 重跑；GitHub 拉不下来 → 配 git 代理 `git config --global http.proxy <PROXY>`。

## 5. 安装并登录各家 CLI（有多少装多少，至少两家不同 vendor）

```bash
npm install -g @anthropic-ai/claude-code @openai/codex @earendil-works/pi-coding-agent
# Kimi Code：curl 安装脚本按其官方文档
```

逐个登录（在本机独立认证，不复制 Mac 凭据）：

```bash
claude        # 走它的登录流程；用 CC Switch 接国产模型的，这里配各家的 BASE_URL/key
kimi login    # 如装了 kimi
# codex 用 `codex login`
```

- **注意 CC Switch 现实**：`claude` CLI 背后是哪家模型，看 `~/.claude/settings.json` 的 `ANTHROPIC_BASE_URL`——vendor 判定按实际后端，不按 CLI 名字（生成器会自动嗅探）。
- **已知无解**：`kimi-native`（kimi CLI 直连形态）会卡在 TUI 审批死等，**不进自动化池**；kimi 模型要走 CC Switch 套 claude 壳。

## 6. 配置 provider（有 API key 的模型才配；订阅 CLI 不用）

编辑 `~/.omnigent/config.yaml`（没有就新建）：

```yaml
providers:
  deepseek:
    kind: gateway
    openai:
      base_url: https://api.deepseek.com/v1
      api_key: $DEEPSEEK_API_KEY
      models:
        default: deepseek-v4-pro
```

`~/.bashrc` 追加：

```bash
export DEEPSEEK_API_KEY="<主公给你的 key>"
# gateway provider 的 key 必须能进 runner 进程（不配这个，pi 子 agent 报凭证无法解析）
export OMNIGENT_RUNNER_ENV_PASSTHROUGH="DEEPSEEK_API_KEY"
```

- **验证**：`source ~/.bashrc` 后 `omnigent-zh config list` 应看到本地 CLI（🎟️ subscription）+ gateway provider（🌐）。
- **失败分支**：`config list` 看不到 provider → 检查 YAML 缩进、环境变量已 export；`$VAR` 没展开 → 变量没在启动 server 的 shell 里 export。

## 7. 生成 controller bundle（自动调配，不手改 YAML）

```bash
cd ~/
git clone https://github.com/shankinchina-dotcom/agentcenter.git
# 若仓库是 private：先 gh auth login 并 gh auth setup-git
python3 ~/agentcenter/agentpeihe/gen_controller_bundle.py
```

- **预期**：打印环境检测（哪些 CLI 有、claude 壳实际 vendor、cooldown 名单）+ 生成计划（大脑 + 工人池），写出 `~/.omnigent/agents/controller/`。
- **检查生成结果**：`cat ~/.omnigent/agents/controller/config.yaml` 的大脑 harness；`ls ~/.omnigent/agents/controller/agents/` 的工人列表——应与你实际可用的执行体一致。
- **失败分支**：某执行体没出现在工人池 → 对照检测输出找原因（CLI 不在 PATH？key 没 export？在 cooldown？）；pi 工人的 config 里 `model`/`auth` 必须在 `executor` 顶层（生成器已保证，别手改）。

## 8. 注册并启动 server

```bash
omnigent-zh server stop 2>/dev/null
omnigent-zh server --no-open --agent ~/.omnigent/agents/controller
# 前台运行，这个终端别关；日常用可以放 tmux 里
```

- **预期**：`Starting omnigent server on 127.0.0.1:6767`；另开终端 `curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:6767` 返回 200。
- **Windows 浏览器**打开 `http://localhost:6767`：
  - **预期**：中文 Web UI，"智能体"区（Polly/Debby 那排）能看到 **controller**。
  - **失败分支**：浏览器打不开 → WSL 端口转发问题，`wsl --shutdown` 重开；智能体区没有 controller → 检查是不是用了前台 `--agent` 模式启动（`server start` 后台模式不注册）；controller 显示成第二个 "Claude Code" → bundle 大脑 harness 必须是 claude-sdk/codex/pi（生成器已保证，别手改成 native）。

## 9. 核心验收（8 项，全部通过才算完）

在 server 的工作目录放测试数据（问主公要 data.csv，或自己生成 3 列×10 行数值 CSV），Web UI 里向 controller 发：

```
请帮我写一个 Python 脚本，读取 data.csv 文件，计算每列的平均值和标准差，输出到 result.json。按 agentpeihe 关卡协议执行。

补充约束：
- data.csv 已放在你的工作目录，3 列 × 10 行
- 标准差使用 ddof=1（样本标准差）；如你选择 ddof=0 请在报告中注明
- 输出 result.json 格式：{"列名": {"mean": float, "std": float}, ...}
- 全程按关卡协议走：拆关卡→派发 Executor→审查报告→Reviewer 核验→汇总，不要自己写代码
```

逐项核对：

1. [ ] Controller 不自己写代码，输出关卡计划
2. [ ] 关卡含 9 字段契约（Role/Gate/Goal/Allowed/Forbidden/Validation/Stop/Report/Next Owner）
3. [ ] 用 agent 工具真实派发（右侧"智能体"面板子代理图谱出现 `关二爷-...` 节点）
4. [ ] Executor 输出 Gate Execution Report
5. [ ] Controller 审查通过后才推进
6. [ ] Reviewer（`法正-...`）与 Executor 不同 vendor（按实际后端）
7. [ ] Controller 汇总报告，result.json 数值正确
8. [ ] 全程无人工复制粘贴

**子 agent 卡住不动的排查顺序**：① 是不是 native CLI 的权限弹窗在等确认（子代理图谱节点显示"等待回应"）→ claude 工人要 `permission_mode: auto`（生成器已配）；② runner 日志 `~/.omnigent/logs/runner/` 最新文件里的报错；③ 报凭证问题 → 回第 6 步查 `OMNIGENT_RUNNER_ENV_PASSTHROUGH`。

## 10. 回报格式（交给主公带回）

完成后把以下内容回报给主公：

1. 每步的实际结果（通过/哪步失败+原始输出）
2. `omnigent-zh platform-info` 输出
3. 8 项验收逐项打勾结果（附 controller 最终汇总的原文）
4. 遇到的任何本文档没覆盖的问题（这就是下一个坑，会写进 PITFALLS.md）

**完成后停止，不要继续扩展玩法。**
