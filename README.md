# Agent 配合（agentpeihe）

多 Agent 协作的关卡（Gate）制度 + omnigent 自动化编排部署 —— 一次只批一个关卡，执行完汇报，不自动推进；模型池、角色、vendor 全部由环境检测自动调配，不手改配置。

## 这个仓库有什么

| 文件 | 内容 |
|------|------|
| `SKILL.md` | agentpeihe 协作协议（关卡契约、报告契约、人工中继模式、多维度评分规则） |
| `gen_controller_bundle.py` | **自动调配生成器**：检测本机 CLI/API key/CC Switch 实际后端/注册表 cooldown，一键生成 omnigent controller bundle——换模型、换大脑、换机器，重跑它就行 |
| `docs/omnigent-agentpeihe-deploy.md` | 双机部署指南（macOS + Windows WSL2），含 provider 配置、proxy/NO_PROXY 国内外混用、角色化验收 |
| `docs/PITFALLS.md` | **踩坑实录**：10 个真实坑，每个按「坑→为什么→怎么解→同类怎么避免」组织。下载本项目前建议先读 |

## 快速开始（omnigent 自动化，Mac 示例）

> 目标：从 Web UI / CLI 发任务，Controller 自动拆关卡 → 派 Executor → 异 vendor Reviewer 核验 → 汇总，全程无人工复制粘贴。

```bash
# 1. 装 omnigent（需 Python 3.12+ / Node 22+ / uv / tmux）
uv tool install --force --python 3.12 "git+https://github.com/professoryu06/omnigent-zh-cn.git"

# 2. 准备执行体（按需，至少有 2 个不同 vendor）
#    - 订阅 CLI：`claude` / `codex` / `kimi` 登录即可，不要 API key
#    - API 模型：export DEEPSEEK_API_KEY=...（pi harness 用，需 npm i -g @earendil-works/pi-coding-agent）
#    - 国内外混用代理：export HTTPS_PROXY=http://127.0.0.1:1082
#      export NO_PROXY=api.deepseek.com,api.moonshot.cn,localhost,127.0.0.1
#    - gateway provider 的 key 要进 runner：
export OMNIGENT_RUNNER_ENV_PASSTHROUGH="DEEPSEEK_API_KEY"

# 3. 配置 provider（API 模型才需要）：~/.omnigent/config.yaml，示例见部署文档第三步

# 4. 生成 controller bundle（自动检测环境，不手改 YAML）
python3 gen_controller_bundle.py
#    输出：~/.omnigent/agents/controller/（大脑 + 可用工人池 + vendor 互审规则）

# 5. 注册并启动（必须前台模式带 --agent；改 bundle 后要重启）
omnigent-zh server --no-open --agent ~/.omnigent/agents/controller

# 6. 浏览器打开 http://localhost:6767，"智能体"区选 controller 发任务
```

**别踩坑**：上面每一步都对应 `docs/PITFALLS.md` 里一个实测过的坑（agent 不注册不显示、native 大脑不显示名字、headless 审批死锁、model 放错层级、runner 拿不到 key、国内外代理互掐……）。装之前读一遍，省三小时。

## 角色

| 角色 | 中文名 | 职责 |
|------|--------|------|
| Boss | 主公 | 批准每个关卡，解决规则冲突 |
| Controller | 诸葛丞相 | 制定计划、审查证据、分配模型、维护评分 |
| Executor | 关二爷 | 执行单个关卡，汇报后停止 |
| Reviewer | 法正 | 独立核验，必须与 Executor 不同 vendor |
| Specialist | 马良 | 有边界的领域任务 |

角色与模型**解耦**：同一份 instructions，生成器按环境把可用模型填进池子；Reviewer 异 vendor 由 Controller 派发时显式自检（按实际后端算，CC Switch 壳按真实 vendor 不按 CLI 名）。

## 多维度模型评分

不信公开榜单（2026 年主流 benchmark 已被证明可刷分），只信实战关卡证据。注册表（`~/.agent-collaboration/model-capability-registry.md`）按 **7 个维度独立记分**（0–100）：

前端 / 后端实现 / Agent 协同 / 修 bug / 架构 / 检索格式化 / 安全数据

规则：0 分维度只能接校准关（过了得 60 基准分）；同维度过关 +5、被拒 −10；30 天无证据过期复证；额度耗尽不扣分记 cooldown；证据未闭环标"暂记"。新模型必给机会，老模型定期复证。详见 `SKILL.md` "Score Calibration and Renewal"。

## 核心流程

```
Boss 提出任务
    ↓
Controller 读项目规则，定义关卡（9 字段契约）
    ↓
Boss 批准关卡
    ↓
Executor 执行 → 提交 Gate Execution Report
    ↓
Controller 审查差异和风险（Reviewer 异 vendor 独立核验）
    ↓
指定 Next Owner → 循环或结束
```

**关键原则：一次一个关卡，不跳步，不自动推进。**

## 手动中继模式

Controller 无法直接调用某模型时（只有网页版、只有订阅 UI），走人工中继：Controller 输出推荐模型 + 职责边界 + 资格状态 + `调用方式：人工中继，不声称已实际调用` + 一段自包含可复制提示词，Boss 转贴并带回 `Gate Execution Report` + `Next Handoff Proposal`。缺 API/CLI/路由**不是阻塞**，协议原生支持。详见 `SKILL.md`。

## 适用 / 不适用

适用：跨多 Agent 的复杂任务、指定模型执行、生产级变更部署、跨仓库协作、ownership 不明。
不适用：简单单步任务、纯信息查询、日常单人开发。
