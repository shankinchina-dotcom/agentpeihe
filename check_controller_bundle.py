#!/usr/bin/env python3
"""check_controller_bundle.py — 只读对账：生成计划 vs 已部署 controller bundle。

复用同目录 gen_controller_bundle.py 的 detect()/build() 算出期望文件集合，
与已部署目录（默认 ~/.omnigent/agents/controller）逐项比对：缺失 / 额外 /
内容漂移。顶层 config.yaml description 的生成日期归一化后比较；
报告只输出路径与哈希，不打印配置正文或敏感值。本脚本只读，不写入任何文件。

退出码: 0 = 一致；1 = 漂移；2 = 输入或运行错误（argparse 用法错误同为 2）。

用法:
  python3 check_controller_bundle.py [--brain claude-sdk|codex|pi|kimi] [--no-codex] [--deployed PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import re
import sys
from pathlib import Path
from typing import NamedTuple

GEN_DATE_RE = re.compile(r"生成（\d{4}-\d{2}-\d{2}）")
DATE_PLACEHOLDER = "生成（<生成日期>）"
HASH_LEN = 12

DEFAULT_DEPLOYED = Path.home() / ".omnigent" / "agents" / "controller"


class BundleDiff(NamedTuple):
    matched: int
    missing: list[str]
    extra: list[str]
    changed: list[tuple[str, str, str]]  # (路径, 期望哈希, 实际哈希)

    @property
    def drift(self) -> bool:
        return bool(self.missing or self.extra or self.changed)


def normalize_expected(rel: str, content: str) -> str:
    if rel == "config.yaml":
        return GEN_DATE_RE.sub(DATE_PLACEHOLDER, content)
    return content


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def expected_hashes(files: dict[str, str]) -> dict[str, str]:
    return {rel: hash_text(normalize_expected(rel, c)) for rel, c in files.items()}


def collect_dir_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        raise FileNotFoundError(f"已部署目录不存在或不是目录: {root}")
    return {
        p.relative_to(root).as_posix(): _hash_deployed_file(root, p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _hash_deployed_file(root: Path, p: Path) -> str:
    rel = p.relative_to(root).as_posix()
    if rel == "config.yaml":
        try:
            return hash_text(normalize_expected(rel, p.read_text(encoding="utf-8")))
        except UnicodeDecodeError:
            pass
    return hashlib.sha256(p.read_bytes()).hexdigest()


def compare_bundles(expected: dict[str, str], deployed: dict[str, str]) -> BundleDiff:
    missing = sorted(set(expected) - set(deployed))
    extra = sorted(set(deployed) - set(expected))
    changed = [
        (rel, expected[rel][:HASH_LEN], deployed[rel][:HASH_LEN])
        for rel in sorted(set(expected) & set(deployed))
        if expected[rel] != deployed[rel]
    ]
    matched = len(set(expected) & set(deployed)) - len(changed)
    return BundleDiff(matched, missing, extra, changed)


def load_generator():
    gen_path = Path(__file__).resolve().parent / "gen_controller_bundle.py"
    if not gen_path.is_file():
        raise FileNotFoundError(f"同目录生成器缺失: {gen_path}")
    spec = importlib.util.spec_from_file_location("gen_controller_bundle", gen_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _print_report(
    root: Path,
    brain: str,
    expected: dict[str, str],
    actual: dict[str, str],
    diff: BundleDiff,
) -> None:
    print(f"== 对账：生成计划 vs {root} ==")
    print(f"大脑: {brain}  期望 {len(expected)} 个文件，已部署 {len(actual)} 个")
    print(f"一致: {diff.matched}")
    if diff.missing:
        print("缺失（计划有、已部署无）:")
        for rel in diff.missing:
            print(f"  - {rel}")
    if diff.extra:
        print("额外（已部署有、计划无）:")
        for rel in diff.extra:
            print(f"  - {rel}")
    if diff.changed:
        print("内容漂移:")
        for rel, want, got in diff.changed:
            print(f"  - {rel}  期望 {want}…  实际 {got}…")
    print("结论: " + ("漂移，需重跑 gen_controller_bundle.py" if diff.drift else "一致"))


def run_check(
    brain: str | None = None,
    no_codex: bool = False,
    deployed: Path | None = None,
    gen=None,
) -> int:
    try:
        gen = gen or load_generator()
        root = Path(deployed).expanduser() if deployed else DEFAULT_DEPLOYED
        det = gen.detect()
        try:
            files, _workers, brain, _notes = gen.build(det, brain, no_codex=no_codex)
        except SystemExit as e:
            raise RuntimeError(f"生成器 build 拒绝当前参数: {e}") from None
        expected = expected_hashes(files)
        actual = collect_dir_hashes(root)
    except (OSError, RuntimeError) as e:
        print(f"错误: {e}", file=sys.stderr)
        return 2
    diff = compare_bundles(expected, actual)
    _print_report(root, brain, expected, actual, diff)
    return 1 if diff.drift else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="只读对账：gen_controller_bundle.py 生成计划 vs 已部署 bundle"
    )
    ap.add_argument("--brain", choices=["claude-sdk", "codex", "pi", "kimi"], default=None)
    ap.add_argument("--no-codex", action="store_true", help="codex 不进池（与生成器同义）")
    ap.add_argument(
        "--deployed",
        default=None,
        help="已部署 bundle 目录（默认 ~/.omnigent/agents/controller）",
    )
    args = ap.parse_args(argv)
    return run_check(
        brain=args.brain,
        no_codex=args.no_codex,
        deployed=Path(args.deployed) if args.deployed else None,
    )


if __name__ == "__main__":
    sys.exit(main())
