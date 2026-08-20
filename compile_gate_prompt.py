#!/usr/bin/env python3
"""compile_gate_prompt.py — agentpeihe 关卡提示词编译器（三段式）。

把一关的 9 字段契约编译成可经 sys_session_send 直接下发的提示词：
initial 模式输出 [固定头]（角色纪律要点 + AGENTS.md 全文 + repo map 全文）
+ [本关契约] + [产物指针]；followup 模式只输出后两段（Sticky Executor
续关时用，固定头不重复下发）。

用法:
  python3 compile_gate_prompt.py --project <repo路径> --role executor|reviewer \
      --gate <关卡名> --goal .. --allowed .. --forbidden .. --validation .. --stop .. \
      [--report ..] [--next-owner ..] [--artifact "<路径>: <一句话说明>"]... \
      [--mode initial|followup] [--out PATH]

规则:
  - 绝对确定性：同输入逐字节同输出；禁止时间戳/日期/随机 ID 混进编译器自产文本
  - reviewer 从接口上拿不到执行者历史（脚本无此参数），保证极简上下文
  - 产物指针必须含冒号分隔「路径: 说明」（全角冒号亦可），否则报错退出非零
  - 产物指针去重保序；纪律上每个前置关卡最多 3 条（由 Controller 把关）
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# 中文角色名闭合集（与 agentpeihe SKILL.md 一致，禁止自创武将名）
ROLE_CN = {"executor": "关二爷", "reviewer": "法正"}

DEFAULT_REPORT = "Gate Execution Report"
DEFAULT_NEXT_OWNER = "controller"

# 固定占位行（逐字固定， Controller 与测试都按原文匹配）
MISSING_AGENTS = "[AGENTS.md 缺失：--project 路径下无此文件]"
MISSING_REPO_MAP = "[repo map 缺失：先运行 gen_repo_map.py <project> 生成]"
NO_ARTIFACTS = "（无前置产物）"

EXECUTOR_DISCIPLINE = """\
- 身份：agentpeihe 协作框架的 Executor（关二爷）。本段为纪律要点，全文见 agentpeihe SKILL.md。
- 只执行当前关卡契约：严格遵守 Allowed / Forbidden，契约之外的操作一律不做。
- 你有文件系统与 shell 工具（sys_os_*），可直接读写文件、执行命令。
- 完工按 Report 字段指定模板汇报（默认 Gate Execution Report：Scope / Todo /
  Actions Taken / Results / Differences / Not Executed / Risks / Recommendation / Next Owner）。
- 汇报即停止：不自行推进下一关，等 Controller 审查；Next Owner 恒为 controller。
- 遇到权限问题、未知差异、任务不清：立即停止并在 Risks 中说明，不要硬闯。
- Sticky 会话：本会话跨关复用，后续关卡只续发 [本关契约] + [产物指针]（followup），
  以最新契约为准；军报必须自包含，不依赖对方翻历史。
- 产物沉淀：产出写入项目内文件，军报只给路径指针；State Summary 写到
  .agentpeihe/state/<角色>·<模型>.md，供会话压缩或换模型后恢复。
- 红线：禁泄露凭据密钥、禁无关安装升级、禁 git commit/push、禁部署共享或生产环境。"""

REVIEWER_DISCIPLINE = """\
- 身份：agentpeihe 协作框架的 Reviewer（法正·御史中丞）。本段为纪律要点，全文见 agentpeihe SKILL.md。
- 极简上下文：你不接收执行者会话历史，只凭 [本关契约]、[产物指针] 与仓库现状独立判断。
- 独立核验：用独立方法复算或重跑关键结果，不复用 Executor 的代码路径。
- 逐条核对 Validation，指出「实际执行 vs 关卡契约」的偏差，给出反例与风险。
- 只报告不修改：不改代码、不修问题。报告格式 = 结论（PASS/FAIL）+ 逐条 Validation 核对
  + 偏差清单 + 风险。
