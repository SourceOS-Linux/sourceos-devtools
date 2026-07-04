"""Tests for unsafe local persistence scanner."""

import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts import scan_local_persistence


class TestLocalPersistenceScanner(unittest.TestCase):
    def test_scan_detects_high_risk_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            sample = root / "bad.plist"
            sample.write_text(
                """
<plist>
<dict>
<key>KeepAlive</key><true/>
<string>/Library/LaunchAgents/org.example.agent.plist</string>
<string>/tmp/example.log</string>
<string>us-central1-docker.pkg.dev/example/image:dev</string>
</dict>
</plist>
""".strip()
            )
            findings = scan_local_persistence.scan(root, include_docs=True)
        ids = {finding.rule_id for finding in findings}
        self.assertIn("launchd-keepalive-true", ids)
        self.assertIn("launchd-root-user-agent", ids)
        self.assertIn("tmp-product-log", ids)
        self.assertIn("direct-google-artifact-runtime", ids)

    def test_scan_ignores_markdown_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "README.md").write_text("/Library/LaunchAgents/example.plist\n")
            findings = scan_local_persistence.scan(root, include_docs=False)
        self.assertEqual(findings, [])

    def test_scan_can_include_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "README.md").write_text("/Library/LaunchAgents/example.plist\n")
            findings = scan_local_persistence.scan(root, include_docs=True)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].rule_id, "launchd-root-user-agent")

    def test_main_fail_on_high(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "bad.sh").write_text("gcloud.auth.docker-helper\n")
            rc = scan_local_persistence.main([str(root), "--fail-on", "high"])
        self.assertEqual(rc, 1)

    def test_main_fail_on_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "bad.sh").write_text("gcloud.auth.docker-helper\n")
            rc = scan_local_persistence.main([str(root), "--fail-on", "none"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
