#!/usr/bin/env python3
"""gen_controller_bundle.py — agentpeihe 自动调配生成器。

检测本机可用执行体（CLI、API key、CC Switch 实际后端、注册表 cooldown），
一键重新生成 omnigent controller bundle（~/.omnigent/agents/controller/）。
换模型池 = 重跑本脚本，不手改 YAML。

用法:
  python3 gen_controller_bundle.py [--brain claude-sdk|codex|pi] [--out PATH] [--dry-run]

规则（Boss 2026-07-22）:
  - 大脑默认优先级: codex → claude-sdk（仅真 anthropic）→ pi
  - 子 agent 按真实 vendor 命名；Reviewer 必须异 vendor
  - DeepSeek: 走 CC Switch + Claude Code 壳（claude-native），借 Claude 底座增强能力；
    不再默认用 pi 直连（有 Claude 壳 deepseek 时跳过 pi deepseek）
  - Kimi: 只走 kimi-native（手工网页选 Kimi / 自动 exec_moonshot）；禁止进 Claude 壳
  - 官方 Anthropic Claude 模型：可选，大概率不用；仅 sniff=anthropic 时生成 exec_anthropic
  - Codex 工人: harness codex headless；Codex 可做丞相（--brain codex）
  - cooldown: 注册表 Scores 表 cooldown-until 未到期 → 该模型不出现在 tools
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path

REGISTRY = Path.home() / ".agent-collaboration/model-capability-registry.md"
CLAUDE_SETTINGS = Path.home() / ".claude/settings.json"

# pi harness 可接的 API provider：(env key, provider 名, 默认模型, vendor)
PI_PROVIDERS = [
    ("DEEPSEEK_API_KEY", "deepseek", "deepseek-v4-pro", "deepseek"),
    ("GROK_API_KEY", "grok", "grok-4.5", "xai"),
    ("ZHIPU_API_KEY", "zhipu", "glm-4-plus", "zhipu"),
    ("DASHSCOPE_API_KEY", "dashscope", "qwen-max", "alibaba"),
]

BRAIN_PRIORITY = ["codex", "claude-sdk", "pi"]

# 池子默认 pin 的 Codex 模型（Boss 指定 2026-07-22；None = 跟 codex CLI 默认走）
CODEX_WORKER_MODEL = "gpt-5.6-sol"


def sniff_claude_vendor() -> str:
    """claude CLI 实际 vendor：无劫持 base_url 才算 anthropic。"""
    try:
        env = json.loads(CLAUDE_SETTINGS.read_text()).get("env", {})
    except Exception:
        return "unknown"
    url = (env.get("ANTHROPIC_BASE_URL") or "").lower()
    key = (env.get("ANTHROPIC_API_KEY") or env.get("ANTHROPIC_AUTH_TOKEN") or "").lower()
    if "kimi.com" in url or "moonshot" in url or key.startswith("sk-kimi-"):
        return "moonshot"
    if "deepseek" in url:
        return "deepseek"
    if "bigmodel" in url:
        return "zhipu"
    if "volces.com" in url or "ark.cn-beijing" in url:
        return "volcengine"
    if not url or "anthropic.com" in url:
        return "anthropic"
    return f"unknown({url})"


def read_cooldowns() -> dict[str, str]:
    """注册表 Scores 表里的 cooldown 名单：{模型关键词: 截止日期}。"""
    out: dict[str, str] = {}
    if not REGISTRY.exists():
        return out
    today = datetime.date.today().isoformat()
    for line in REGISTRY.read_text().splitlines():
        if "cooldown-until:" not in line or not line.strip().startswith("|"):
            continue
        m = re.search(r"cooldown-until:\s*(\d{4}-\d{2}-\d{2})", line)
        first_cell = line.split("|")[1].strip() if line.count("|") >= 2 else ""
        if m and first_cell and m.group(1) > today:
            out[first_cell.lower()] = m.group(1)
    return out


def detect() -> dict:
    return {
        "has_claude": bool(shutil.which("claude")),
        "claude_vendor": sniff_claude_vendor() if shutil.which("claude") else None,
        "has_codex": bool(shutil.which("codex")),
        "has_pi": bool(shutil.which("pi")),
        "has_kimi": bool(shutil.which("kimi")),
        "has_grok": bool(shutil.which("grok")),
        "cooldowns": read_cooldowns(),
        "pi_providers": [(p, m, v) for k, p, m, v in PI_PROVIDERS if os.environ.get(k)],
    }


def worker_yaml(
    name: str,
    desc: str,
    harness_cfg: str,
    role_prompt: str,
    env_keys: list[str] | None = None,
    executor_extra: str = "",
) -> str:
    passthrough = ""
    if env_keys:
        keys = ", ".join(f'"{k}"' for k in env_keys)
        passthrough = f"""
    # omnigent 给子进程的环境是白名单制（防泄密），API key 必须显式放行
    env_passthrough: [{keys}]"""
    return f"""spec_version: 1
