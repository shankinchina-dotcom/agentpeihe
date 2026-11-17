#!/usr/bin/env python3
"""test_controller_bundle.py — gen_controller_bundle.py 的 prompt 尺寸硬门单测。

覆盖：硬上限常量口径（12*1024 UTF-8 字节）、95% 预警、默认 detect fixture 可构建且不误伤、
边界 12288B 放行 / 12289B 拒绝（报错含实际字节数且 build 不返回 → main 不落盘）、
尺寸口径只量 prompt 块（os_env/guardrails/tools 不计入）。
不读真实凭证：det 为内存 dict，不经 detect() / 网络 / CLI。
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    """按路径加载仓库根目录的脚本模块（scripts 非包，走 importlib）。"""
    spec = importlib.util.spec_from_file_location(
        "gen_controller_bundle", ROOT / "gen_controller_bundle.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gcb = _load()

# 轻量 det：只有 kimi 可用（brain 显式 "kimi"），不触发任何 CLI/凭证嗅探
DET = {
    "has_claude": False,
    "claude_vendor": None,
    "has_codex": False,
    "has_pi": False,
    "has_kimi": True,
    "has_grok": False,
    "has_codebuddy": False,
    "has_hermes": False,
    "hermes_model": None,
    "hermes_provider": None,
    "hermes_plan_model": None,
    "cooldowns": {},
    "pi_providers": [],
}


class PromptSizeGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self._orig_tmpl = gcb.CONTROLLER_PROMPT_TMPL

    def tearDown(self) -> None:
        gcb.CONTROLLER_PROMPT_TMPL = self._orig_tmpl

    def _pad(self, target: int) -> None:
        """把 prompt 补到指定字节数：基准构建一次，按差值在模板尾部补 x。"""
        files, *_ = gcb.build(dict(DET), "kimi")
        base = gcb.prompt_block_bytes(files["config.yaml"])
        gcb.CONTROLLER_PROMPT_TMPL = self._orig_tmpl + "x" * (target - base)

    def test_limit_constant(self):
        self.assertEqual(gcb.PROMPT_SIZE_LIMIT_BYTES, 12 * 1024)
        self.assertEqual(gcb.PROMPT_WARNING_THRESHOLD_BYTES, int(12 * 1024 * 0.95))

    def test_no_warning_at_threshold(self):
        self._pad(gcb.PROMPT_WARNING_THRESHOLD_BYTES)
        files, *_ = gcb.build(dict(DET), "kimi")
        self.assertIsNone(gcb.prompt_size_warning(files["config.yaml"]))

    def test_warning_above_threshold(self):
        self._pad(gcb.PROMPT_WARNING_THRESHOLD_BYTES + 1)
        files, *_ = gcb.build(dict(DET), "kimi")
        warning = gcb.prompt_size_warning(files["config.yaml"])
        self.assertIsNotNone(warning)
        self.assertIn(str(gcb.PROMPT_WARNING_THRESHOLD_BYTES + 1), warning)
        self.assertIn("95%", warning)

    def test_default_build_under_limit(self):
        files, workers, brain, _notes = gcb.build(dict(DET), "kimi")
        self.assertEqual(brain, "kimi")
        self.assertIn("config.yaml", files)
        self.assertIn("agents/exec_moonshot/config.yaml", files)
        size = gcb.prompt_block_bytes(files["config.yaml"])
        self.assertLessEqual(size, gcb.PROMPT_SIZE_LIMIT_BYTES)

    def test_boundary_12288_passes(self):
        self._pad(12 * 1024)
        files, *_ = gcb.build(dict(DET), "kimi")
        self.assertEqual(
            gcb.prompt_block_bytes(files["config.yaml"]), gcb.PROMPT_SIZE_LIMIT_BYTES
        )

    def test_boundary_12289_rejected(self):
        self._pad(12 * 1024 + 1)
        with self.assertRaises(SystemExit) as cm:
            gcb.build(dict(DET), "kimi")
        msg = str(cm.exception)
        self.assertIn(str(12 * 1024 + 1), msg)  # 报错带实际字节数
        self.assertIn(str(12 * 1024), msg)  # 报错带上限

    def test_oversize_blocks_return(self):
        # build() 不返回 → main() 拿不到 files → 写盘循环不会执行（阻止写文件）
        self._pad(12 * 1024 + 64)
        with self.assertRaises(SystemExit):
            gcb.build(dict(DET), "kimi")

    def test_size_covers_prompt_block_only(self):
        files, *_ = gcb.build(dict(DET), "kimi")
        yaml_text = files["config.yaml"]
        self.assertIn("prompt: |", yaml_text)
        self.assertLess(
            gcb.prompt_block_bytes(yaml_text),
            len(yaml_text.encode("utf-8")),
        )


if __name__ == "__main__":
    unittest.main()
