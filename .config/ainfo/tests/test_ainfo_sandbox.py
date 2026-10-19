#!/usr/bin/env python3
"""A leading ~ in AI_HOME is expanded for STATE_DIR and the sandbox profile.
Run: PYTHONDONTWRITEBYTECODE=1 python3 .config/ainfo/tests/test_ainfo_sandbox.py
"""
import importlib
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestAinfoSandbox(unittest.TestCase):
    def test_tilde_ai_home_is_expanded(self):
        with tempfile.TemporaryDirectory() as h, mock.patch.dict(os.environ, {"HOME": h, "AI_HOME": "~/aihome"}):
            os.environ.pop("AINFO_STATE_DIR", None)
            sys.modules.pop("ainfo_mcp", None)
            m = importlib.import_module("ainfo_mcp")
            try:
                ai = os.path.join(h, "aihome")
                self.assertTrue(m.STATE_DIR.startswith(ai + "/"), m.STATE_DIR)
                with open(m.sandbox_profile()) as f:
                    prof = f.read()
                self.assertIn(f'(subpath "{ai}")', prof)
                self.assertIn(f'(deny file-write* (subpath "{os.path.join(ai, "guard")}")', prof)
                self.assertNotIn("~", prof)
            finally:
                sys.modules.pop("ainfo_mcp", None)


if __name__ == "__main__":
    unittest.main()
