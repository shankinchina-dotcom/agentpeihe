#!/usr/bin/env python3
"""test_controller_bundle_check.py — check_controller_bundle.py 的单元测试。

覆盖：顶层 config.yaml 生成日期归一化、目录哈希收集（嵌套/排序/缺失报错）、
纯比较函数（一致/缺失/额外/漂移）、run_check 退出码（0 一致 / 1 漂移 / 2 错误）、
brain 与 no_codex 透传、build 拒绝转 2、报告只含路径与哈希不含配置正文。
全部走临时目录，detect/build 均 mock，不碰真实 CLI、真实 home 或网络。
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
CHECK = ROOT / "check_controller_bundle.py"

TOP_CONFIG = "description: 三国总控。本文件由 gen_controller_bundle.py 生成（{date}），请勿手改。\n"
WORKER_CONFIG = "name: exec_demo\nprompt: |\n  干活。api_key: sk-fake-secret-值不外泄\n"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cbc = _load("check_controller_bundle")


def _fake_gen(files: dict[str, str], brain: str = "codex"):
    gen = SimpleNamespace()

    def _detect() -> dict:
        return {"_fake": True}

    def _build(det, brain_arg=None, no_codex=False):
        return files, [], brain_arg or brain, []

    gen.detect = _detect
    gen.build = _build
    return gen


def _build_refusing_gen(message: str):
    gen = _fake_gen({})

    def _build(det, brain_arg=None, no_codex=False):
        raise SystemExit(message)

    gen.build = _build
    return gen


def _capture(fn, *args, **kwargs):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = fn(*args, **kwargs)
    return code, out.getvalue(), err.getvalue()


class DeployedMixin:
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.deployed = Path(self.tmp.name) / "controller"
        self.deployed.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _write_deployed(self, rel: str, content: str) -> None:
        p = self.deployed / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")

    def _plan(self) -> dict[str, str]:
        return {
            "config.yaml": TOP_CONFIG.format(date="2026-11-17"),
            "agents/exec_demo/config.yaml": WORKER_CONFIG,
        }


class NormalizeTest(unittest.TestCase):
    def test_top_config_date_normalized(self):
        raw = TOP_CONFIG.format(date="2026-11-17")
        self.assertEqual(
            cbc.normalize_expected("config.yaml", raw),
            TOP_CONFIG.format(date="<生成日期>"),
        )

    def test_worker_config_date_kept(self):
        raw = WORKER_CONFIG.replace("干活。", "干活。生成（2026-01-01）")
        self.assertEqual(cbc.normalize_expected("agents/exec_demo/config.yaml", raw), raw)

    def test_expected_hashes_date_insensitive(self):
        a = cbc.expected_hashes({"config.yaml": TOP_CONFIG.format(date="2026-11-17")})
        b = cbc.expected_hashes({"config.yaml": TOP_CONFIG.format(date="2026-09-01")})
        self.assertEqual(a, b)

    def test_expected_hashes_other_files_date_sensitive(self):
        a = cbc.expected_hashes(
            {"agents/exec_demo/config.yaml": WORKER_CONFIG.replace("干活。", "干活。生成（2026-01-01）")}
        )
        b = cbc.expected_hashes({"agents/exec_demo/config.yaml": WORKER_CONFIG})
        self.assertNotEqual(a["agents/exec_demo/config.yaml"], b["agents/exec_demo/config.yaml"])


class CollectDirHashesTest(DeployedMixin, unittest.TestCase):
    def test_nested_sorted_posix_keys(self):
        self._write_deployed("agents/b/config.yaml", "b\n")
        self._write_deployed("agents/a/config.yaml", "a\n")
        self._write_deployed("config.yaml", "top\n")
        got = cbc.collect_dir_hashes(self.deployed)
        self.assertEqual(list(got), ["agents/a/config.yaml", "agents/b/config.yaml", "config.yaml"])
        self.assertEqual(got["config.yaml"], cbc.hash_text("top\n"))

    def test_top_config_date_normalized_on_disk(self):
        self._write_deployed("config.yaml", TOP_CONFIG.format(date="2026-09-01"))
        got = cbc.collect_dir_hashes(self.deployed)
        want = cbc.expected_hashes({"config.yaml": TOP_CONFIG.format(date="2026-11-17")})
        self.assertEqual(got["config.yaml"], want["config.yaml"])

    def test_missing_dir_raises(self):
        with self.assertRaises(FileNotFoundError):
            cbc.collect_dir_hashes(self.deployed / "不存在")

    def test_file_as_root_raises(self):
        f = Path(self.tmp.name) / "普通文件"
        f.write_text("x", encoding="utf-8")
        with self.assertRaises(FileNotFoundError):
            cbc.collect_dir_hashes(f)


class CompareBundlesTest(unittest.TestCase):
    def test_identical(self):
        d = {"config.yaml": "h1", "agents/a/config.yaml": "h2"}
        diff = cbc.compare_bundles(d, dict(d))
        self.assertFalse(diff.drift)
        self.assertEqual(diff.matched, 2)
        self.assertEqual((diff.missing, diff.extra, diff.changed), ([], [], []))

    def test_missing_extra_changed(self):
        expected = {"config.yaml": "h1", "agents/a/config.yaml": "h2", "agents/b/config.yaml": "h3"}
        deployed = {"config.yaml": "h9", "agents/a/config.yaml": "h2", "agents/旧/config.yaml": "h4"}
        diff = cbc.compare_bundles(expected, deployed)
        self.assertTrue(diff.drift)
        self.assertEqual(diff.missing, ["agents/b/config.yaml"])
        self.assertEqual(diff.extra, ["agents/旧/config.yaml"])
        self.assertEqual(diff.changed, [("config.yaml", "h1", "h9")])
        self.assertEqual(diff.matched, 1)

    def test_empty_deployed_all_missing(self):
        diff = cbc.compare_bundles({"config.yaml": "h1"}, {})
        self.assertEqual(diff.missing, ["config.yaml"])
        self.assertTrue(diff.drift)

    def test_empty_expected_all_extra(self):
        diff = cbc.compare_bundles({}, {"config.yaml": "h1"})
        self.assertEqual(diff.extra, ["config.yaml"])
        self.assertTrue(diff.drift)

    def test_changed_hashes_truncated(self):
        full = cbc.hash_text("x")
        diff = cbc.compare_bundles({"config.yaml": full}, {"config.yaml": cbc.hash_text("y")})
        self.assertEqual(len(diff.changed[0][1]), cbc.HASH_LEN)


class RunCheckTest(DeployedMixin, unittest.TestCase):
    def _deploy_plan(self, files: dict[str, str]) -> None:
        for rel, content in files.items():
            self._write_deployed(rel, content)

    def test_consistent_exit_0(self):
        plan = self._plan()
        self._deploy_plan(plan)
        code, out, err = _capture(
            cbc.run_check, gen=_fake_gen(plan), deployed=self.deployed
        )
        self.assertEqual(code, 0, err)
        self.assertIn("结论: 一致", out)
        self.assertIn("一致: 2", out)

    def test_deployed_date_skew_still_consistent(self):
        plan = self._plan()
        deployed = dict(plan)
        deployed["config.yaml"] = TOP_CONFIG.format(date="2026-09-01")
        self._deploy_plan(deployed)
        code, out, err = _capture(
            cbc.run_check, gen=_fake_gen(plan), deployed=self.deployed
        )
        self.assertEqual(code, 0, err)
        self.assertNotIn("内容漂移", out)

    def test_content_drift_exit_1(self):
        plan = self._plan()
        deployed = dict(plan)
        deployed["agents/exec_demo/config.yaml"] = WORKER_CONFIG + "手改一行\n"
        self._deploy_plan(deployed)
        code, out, err = _capture(
            cbc.run_check, gen=_fake_gen(plan), deployed=self.deployed
        )
        self.assertEqual(code, 1, err)
        self.assertIn("agents/exec_demo/config.yaml", out)
        self.assertIn("内容漂移", out)
        self.assertIn("结论: 漂移", out)
        self.assertNotIn("手改一行", out)  # 报告不含配置正文
        self.assertNotIn("sk-fake-secret", out)  # 报告不含敏感值

    def test_missing_and_extra_exit_1(self):
        plan = self._plan()
        deployed = {"config.yaml": plan["config.yaml"]}
        self._deploy_plan(deployed)
        self._write_deployed("agents/残留/config.yaml", "旧副本\n")
        code, out, err = _capture(
            cbc.run_check, gen=_fake_gen(plan), deployed=self.deployed
        )
        self.assertEqual(code, 1, err)
        self.assertIn("缺失", out)
        self.assertIn("agents/exec_demo/config.yaml", out)
        self.assertIn("额外", out)
        self.assertIn("agents/残留/config.yaml", out)
        self.assertNotIn("旧副本", out)

    def test_missing_deployed_dir_exit_2(self):
        code, out, err = _capture(
            cbc.run_check,
            gen=_fake_gen(self._plan()),
            deployed=self.deployed / "不存在",
        )
        self.assertEqual(code, 2)
        self.assertIn("已部署目录不存在", err)

    def test_build_refusal_exit_2(self):
        code, out, err = _capture(
            cbc.run_check,
            gen=_build_refusing_gen("错误：--brain claude-sdk 但当前 Claude 实际 vendor=deepseek"),
            deployed=self.deployed,
        )
        self.assertEqual(code, 2)
        self.assertIn("build 拒绝", err)

    def test_brain_and_no_codex_forwarded(self):
        seen = {}
        gen = _fake_gen(self._plan())
        orig_build = gen.build

        def _build(det, brain_arg=None, no_codex=False):
            seen["brain"], seen["no_codex"] = brain_arg, no_codex
            return orig_build(det, brain_arg, no_codex)

        gen.build = _build
        code, out, err = _capture(
            cbc.run_check, brain="kimi", no_codex=True, gen=gen, deployed=self.deployed
        )
        self.assertEqual(code, 1, err)  # 计划未部署 → 全缺失
        self.assertEqual(seen, {"brain": "kimi", "no_codex": True})
        self.assertIn("大脑: kimi", out)

    def test_load_generator_used_by_default(self):
        plan = self._plan()
        self._deploy_plan(plan)
        fake = _fake_gen(plan)
        orig = cbc.load_generator
        cbc.load_generator = lambda: fake
        try:
            code, out, err = _capture(cbc.run_check, deployed=self.deployed)
        finally:
            cbc.load_generator = orig
        self.assertEqual(code, 0, err)
        self.assertIn("结论: 一致", out)


class MainTest(DeployedMixin, unittest.TestCase):
    def test_main_argv_consistent(self):
        plan = self._plan()
        for rel, content in plan.items():
            self._write_deployed(rel, content)
        fake = _fake_gen(plan)
        orig = cbc.load_generator
        cbc.load_generator = lambda: fake
        try:
            code, out, err = _capture(
                cbc.main, ["--deployed", str(self.deployed), "--no-codex"]
            )
        finally:
            cbc.load_generator = orig
        self.assertEqual(code, 0, err)
        self.assertIn("结论: 一致", out)

    def test_main_bad_brain_exits_2(self):
        with self.assertRaises(SystemExit) as cm:
            _capture(cbc.main, ["--brain", "bogus"])
        self.assertEqual(cm.exception.code, 2)

    def test_main_drift_exit_1(self):
        plan = self._plan()
        self._write_deployed("config.yaml", plan["config.yaml"])
        fake = _fake_gen(plan)
        orig = cbc.load_generator
        cbc.load_generator = lambda: fake
        try:
            code, out, err = _capture(cbc.main, ["--deployed", str(self.deployed)])
        finally:
            cbc.load_generator = orig
        self.assertEqual(code, 1, err)


if __name__ == "__main__":
    unittest.main()