- 汇报即停止：Next Owner 恒为 controller。"""

DISCIPLINE = {"executor": EXECUTOR_DISCIPLINE, "reviewer": REVIEWER_DISCIPLINE}

# 动态字段模式：编译器自产文本一律禁止命中
_DYNAMIC_RES = (
    re.compile(r"\d{4}-\d{2}-\d{2}"),  # ISO 日期
    re.compile(r"\d{4}/\d{2}/\d{2}"),  # 斜杠日期
    re.compile(r"\d{2}:\d{2}:\d{2}"),  # 时间戳
    re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"),  # uuid
)


def _assert_static(text: str) -> None:
    """编译器自产文本的确定性自检：禁止日期/时间戳/uuid。

    只查编译器自己生成的片段（纪律要点、段标题、占位行）；AGENTS.md /
    repo map 嵌入原文与契约字段值都是用户数据，不在此列。
    """
    for pat in _DYNAMIC_RES:
        m = pat.search(text)
        if m:
            raise ValueError(f"编译脚手架含动态字段 {m.group(0)!r}（禁止日期/时间戳/uuid）")


def parse_artifacts(raw: list[str]) -> list[str]:
    """校验并规范化产物指针：每条必须「路径: 说明」（半角/全角冒号均可），去重保序。"""
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        s = item.strip()
        m = re.search(r"[:：]", s)
        if not m:
            raise ValueError(
                f"产物指针格式非法: {item!r}（缺冒号分隔，应为 \"<路径>: <一句话说明>\"）"
            )
        path, desc = s[: m.start()].strip(), s[m.end():].strip()
        if not path or not desc:
            raise ValueError(f"产物指针格式非法: {item!r}（路径与说明都不能为空）")
        line = f"{path}: {desc}"
        if line not in seen:
            seen.add(line)
            out.append(line)
    return out


def _read_embed(path: Path, placeholder: str) -> tuple[str, bool]:
    """读嵌入文件全文；文件缺失 → 固定占位行。返回 (文本, 是否编译器自产)。"""
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace").rstrip("\n"), False
    return placeholder, True


def compile_prompt(
    project: Path,
    role: str,
    gate: str,
    goal: str,
    allowed: str,
    forbidden: str,
    validation: str,
    stop: str,
    report: str = DEFAULT_REPORT,
    next_owner: str = DEFAULT_NEXT_OWNER,
    artifacts: list[str] | None = None,
    mode: str = "initial",
) -> str:
    """编译三段式关卡提示词。同输入逐字节同输出，无时间戳/日期/随机 ID。"""
    if role not in ROLE_CN:
        raise ValueError(f"未知角色: {role!r}（闭合集：{'/'.join(ROLE_CN)}）")
    if mode not in ("initial", "followup"):
        raise ValueError(f"未知模式: {mode!r}（initial/followup）")

    segs: list[tuple[str, bool]] = []  # (片段, 是否编译器自产)
    if mode == "initial":
        agents_text, agents_self = _read_embed(project / "AGENTS.md", MISSING_AGENTS)
        rmap_text, rmap_self = _read_embed(
            project / ".agentpeihe" / "repo_map.md", MISSING_REPO_MAP
        )
        segs += [
            ("# [固定头]\n\n", True),
            (f"## 角色纪律（{role} · {ROLE_CN[role]}）\n\n", True),
            (DISCIPLINE[role] + "\n\n", True),
            ("## 项目规范（AGENTS.md）\n\n", True),
            (agents_text + "\n\n", agents_self),
            ("## 仓库骨架（repo map）\n\n", True),
            (rmap_text + "\n\n", rmap_self),
        ]

    fields = [
        ("Role", role),
        ("Gate", gate),
        ("Goal", goal),
        ("Allowed", allowed),
        ("Forbidden", forbidden),
        ("Validation", validation),
        ("Stop", stop),
        ("Report", report),
        ("Next Owner", next_owner),
    ]
    segs.append(("# [本关契约]\n\n", True))
    segs.append(("".join(f"{k}: {v}\n" for k, v in fields) + "\n", False))

    segs.append(("# [产物指针]\n\n", True))
    lines = parse_artifacts(artifacts or [])
    if lines:
        segs.append(("".join(f"- {ln}\n" for ln in lines), False))
    else:
        segs.append((NO_ARTIFACTS + "\n", True))

    _assert_static("".join(t for t, self_gen in segs if self_gen))
    return "".join(t for t, _ in segs)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="agentpeihe 关卡提示词编译器（三段式，绝对确定性）"
    )
    ap.add_argument("--project", required=True, help="目标项目仓库路径")
    ap.add_argument("--role", required=True, choices=sorted(ROLE_CN), help="角色（闭合集）")
    ap.add_argument("--gate", required=True, help="关卡名")
    ap.add_argument("--goal", required=True, help="目标")
    ap.add_argument("--allowed", required=True, help="允许的操作")
    ap.add_argument("--forbidden", required=True, help="禁止的操作")
    ap.add_argument("--validation", required=True, help="验收条件")
    ap.add_argument("--stop", required=True, help="停止条件")
    ap.add_argument("--report", default=DEFAULT_REPORT, help=f"汇报模板（默认 {DEFAULT_REPORT}）")
    ap.add_argument(
        "--next-owner", default=DEFAULT_NEXT_OWNER, help=f"下一棒（默认 {DEFAULT_NEXT_OWNER}）"
    )
    ap.add_argument(
        "--artifact",
        action="append",
        default=[],
        metavar='"路径: 说明"',
        help="前置关卡产物指针，可重复；每个前置关卡最多 3 条",
    )
    ap.add_argument(
        "--mode",
        choices=["initial", "followup"],
        default="initial",
        help="initial 含固定头；followup 只下发契约+指针（sticky 续关，默认 initial）",
    )
    ap.add_argument("--out", default=None, help="写入文件（覆盖）；缺省输出到 stdout")
    args = ap.parse_args()

    project = Path(args.project).expanduser()
    if not project.is_dir():
        sys.exit(f"错误：--project 路径不存在或不是目录: {project}")
    try:
        text = compile_prompt(
            project=project,
            role=args.role,
            gate=args.gate,
            goal=args.goal,
            allowed=args.allowed,
            forbidden=args.forbidden,
            validation=args.validation,
            stop=args.stop,
            report=args.report,
            next_owner=args.next_owner,
            artifacts=args.artifact,
            mode=args.mode,
        )
    except ValueError as e:
        sys.exit(f"错误：{e}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"写 {out}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
