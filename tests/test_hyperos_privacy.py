"""Offline tests for MyAndroid/bin/hyperos-privacy HMA policy loading and XML sanitization."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "bin" / "hyperos-privacy"
EXAMPLE_POLICY = REPO_ROOT / "templates" / "hyperos-privacy" / "hma-policy.example.json"


def _load_hyperos_module():
    loader = importlib.machinery.SourceFileLoader("hyperos_privacy_mod", str(SCRIPT_PATH))
    spec = importlib.util.spec_from_loader("hyperos_privacy_mod", loader)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["hyperos_privacy_mod"] = module
    loader.exec_module(module)
    return module


HP = _load_hyperos_module()


class HyperosPrivacyPolicyTests(unittest.TestCase):
    def test_example_policy_template_loads_and_filters_blur_categories(self) -> None:
        policy = HP.load_hma_policy(EXAMPLE_POLICY)
        self.assertIn("me.weishu.kernelsu", policy.hide_root)
        self.assertIn("com.follow.clash", policy.hide_sensitive)
        self.assertEqual(policy.domestic_scoped_apps, ("com.example.banking", "com.example.payment"))
        self.assertTrue(policy.blur_re.search("com.follow.clash"))

        xml_in = (
            "<map>"
            '<boolean name="key_is_guard_support" value="true" />'
            '<string name="privacy_thumbnail_blur_category">{"com.follow.clash":1,"com.example.ok":2}</string>'
            "</map>"
        )
        cleaned = HP.clean_remote_provider_xml(xml_in, ["com.follow.clash"], policy)
        self.assertIn('value="false"', cleaned)
        self.assertNotIn("com.follow.clash\\\":1", cleaned)
        self.assertIn("com.example.ok", cleaned)

    def test_explicit_missing_or_invalid_policy_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            bad = Path(tmpdir) / "bad.json"
            bad.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")
            with self.assertRaises(ValueError):
                HP.load_hma_policy(bad)
            with self.assertRaises(FileNotFoundError):
                HP.load_hma_policy(Path(tmpdir) / "missing.json")


if __name__ == "__main__":
    unittest.main()
