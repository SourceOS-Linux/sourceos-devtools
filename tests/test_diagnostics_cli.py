"""Unit tests for sourceosctl diagnostics commands."""

import json
import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from sourceosctl.commands import diagnostics


class TestDiagnosticsCommands(unittest.TestCase):
    def test_redact_masks_sensitive_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            in_path = pathlib.Path(tmp) / "diagnostic.log"
            out_path = pathlib.Path(tmp) / "diagnostic.redacted.log"
            in_path.write_text(
                "\n".join(
                    [
                        "cookie: session=abc123",
                        "Authorization: Bearer super-secret-bearer-token",
                        'api_key: "abc123"',
                        'user_id: "user-42"',
                        'prompt: "Summarize private model prompt"',
                        "<policy-marked>never expose this snippet</policy-marked>",
                    ]
                ),
                encoding="utf-8",
            )
            rc = diagnostics.diagnostics_main(["redact", str(in_path), "--output", str(out_path)])
            self.assertEqual(rc, 0)
            redacted = out_path.read_text(encoding="utf-8")
            self.assertNotIn("abc123", redacted)
            self.assertNotIn("super-secret-bearer-token", redacted)
            self.assertNotIn("Summarize private model prompt", redacted)
            self.assertIn("<redacted-cookie>", redacted)
            self.assertIn("<redacted-token>", redacted)
            self.assertIn("<redacted-prompt>", redacted)
            self.assertIn("<redacted-policy-snippet>", redacted)

    def test_redact_json_preserves_json_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            in_path = pathlib.Path(tmp) / "diagnostic.json"
            out_path = pathlib.Path(tmp) / "diagnostic.redacted.json"
            in_path.write_text(
                json.dumps(
                    {
                        "user_id": "user-123",
                        "prompt": "Line one\nLine two",
                        "authorization": "Bearer abcDEF123",
                    }
                ),
                encoding="utf-8",
            )
            rc = diagnostics.diagnostics_main(["redact", str(in_path), "--output", str(out_path)])
            self.assertEqual(rc, 0)
            payload = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["user_id"], "<redacted-id>")
            self.assertEqual(payload["prompt"], "<redacted-prompt>")
            self.assertEqual(payload["authorization"], "<redacted-secret>")


if __name__ == "__main__":
    unittest.main()