name: {name}
description: {desc}

executor:
  type: omnigent{executor_extra}
  config:
{harness_cfg}

os_env:
  type: caller_process
  cwd: .
  sandbox:
    type: none{passthrough}

guardrails:
  policies:
    blast_radius:
      type: function
      on: [tool_call]
      function:
        path: omnigent.inner.nessie.policies.blast_radius
        arguments:
          gate_pushes: false

prompt: |
{role_prompt}
"""


EXECUTOR_PROMPT = """  你是 agentpeihe 协作框架中的 Executor（关二爷）。执行 Controller 分配的单个关卡。

  ## 纪律
  - 严格遵守关卡契约中的 Allowed / Forbidden actions
  - 你有文件系统和 shell 工具（sys_os_*），可以直接读写文件、执行命令
  - 完成后按 Gate Execution Report 模板汇报：Scope / Todo / Actions Taken /
    Results / Differences / Not Executed / Risks / Recommendation / Next Owner
  - 不自行推进下一关，汇报后停止，等 Controller 审查
  - 遇到权限问题、未知差异、任务不清：立即停止并在 Risks 中说明，不要硬闯"""

REVIEWER_PROMPT = """  你是 agentpeihe 协作框架中的 Reviewer（法正·御史中丞）。独立审查 Executor 的产出。

  ## 纪律
  - 你有文件系统和 shell 工具（sys_os_*），可以独立重算/重跑验证
  - 检查关卡契约中 Validation 是否逐条满足
  - 发现"实际执行 vs 关卡契约"的偏差，提出反例和风险
  - 用独立方法复算关键结果（不复用 Executor 的代码路径）
  - 不自己修改代码、不修复问题——只报告
  - 报告格式：结论（PASS/FAIL）+ 逐条 Validation 核对 + 偏差清单 + 风险
  - 汇报后停止，Next Owner: controller"""

WORKER_PROMPT = EXECUTOR_PROMPT + "\n\n" + REVIEWER_PROMPT

CONTROLLER_PROMPT_TMPL = """  你是 agentpeihe 协作框架中的 **Controller（控制器，诸葛丞相）**。

  ## 核心职责
  1. 接收 Boss 任务，拆解为关卡序列（每个关卡 9 字段完整）
  2. 从模型池中为每个关卡选择最合适的 Executor
  3. 派发关卡时指定 Role: executor
  4. 审查 Gate Execution Report，拒绝不达标报告
  5. 选择与 Executor 不同 vendor 的 Reviewer 进行核验
  6. 汇总并向 Boss 报告

  ## 模型池（vendor 按实际后端判定，由 gen_controller_bundle.py 于 {date} 生成）
{pool_table}

  ## 通道隔离（硬规则）
  - DeepSeek：CC Switch + Claude Code 壳（exec_deepseek / claude-native），vendor=deepseek
  - Kimi：只走 kimi-native（手工网页选 Kimi / 自动 exec_moonshot），禁止塞进 Claude 壳
  - 官方 Anthropic Claude：可选，非默认
  - Codex 丞相与 openai 工人：harness codex，与上列独立

  ## 角色分配规则
  - Executor 从"可用"子 agent 中选
  - Reviewer 从"可用"且实际 vendor ≠ Executor 实际 vendor 的子 agent 中选
  - **避免裁判运动员一身兼：Executor 与 Controller 大脑同模型时，优先换其他 vendor 的 Executor**
  - **vendor 自检（无代码级强制，靠你执行）：** 派发 Reviewer 前，在派发消息中显式写出
    "Executor vendor = X, Reviewer vendor = Y, X ≠ Y"（按实际后端），不成立则换 Reviewer

  ## 关卡契约模板（派发时包含，共 9 字段）
  Role: executor
  Gate: [关卡名]
  Goal: [目标]
  Allowed: [允许的操作]
  Forbidden: [禁止的操作]
  Validation: [验收条件]
  Stop: [停止条件]
  Report: Gate Execution Report
  Next Owner: controller

  ## 执行原则
  - **一次一个关卡，不跳步**
  - **Executor 报告不满足 Validation = 拒绝 + 说明原因 + 要求重做**
  - **任何执行 > 1 分钟的任务必须派发**
  - **每次回复以 Next Owner 结尾**
  - **不要自己写代码、改文件、执行命令**（你是 Controller，不是 Executor）
  - 派发用 sys_session_send，子 agent 完成后会经 inbox 通知你；不要轮询，等通知即可

  ## 立项关（项目启动摄入机制）
  - **触发**：Boss 的消息是项目级任务（多阶段/多关卡/有长期计划）时，动工前先做立项问答；
    单步小任务直接跳过，不搞形式主义
  - **三个问题（一条消息问完，Boss 一条回复答完）**：
    1. 你有没有已列好的长计划/todo list？（有 → 我按你的计划映射关卡序列；没有 → 我先拆一版给你确认）
    2. 角色怎么定？——全自动（按维度分+vendor 规则）/ 半指定（只点名丞相或法正）/ 全指定（我只做 vendor 校验和 cooldown 检查）
    3. 项目红线和验收标准是什么？（禁做事项、怎么算完成）
  - **产出《项目章程》**：关卡序列草案 + 角色安排 + 红线 + 验收标准，
    Boss 确认后才开第一关；之后所有关卡引用章程作为上下文锚点
  - **会话命名必须用中文角色名（Web UI 子代理图谱直接显示它）**：
    session_name 格式 `<角色中文名>-<关卡号>-<简述>`，
    例：`关二爷-G1-统计脚本`、`法正-G2-独立核验`、`马良-G3-架构评审`。
    禁止英文 slug（gate2-verify 这类名字 Boss 看不懂是谁）"""


def build(det: dict, brain: str | None) -> tuple[dict[str, str], list[str], str, list[str]]:
    """返回 ({相对路径: 内容}, workers, brain, pool_notes)。"""
    files: dict[str, str] = {}
    workers: list[tuple[str, str, str, str]] = []  # (name, harness, vendor, note)
    pool_notes: list[str] = []
    cd = det["cooldowns"]

    # Claude Code 壳工人（按 CC Switch 实际 vendor）
    # - deepseek：Boss 指定主路径（Claude 底座 + DeepSeek 模型）
    # - anthropic：官方 Claude，可选，大概率不用
    # - moonshot：禁止（Kimi 必须 kimi-native）
    claude_shell_vendors: set[str] = set()
    v = det.get("claude_vendor")
    if det["has_claude"] and v and v not in (None, "unknown"):
        if v == "moonshot":
            pool_notes.append(
                "  | claude-native | claude-native | moonshot | — | "
                "禁止（Kimi 只走 kimi-native，勿用 CC Switch 占 Claude 壳） |"
            )
        else:
            name = f"exec_{v}"
            if v == "deepseek":
                note = "CC Switch + Claude Code 壳，permission_mode=auto（DeepSeek 主路径）"
                desc = (
                    "deepseek 执行体（Claude Code 壳经 CC Switch → DeepSeek）。"
                    "借 Claude 底座；可担任 executor/reviewer。"
                )
            elif v == "anthropic":
                note = "真 Anthropic Claude Code，permission_mode=auto（可选）"
                desc = "anthropic 执行体（官方 Claude Code）。可担任 executor/reviewer。"
            else:
                note = f"Claude Code 壳经 CC Switch，permission_mode=auto，vendor={v}"
                desc = f"{v} 执行体（Claude Code 壳经 CC Switch）。可担任 executor/reviewer。"
            workers.append((name, "claude-native", v, note))
            files[f"agents/{name}/config.yaml"] = worker_yaml(
                name,
                desc,
                "    harness: claude-native\n    permission_mode: auto",
                WORKER_PROMPT,
            )
            claude_shell_vendors.add(v)

    # Codex 工人（headless codex exec）
    if det["has_codex"] and "codex current model" not in cd:
        workers.append(
            (
                "exec_openai",
                "codex",
                "openai",
                f"headless exec 形态，model={CODEX_WORKER_MODEL or 'CLI默认'}",
            )
        )
        files["agents/exec_openai/config.yaml"] = worker_yaml(
            "exec_openai",
            f"openai 执行体（Codex CLI，headless exec 形态，model={CODEX_WORKER_MODEL or 'CLI默认'}）。可担任 executor/reviewer。",
            "    harness: codex",
            WORKER_PROMPT,
            executor_extra=f"\n  model: {CODEX_WORKER_MODEL}" if CODEX_WORKER_MODEL else "",
        )

    # pi API 工人：备用通道；与 Claude 壳 / ACP 冲突的 vendor 跳过
    if det["has_pi"]:
        for provider, model, vendor in det["pi_providers"]:
            if vendor in claude_shell_vendors:
                pool_notes.append(
                    f"  | pi:{model} | pi | {vendor} | — | "
                    f"跳过（已用 Claude 壳 exec_{vendor}） |"
                )
                continue
            if vendor == "xai" and det.get("has_grok"):
                pool_notes.append(
                    f"  | pi:{model} | pi | xai | — | 跳过（已有 exec_xai = acp:grok-build） |"
                )
                continue
            name = f"exec_{vendor}"
            workers.append((name, f"pi:{model}", vendor, "API key 已检测到（pi 备用）"))
            files[f"agents/{name}/config.yaml"] = worker_yaml(
                name,
                f"{vendor} 执行体（pi harness，API model={model}）。可担任 executor/reviewer。",
                "    harness: pi",
                WORKER_PROMPT,
                executor_extra=(
                    f"\n  model: {model}\n  auth:\n    type: provider\n    name: {provider}"
                ),
            )

    # Kimi 工人：只走 kimi-native（与 Claude 通道完全隔离）
    # Omnigent 默认给 kimi-native 加 --yolo，可被 Controller 自动派活；
    # 手工用：网页选 Kimi 或 `omnigent-zh kimi`（同一 CLI，不占 Claude）。
    if det["has_kimi"]:
        workers.append(
            ("exec_moonshot", "kimi-native", "moonshot", "Kimi Code CLI，默认 --yolo；可手工也可自动派")
        )
        files["agents/exec_moonshot/config.yaml"] = worker_yaml(
            "exec_moonshot",
            "moonshot 执行体（kimi-native，Kimi Code CLI）。可担任 executor/reviewer；也可网页手工开 Kimi 会话。",
            "    harness: kimi-native",
            WORKER_PROMPT,
        )
    else:
        pool_notes.append(
            "  | kimi-native | kimi-native | moonshot | — | 不可用（PATH 无 kimi；装 ~/.kimi-code/bin） |"
        )

    # Grok Build（ACP）
    if det.get("has_grok"):
        workers.append(("exec_xai", "acp:grok-build", "xai", "Grok Build CLI，ACP 接入"))
        files["agents/exec_xai/config.yaml"] = worker_yaml(
            "exec_xai",
            "xai 执行体（Grok Build CLI，ACP 协议，SuperGrok 订阅）。可担任 executor/reviewer。",
            "    harness: acp:grok-build",
            WORKER_PROMPT,
        )

    # 大脑选择：claude-sdk 仅真 anthropic 可当默认大脑
    if brain is None:
        for b in BRAIN_PRIORITY:
            if b == "codex" and det["has_codex"] and "codex current model" not in cd:
                brain = b
                break
            if (
                b == "claude-sdk"
                and det["has_claude"]
                and det["claude_vendor"] == "anthropic"
            ):
                brain = b
                break
            if b == "pi" and det["has_pi"] and det["pi_providers"]:
                brain = b
                break
        else:
            sys.exit("错误：没有可用的大脑（codex / 真 claude / pi 全部不可用）")

    if brain == "claude-sdk" and det["claude_vendor"] != "anthropic":
        sys.exit(
            f"错误：--brain claude-sdk 但当前 Claude 实际 vendor={det['claude_vendor']} "
            "（CC Switch 劫持）。请先恢复真 Anthropic，或改用 --brain codex / pi。"
        )

    brain_note = {
        "claude-sdk": "真 Claude（claude-sdk，vendor=anthropic）",
        "codex": "Codex（openai，headless SDK 形态）",
        "pi": f"API 模型（pi harness，{det['pi_providers'][0][1] if det['pi_providers'] else '?'}）",
    }[brain]

    pool_rows = "\n".join(
        f"  | {n} | {h} | {v} | executor, reviewer | 可用（{note}） |"
        for n, h, v, note in workers
    )
    pool_table = (
        "  | 子 agent | Harness | 实际 Vendor | 可担任角色 | 状态 |\n"
        "  |---------|---------|--------|-----------|------|\n"
        + pool_rows
    )
    if cd:
        pool_table += "\n" + "\n".join(
            f"  | {k} | — | — | — | cooldown 至 {v} |" for k, v in cd.items()
        )
    if pool_notes:
        pool_table += "\n" + "\n".join(pool_notes)

    brain_cfg = f"    harness: {brain}"
    if brain == "pi" and det["pi_providers"]:
        # model 必须在 executor 顶层，spawn 才读得到
        # 注意：brain_cfg 只写 config.harness；pi 大脑的 model 放 executor 顶层
        pass

    pi_model_top = ""
    if brain == "pi" and det["pi_providers"]:
        provider, model, _vendor = det["pi_providers"][0]
        pi_model_top = (
            f"\n  model: {model}\n  auth:\n    type: provider\n    name: {provider}"
        )

    files["config.yaml"] = f"""spec_version: 1
