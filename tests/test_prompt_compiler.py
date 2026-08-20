#!/usr/bin/env python3
"""test_prompt_compiler.py — compile_gate_prompt.py / gen_repo_map.py 的单元测试。

覆盖：逐字节确定性、零动态字段（日期/uuid）、三段式结构与顺序、
executor/reviewer 固定头差异、产物指针校验与去重、占位行、
repo map 的 os.walk 回退与 git 双路径、默认输出幂等。
"""
from __future__ import annotations

import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPILE = ROOT / "compile_gate_prompt.py"
GENMAP = ROOT / "gen_repo_map.py"

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
UUID_RE = re.compile(r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}")


def _load(name: str):
    """按路径加载仓库根目录的脚本模块（scripts 非包，走 importlib）。"""
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cgp = _load("compile_gate_prompt")
grm = _load("gen_repo_map")


def run_py(script: Path, *args) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script), *map(str, args)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


class FixtureMixin:
    """非 git fixture 项目：AGENTS.md + pyproject.toml + 若干 .py + 噪音目录。"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "proj"
        self.repo.mkdir()
        (self.repo / "AGENTS.md").write_text(
            "# 项目规范\n\n- 用中文注释\n- 单测必须全绿\n", encoding="utf-8"
        )
        (self.repo / "pyproject.toml").write_text(
            '[project]\nname = "demo-proj"\nversion = "0.1.0"\n\n'
            '[project.scripts]\ndemo-cli = "demo.cli:main"\n',
            encoding="utf-8",
        )
        (self.repo / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")
        demo = self.repo / "src" / "demo"
        demo.mkdir(parents=True)
        (demo / "__init__.py").write_text("", encoding="utf-8")
        (demo / "core.py").write_text("def run():\n    return 1\n", encoding="utf-8")
        (self.repo / "src" / "main.py").write_text(
            "from demo.core import run\n", encoding="utf-8"
        )
        # 噪音目录：os.walk 回退必须排除
        nm = self.repo / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("module.exports = 1\n", encoding="utf-8")
        pc = self.repo / "__pycache__"
        pc.mkdir()
        (pc / "junk.pyc").write_bytes(b"\x00\x01")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _compile(self, *extra, role="executor", mode=None, project=None):
        args = [
            "--project",
            str(project or self.repo),
            "--role",
            role,
            "--gate",
            "G1",
            "--goal",
            "实现核心逻辑",
            "--allowed",
            "读写 src/ 与 tests/",
            "--forbidden",
            "git 提交与推送",
            "--validation",
            "单测全绿",
            "--stop",
            "出现未预期差异",
        ]
        if mode:
            args += ["--mode", mode]
        args += list(extra)
        return run_py(COMPILE, *args)


class CompileTest(FixtureMixin, unittest.TestCase):
    def test_deterministic_byte_identical(self):
        a = self._compile()
        b = self._compile()
        self.assertEqual(a.returncode, 0, a.stderr)
        self.assertEqual(a.stdout, b.stdout)

    def test_no_dynamic_fields(self):
        out = self._compile().stdout
        self.assertIsNone(DATE_RE.search(out), "输出含 ISO 日期")
        self.assertIsNone(UUID_RE.search(out), "输出含 uuid")

    def test_initial_three_sections_ordered(self):
        out = self._compile().stdout
        for marker in ("# [固定头]", "# [本关契约]", "# [产物指针]"):
            self.assertIn(marker, out)
        self.assertLess(out.index("# [固定头]"), out.index("# [本关契约]"))
        self.assertLess(out.index("# [本关契约]"), out.index("# [产物指针]"))
        self.assertIn("## 项目规范（AGENTS.md）", out)
        self.assertIn("## 仓库骨架（repo map）", out)
        self.assertIn("- 用中文注释", out)  # fixture AGENTS.md 原文被嵌入
        for field in (
            "Role: executor",
            "Gate: G1",
            "Goal: 实现核心逻辑",
            "Allowed: 读写 src/ 与 tests/",
            "Forbidden: git 提交与推送",
            "Validation: 单测全绿",
            "Stop: 出现未预期差异",
            "Report: Gate Execution Report",  # 默认值
            "Next Owner: controller",  # 默认值
        ):
            self.assertIn(field, out)

    def test_followup_has_no_fixed_header(self):
        out = self._compile(mode="followup").stdout
        self.assertNotIn("[固定头]", out)
        self.assertIn("# [本关契约]", out)
        self.assertIn("# [产物指针]", out)
        self.assertIn("Gate: G1", out)

    def test_role_headers_differ(self):
        ex = self._compile(role="executor").stdout
        rv = self._compile(role="reviewer").stdout
        self.assertNotEqual(ex, rv)
        self.assertIn("关二爷", ex)
        self.assertIn("法正", rv)
        self.assertIn("独立核验", rv)
        self.assertNotIn("独立核验", ex)
        self.assertIn("Role: reviewer", rv)

    def test_custom_report_and_next_owner(self):
        out = self._compile("--report", "专项核验单", "--next-owner", "主公").stdout
        self.assertIn("Report: 专项核验单", out)
        self.assertIn("Next Owner: 主公", out)

    def test_artifact_invalid_exits_nonzero(self):
        bad = self._compile("--artifact", "没有冒号的指针")
        self.assertNotEqual(bad.returncode, 0)
        self.assertIn("产物指针", bad.stderr)

    def test_artifact_dedupe_and_fullwidth_colon(self):
        ok = self._compile(
            "--artifact",
            "src/demo/core.py: 核心实现",
            "--artifact",
            "src/demo/core.py: 核心实现",
            "--artifact",
            "docs/plan.md：拆解依据",
        )
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(ok.stdout.count("- src/demo/core.py: 核心实现"), 1)  # 去重保序
        self.assertIn("- docs/plan.md: 拆解依据", ok.stdout)  # 全角冒号规范化

    def test_no_artifacts_placeholder(self):
        self.assertIn("（无前置产物）", self._compile().stdout)

    def test_missing_files_placeholders(self):
        empty = Path(self.tmp.name) / "empty"
        empty.mkdir()
        out = self._compile(project=empty).stdout
        self.assertIn("[AGENTS.md 缺失：--project 路径下无此文件]", out)
        self.assertIn("[repo map 缺失：先运行 gen_repo_map.py <project> 生成]", out)

    def test_out_file_overwrite(self):
        target = Path(self.tmp.name) / "out.md"
        r = self._compile("--out", str(target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(target.read_text(encoding="utf-8"), self._compile().stdout)

    def test_reviewer_has_no_history_param(self):
        # 从接口上保证 reviewer 极简上下文：没有任何接收执行者历史的参数
        help_out = run_py(COMPILE, "--help").stdout
        self.assertNotIn("history", help_out.lower())
        self.assertNotIn("executor-output", help_out)
        self.assertNotIn("transcript", help_out.lower())

    def test_initial_embeds_repo_map_when_present(self):
        r = run_py(GENMAP, str(self.repo))
        self.assertEqual(r.returncode, 0, r.stderr)
        out = self._compile().stdout
        self.assertIn("# Repo Map", out)
        self.assertIn("由 gen_repo_map.py 生成", out)
        self.assertIsNone(DATE_RE.search(out))


class StaticAssertTest(unittest.TestCase):
    def test_assert_static(self):
        cgp._assert_static("干净的文本 Role: executor Gate: G1")
        with self.assertRaises(ValueError):
            cgp._assert_static("生成于 2026-08-19 的提示词")
        with self.assertRaises(ValueError):
            cgp._assert_static("id=550e8400-e29b-41d4-a716-446655440000")
        with self.assertRaises(ValueError):
            cgp._assert_static("时间 10:20:30")


class RepoMapWalkTest(FixtureMixin, unittest.TestCase):
    """fixture 非 git 仓库 → 走 os.walk 回退路径。"""

    def test_walk_deterministic_no_date(self):
        a = grm.build_map(self.repo)
        b = grm.build_map(self.repo)
        self.assertEqual(a, b)
        self.assertIsNone(DATE_RE.search(a))
        self.assertIsNone(UUID_RE.search(a))

    def test_walk_content(self):
        out = grm.build_map(self.repo)
        self.assertIn("# Repo Map", out)
        self.assertIn("由 gen_repo_map.py 生成；仓库结构变化时重跑。", out)
        self.assertIn("清单来源：os.walk（非 git 仓库回退）", out)
        self.assertIn("- 文件总数：6", out)
        self.assertIn("- 根目录（3 个文件）", out)
        self.assertIn("- `src/`（3 个文件）", out)
        self.assertIn("- `src/demo/`（2 个文件）", out)
        # 噪音目录被排除
        self.assertNotIn("node_modules", out)
        self.assertNotIn("__pycache__", out)
        # 清单文件要点
        self.assertIn("project.name = `demo-proj`", out)
        self.assertIn("scripts = `demo-cli`", out)
        # 入口提示（字典序）
        self.assertLess(out.index("- `main.py`"), out.index("- `src/main.py`"))

    def test_cli_default_out_idempotent(self):
        for _ in range(2):
            r = run_py(GENMAP, str(self.repo))
            self.assertEqual(r.returncode, 0, r.stderr)
        p = self.repo / ".agentpeihe" / "repo_map.md"
        content = p.read_text(encoding="utf-8")
        # 再跑一次，产物自身所在目录被剔除 → 逐字节一致（幂等）
        r = run_py(GENMAP, str(self.repo))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(p.read_text(encoding="utf-8"), content)
        self.assertNotIn(".agentpeihe", content)

    def test_cli_custom_out(self):
        target = Path(self.tmp.name) / "custom.md"
        r = run_py(GENMAP, str(self.repo), "--out", str(target))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(target.read_text(encoding="utf-8").startswith("# Repo Map"))

    def test_cli_bad_repo_exits_nonzero(self):
        r = run_py(GENMAP, str(Path(self.tmp.name) / "不存在"))
        self.assertNotEqual(r.returncode, 0)


class RepoMapGitTest(unittest.TestCase):
    """git 仓库 fixture → 走 git ls-files 路径（环境不允许则 skip）。"""

    def setUp(self) -> None:
        if not shutil.which("git"):
            self.skipTest("环境无 git")
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "gproj"
        self.repo.mkdir()
        (self.repo / "a.py").write_text("x = 1\n", encoding="utf-8")
        (self.repo / "README.md").write_text("# demo\n", encoding="utf-8")
        try:
            subprocess.run(
                ["git", "init", "-q"], cwd=self.repo, check=True, capture_output=True
            )
            subprocess.run(
                ["git", "add", "-A"], cwd=self.repo, check=True, capture_output=True
            )
            subprocess.run(
                [
                    "git",
                    "-c",
                    "user.email=t@example.com",
                    "-c",
                    "user.name=t",
                    "commit",
                    "-q",
                    "-m",
                    "init",
                ],
                cwd=self.repo,
                check=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, OSError) as e:
            self.skipTest(f"git 初始化失败: {e}")
        # 未跟踪但未忽略 → 计入；被 gitignore → 不计入
        (self.repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (self.repo / "new.py").write_text("y = 2\n", encoding="utf-8")
        (self.repo / "ignored.txt").write_text("z\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_git_path_deterministic(self):
        a = grm.build_map(self.repo)
        b = grm.build_map(self.repo)
        self.assertEqual(a, b)
        self.assertIn("清单来源：git ls-files", a)
        self.assertIn("- 文件总数：4", a)  # a.py README.md .gitignore new.py
        self.assertIn("- 根目录（4 个文件）", a)
        self.assertNotIn("ignored.txt", a)
        self.assertIn("（未识别到清单文件）", a)
        self.assertIsNone(DATE_RE.search(a))


if __name__ == "__main__":
    unittest.main()
