#!/usr/bin/env python3
import os
import sys
import tempfile
import unittest
from pathlib import Path


class TestAinfoSandbox(unittest.TestCase):
    def test_no_unexpanded_tilde_in_sandbox_profile(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            h = tmpdir
            old_home = os.environ.get("HOME")
            old_ai_home = os.environ.get("AI_HOME")
            old_ainfo_state = os.environ.get("AINFO_STATE_DIR")
            try:
                os.environ["HOME"] = h
                os.environ["AI_HOME"] = "~/aihome"
                if "AINFO_STATE_DIR" in os.environ:
                    del os.environ["AINFO_STATE_DIR"]

                # Ensure a fresh import
                sys.path.insert(0, str(Path(__file__).parent / "../../ainfo"))
                if "ainfo_mcp" in sys.modules:
                    del sys.modules["ainfo_mcp"]

                import ainfo_mcp

                self.assertTrue(
                    ainfo_mcp.STATE_DIR.startswith(os.path.join(h, "aihome")),
                    f"STATE_DIR {ainfo_mcp.STATE_DIR} should start with {os.path.join(h, 'aihome')}",
                )

                profile_text = ainfo_mcp.sandbox_profile()
                if os.path.exists(profile_text):
                    with open(profile_text) as f:
                        profile_text = f.read()

                expected = os.path.join(h, "aihome")
                self.assertIn(expected, profile_text)
                self.assertIn(os.path.join(h, "aihome", "guard"), profile_text)
                self.assertNotIn("~", profile_text)
            finally:
                if old_home is not None:
                    os.environ["HOME"] = old_home
                else:
                    os.environ.pop("HOME", None)
                if old_ai_home is not None:
                    os.environ["AI_HOME"] = old_ai_home
                else:
                    os.environ.pop("AI_HOME", None)
                if old_ainfo_state is not None:
                    os.environ["AINFO_STATE_DIR"] = old_ainfo_state
                else:
                    os.environ.pop("AINFO_STATE_DIR", None)
                sys.path.pop(0)
                if "ainfo_mcp" in sys.modules:
                    del sys.modules["ainfo_mcp"]


if __name__ == "__main__":
    unittest.main()
