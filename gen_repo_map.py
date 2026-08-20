#!/usr/bin/env python3
"""gen_repo_map.py — 生成目标仓库的稳定骨架（repo map）。

供 compile_gate_prompt.py 的固定头嵌入，让执行者/复核者拿到零动态字段的
仓库全貌。仓库结构变化时重跑本脚本即可，勿手改产物。

用法:
  python3 gen_repo_map.py <repo路径> [--out PATH]

规则:
  - 文件清单优先 git ls-files（含未跟踪但未忽略的文件）；非 git 仓库回退 os.walk
  - 输出两层目录树（目录 + 文件数）、清单文件要点、常见入口提示
  - 全部字典序、零动态字段（无日期/时间戳）：同一代码状态逐字节一致
  - .agentpeihe/ 不计入（产物自身所在目录，纳入会打破幂等）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover - 老版本 Python 回退正则提取
    tomllib = None  # type: ignore[assignment]

# os.walk 回退时排除的常见目录
EXCLUDE_DIRS = frozenset(
    {
        ".git",
        "__pycache__",
        "node_modules",
        ".venv",
        "venv",
        ".idea",
        ".vscode",
        "dist",
        "build",
        "target",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".tox",
        ".eggs",
        ".agentpeihe",
    }
)

# 常见入口文件候选（相对仓库根）
ENTRY_CANDIDATES = [
    "main.py",
    "app.py",
    "run.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
    "__main__.py",
    "index.py",
    "index.js",
    "index.ts",
    "main.go",
    "main.rs",
    "cmd/main.go",
    "src/main.py",
    "src/main.js",
    "src/main.ts",
    "src/main.go",
    "src/main.rs",
    "src/index.js",
    "src/index.ts",
    "src/app.py",
]

SUBTITLE = "由 gen_repo_map.py 生成；仓库结构变化时重跑。"


def _git_files(repo: Path) -> list[str] | None:
    """git 仓库 → git ls-files 清单；非 git 或 git 不可用 → None（回退 os.walk）。"""
    if not shutil.which("git"):
        return None
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if top.returncode != 0:
            return None
        # 防误纳父仓库：目标目录落在别的 git 工作树里时按非 git 处理
        if Path(top.stdout.strip()).resolve() != repo.resolve():
            return None
        out = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=repo,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        if out.returncode != 0:
            return None
        return [f for f in out.stdout.split("\0") if f]
    except (OSError, subprocess.TimeoutExpired):
        return None


def _walk_files(repo: Path) -> list[str]:
    """os.walk 回退清单（排除常见噪音目录，不跟随符号链接防环）。"""
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_DIRS)
        for fn in filenames:
            rel = (Path(dirpath) / fn).relative_to(repo).as_posix()
            out.append(rel)
    return out


def _render_tree(files: list[str]) -> list[str]:
    """两层目录树：第一层目录（根目录单列）+ 第二层目录，各带文件数，字典序。"""
    top: dict[str, int] = {}  # 第一层目录（"" 表示根目录）→ 文件数（含深层）
    second: dict[str, dict[str, int]] = {}  # 第一层 → {第二层目录 → 文件数（含深层）}
    for f in files:
        parts = f.split("/")
        key1 = parts[0] if len(parts) > 1 else ""
        top[key1] = top.get(key1, 0) + 1
        if len(parts) > 2:
            key2 = f"{parts[0]}/{parts[1]}"
            bucket = second.setdefault(key1, {})
            bucket[key2] = bucket.get(key2, 0) + 1
    lines: list[str] = []
    if top.get(""):
        lines.append(f"- 根目录（{top['']} 个文件）")
    for d in sorted(k for k in top if k):
        lines.append(f"- `{d}/`（{top[d]} 个文件）")
        for d2 in sorted(second.get(d, {})):
            lines.append(f"  - `{d2}/`（{second[d][d2]} 个文件）")
    return lines


def _regex_toml_fields(text: str, section: str, keys: tuple[str, ...]) -> dict[str, str]:
    """极简 TOML 提取：只认 [section] 段内 key = "value" 行（tomllib 缺失时的回退）。"""
    out: dict[str, str] = {}
    in_sec = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            in_sec = s == f"[{section}]"
            continue
        if in_sec:
            m = re.match(r'([A-Za-z0-9_-]+)\s*=\s*"([^"]*)"', s)
            if m and m.group(1) in keys:
                out[m.group(1)] = m.group(2)
    return out


def _regex_toml_section_keys(text: str, section: str) -> list[str]:
    """极简 TOML 提取：[section] 段内全部键名（tomllib 缺失时的回退）。"""
    keys: list[str] = []
    in_sec = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("["):
            in_sec = s == f"[{section}]"
            continue
        if in_sec:
            m = re.match(r'([A-Za-z0-9_-]+|"[^"]+")\s*=', s)
            if m:
                keys.append(m.group(1).strip('"'))
    return sorted(keys)


def _pyproject_note(repo: Path) -> str | None:
    """pyproject.toml：[project] name + [project.scripts] 键。"""
    p = repo / "pyproject.toml"
    if not p.is_file():
        return None
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        if tomllib is not None:
            proj = tomllib.loads(text).get("project") or {}
            name = proj.get("name") or ""
            scripts = sorted((proj.get("scripts") or {}).keys())
        else:
            name = _regex_toml_fields(text, "project", ("name",)).get("name", "")
            scripts = _regex_toml_section_keys(text, "project.scripts")
    except Exception:
        return None
    parts = []
    if name:
        parts.append(f"project.name = `{name}`")
    if scripts:
        parts.append("scripts = " + "、".join(f"`{s}`" for s in scripts))
    return f"- `pyproject.toml`：{'；'.join(parts)}" if parts else None


def _package_json_note(repo: Path) -> str | None:
    """package.json：name / main / bin。"""
    p = repo / "package.json"
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return None
    parts = []
    if data.get("name"):
        parts.append(f"name = `{data['name']}`")
    if data.get("main"):
        parts.append(f"main = `{data['main']}`")
    binv = data.get("bin")
    if isinstance(binv, dict) and binv:
        parts.append("bin = " + "、".join(f"`{k}`" for k in sorted(binv)))
    elif isinstance(binv, str) and binv:
        parts.append(f"bin = `{binv}`")
    return f"- `package.json`：{'；'.join(parts)}" if parts else None


def _go_mod_note(repo: Path) -> str | None:
    """go.mod：module 行。"""
    p = repo / "go.mod"
    if not p.is_file():
        return None
    m = re.search(r"(?m)^module\s+(\S+)", p.read_text(encoding="utf-8", errors="replace"))
    return f"- `go.mod`：module = `{m.group(1)}`" if m else None


def _cargo_note(repo: Path) -> str | None:
    """Cargo.toml：[package] name。"""
    p = repo / "Cargo.toml"
    if not p.is_file():
        return None
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
        if tomllib is not None:
            name = (tomllib.loads(text).get("package") or {}).get("name") or ""
        else:
            name = _regex_toml_fields(text, "package", ("name",)).get("name", "")
    except Exception:
        return None
    return f"- `Cargo.toml`：package.name = `{name}`" if name else None


def build_map(repo: Path) -> str:
    """扫描 repo 生成 repo map 全文（确定性：同一代码状态逐字节一致）。"""
    repo = Path(repo).resolve()
    files = _git_files(repo)
    source = "git ls-files"
    if files is None:
        files = sorted(_walk_files(repo))
        source = "os.walk（非 git 仓库回退）"
    # .agentpeihe/ 是产物自身所在目录，两种清单路径都统一剔除
    files = sorted(f for f in files if not f.startswith(".agentpeihe/"))
    file_set = set(files)

    lines: list[str] = [
        "# Repo Map",
        "",
        SUBTITLE,
        "",
        "## 概览",
        "",
        f"- 文件总数：{len(files)}",
        f"- 清单来源：{source}",
        "",
        "## 目录结构（两层，按目录聚合文件数）",
        "",
    ]
    lines += _render_tree(files) or ["（空仓库）"]
    lines += ["", "## 清单文件要点", ""]
    notes = [
        n
        for n in (
            _pyproject_note(repo),
            _package_json_note(repo),
            _go_mod_note(repo),
            _cargo_note(repo),
        )
        if n
    ]
    lines += notes or ["（未识别到清单文件）"]
    lines += ["", "## 入口提示", ""]
    hits = sorted(c for c in ENTRY_CANDIDATES if c in file_set)
    lines += [f"- `{c}`" for c in hits] or ["（未识别到常见入口文件）"]
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(
        description="生成目标仓库的稳定骨架 repo map（确定性、零动态字段）"
    )
    ap.add_argument("repo", help="目标仓库路径")
    ap.add_argument(
        "--out", default=None, help="输出路径（默认 <repo>/.agentpeihe/repo_map.md）"
    )
    args = ap.parse_args()

    repo = Path(args.repo).expanduser()
    if not repo.is_dir():
        sys.exit(f"错误：仓库路径不存在或不是目录: {repo}")
    content = build_map(repo)
    out = Path(args.out) if args.out else repo / ".agentpeihe" / "repo_map.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    print(f"写 {out}")


if __name__ == "__main__":
    main()
