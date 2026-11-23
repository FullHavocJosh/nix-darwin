"""Test aidev_guard.py: read_tool_log function."""

import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "aidev_guard", os.path.join(HERE, "..", "aidev_guard.py")
)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

read_tool_log = a.read_tool_log

FAILS = []


def check(name, cond, extra=""):
    print(
        f"{'PASS' if cond else 'FAIL'}: {name}"
        + (f" ({extra})" if extra and not cond else "")
    )
    if not cond:
        FAILS.append(name)


class TestReadToolLog:
    """Tests for read_tool_log function."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def make_file(self, lines):
        """Create a temp file with the given lines."""
        path = os.path.join(self.tmpdir, "log.bin")
        with open(path, "wb") as f:
            for line in lines:
                if isinstance(line, str):
                    f.write(line.encode("utf-8"))
                else:
                    f.write(line)
                f.write(b"\n")
        return path

    def make_file_no_final_newline(self, lines):
        """Create a temp file with the given lines, no trailing newline on last line."""
        path = os.path.join(self.tmpdir, "log.bin")
        with open(path, "wb") as f:
            for i, line in enumerate(lines):
                if isinstance(line, str):
                    f.write(line.encode("utf-8"))
                else:
                    f.write(line)
                if i != len(lines) - 1:
                    f.write(b"\n")
        return path

    def test_two_full_lines_partial_third(self):
        """A temp file with 2 full lines and a partial third returns
        2 calls and an offset before the partial line.
        """
        lines = [
            json.dumps({"tool": "read", "args": '{"path": "foo.txt"}', "out": "bar\n"}),
            json.dumps({"tool": "bash", "args": '{"cmd": "echo hi"}', "out": "hi\n"}),
            '{"partial": true',  # partial line, not valid JSON
        ]
        path = self.make_file_no_final_newline(lines)
        calls, offset = read_tool_log(path)
        check("two full lines, partial third returns 2 calls", len(calls) == 2)
        check("first call is read", calls[0]["tool"] == "read")
        check("first call args correct", calls[0]["args"] == '{"path": "foo.txt"}')
        check("first call out correct", calls[0]["out"] == "bar\n")
        check("second call is bash", calls[1]["tool"] == "bash")
        check("second call args correct", calls[1]["args"] == '{"cmd": "echo hi"}')
        check("second call out correct", calls[1]["out"] == "hi\n")
        check("offset is positive", offset > 0)

    def test_resume_from_partial_then_complete(self):
        """A second call from that offset after the line completes returns 1 call."""
        lines = [
            json.dumps({"tool": "read", "args": '{"path": "foo.txt"}', "out": "bar\n"}),
            json.dumps({"tool": "bash", "args": '{"cmd": "echo hi"}', "out": "hi\n"}),
            '{"partial": true',  # partial line
        ]
        path = self.make_file_no_final_newline(lines)
        calls, offset = read_tool_log(path)
        check("first read returns 2 calls", len(calls) == 2)

        # Now read again from the offset
        # Append the rest of the partial line and complete it
        append_data = ', "tool": "bash", "args": "{\\"cmd\\": \\"echo bye\\"}", "out": "bye\\n"}'
        with open(path, "ab") as f:
            f.write(append_data.encode("utf-8"))
            f.write(b"\n")

        calls2, _ = read_tool_log(path, offset)
        check("resume read returns 1 call", len(calls2) == 1)
        check("resumed call is bash", calls2[0]["tool"] == "bash")
        check("resumed call args correct", calls2[0]["args"] == '{"cmd": "echo bye"}')
        check("resumed call out correct", calls2[0]["out"] == "bye\n")

    def test_garbage_line_skipped(self):
        """A garbage line is skipped. Note: the last line is not complete, so it's not returned."""
        lines = [
            json.dumps({"tool": "read", "args": '{"path": "foo.txt"}', "out": "bar\n"}),
            "this is not json at all!!!",
            json.dumps({"tool": "bash", "args": '{"cmd": "echo hi"}', "out": "hi\n"}),
        ]
        path = self.make_file_no_final_newline(lines)
        calls, _ = read_tool_log(path)
        # First line is a complete JSON line, second is garbage (skipped), third is not complete (not returned)
        check("garbage line skipped, 1 call returned", len(calls) == 1)
        check("first call is read", calls[0]["tool"] == "read")

    def test_missing_file(self):
        """A missing file returns ([], offset)."""
        path = os.path.join(self.tmpdir, "nonexistent.bin")
        calls, offset = read_tool_log(path)
        check("missing file returns empty list", calls == [])
        check("missing file offset is 0", offset == 0)


if __name__ == "__main__":
    import json

    test = TestReadToolLog()
    test.setUp()
    try:
        test.test_two_full_lines_partial_third()
        test.test_resume_from_partial_then_complete()
        test.test_garbage_line_skipped()
        test.test_missing_file()
    finally:
        test.tearDown()

    print()
    if FAILS:
        print(f"Failed tests: {FAILS}")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)