name: controller
description: 三国总控（诸葛丞相）。本文件由 gen_controller_bundle.py 生成（{datetime.date.today().isoformat()}），请勿手改——重新跑生成器即可。

executor:
  type: omnigent{pi_model_top}
  config:
{brain_cfg}
    # 大脑：{brain_note}

prompt: |
{CONTROLLER_PROMPT_TMPL.format(date=datetime.date.today().isoformat(), pool_table=pool_table)}

os_env:
  type: caller_process
  cwd: .
  sandbox:
    type: none

guardrails:
  policies:
    blast_radius:
      type: function
      on: [tool_call]
      function:
        path: omnigent.inner.nessie.policies.blast_radius
        arguments:
          gate_pushes: false

async: true
cancellable: true

tools:
  agents:
{chr(10).join(f'    - {n}' for n, _, _, _ in workers)}
"""
    return files, [n for n, _, _, _ in workers], brain, pool_notes


def ensure_acp_config(dry_run: bool = False) -> None:
    """~/.omnigent/config.yaml 缺 acp agents 块时补上（Grok Build 接入的前提）。"""
    cfg = Path.home() / ".omnigent/config.yaml"
    block = (
        "\n# ACP 协议接入的执行体（各自管自己的登录态，omnigent 不存凭据）\n"
        "acp:\n  agents:\n    - {name: Grok Build, command: grok agent stdio}\n"
    )
    existing = cfg.read_text() if cfg.exists() else ""
    if "acp:" in existing and "grok agent stdio" in existing:
        print("acp 配置块已存在，跳过")
        return
    print(f"{'[dry] ' if dry_run else ''}向 {cfg} 追加 acp agents 块")
    if not dry_run:
        cfg.parent.mkdir(parents=True, exist_ok=True)
        with cfg.open("a") as f:
            f.write(block)


def _purge_stale_agents(out: Path, keep: set[str], dry_run: bool) -> None:
    """删除本轮未生成的 agents/<name>，避免残留假 Claude 壳配置。"""
    agents_dir = out / "agents"
    if not agents_dir.is_dir():
        return
    for child in agents_dir.iterdir():
        if not child.is_dir():
            continue
        if child.name in keep:
            continue
        print(f"  {'[dry] ' if dry_run else ''}删残留 {child}")
        if not dry_run:
            shutil.rmtree(child)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brain", choices=["claude-sdk", "codex", "pi"], default=None)
    ap.add_argument("--out", default=str(Path.home() / ".omnigent/agents/controller"))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    det = detect()
    print("== 环境检测 ==")
    print(f"claude CLI: {'有' if det['has_claude'] else '无'}  实际 vendor: {det['claude_vendor']}")
    print(f"codex CLI:  {'有' if det['has_codex'] else '无'}  cooldown: {det['cooldowns'] or '无'}")
    print(f"kimi CLI:   {'有' if det['has_kimi'] else '无'}  （kimi-native 手工+自动）")
    print(
        f"pi CLI:     {'有' if det['has_pi'] else '无'}  "
        f"API providers: {[p for p, _, _ in det['pi_providers']] or '无'}"
    )

    files, workers, brain, notes = build(det, args.brain)
    print(f"\n== 生成计划 ==\n大脑: {brain}\n工人: {workers}")
    if notes:
        print("备注:")
        for n in notes:
            print(n)
    if det.get("has_grok"):
        ensure_acp_config(dry_run=args.dry_run)
    out = Path(args.out)
    keep = set(workers)
    _purge_stale_agents(out, keep, args.dry_run)
    for rel, content in files.items():
        p = out / rel
        print(f"  {'[dry] ' if args.dry_run else ''}写 {p}")
        if not args.dry_run:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
    if not args.dry_run:
        print(
            f"\n完成。重新注册：omnigent-zh server stop; "
            f"omnigent-zh server --no-open --agent {out}"
        )


if __name__ == "__main__":
    main()
