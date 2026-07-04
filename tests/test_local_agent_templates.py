"""Tests for local-agent backend template validation."""

import pathlib
import sys
import tempfile
import unittest

_REPO_ROOT = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from scripts import validate_local_agent_templates


class TestLocalAgentTemplateValidator(unittest.TestCase):
    def test_repository_templates_validate(self):
        findings = validate_local_agent_templates.validate(_REPO_ROOT)
        self.assertEqual(findings, [])

    def test_rejects_restart_always(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            templates = root / "sourceosctl" / "local_agents" / "templates"
            templates.mkdir(parents=True)
            (templates / "bad.service.tmpl").write_text(
                """
[Service]
Restart=always
RestartSec={{restart_sec}}
StartLimitIntervalSec={{start_limit_interval_sec}}
StartLimitBurst={{start_limit_burst}}
Environment=CONTAINERS_AUTH_FILE={{authfile}}
""".strip()
            )
            findings = validate_local_agent_templates.validate(root)
        self.assertTrue(any("Restart=always" in f.message for f in findings))

    def test_rejects_quadlet_missing_authfile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            templates = root / "sourceosctl" / "local_agents" / "templates"
            templates.mkdir(parents=True)
            (templates / "bad.container.tmpl").write_text(
                """
[Container]
Image={{runtime_image}}
Pull=never
AutoUpdate=registry-disabled
[Service]
Restart={{restart}}
RestartSec={{restart_sec}}
StartLimitIntervalSec={{start_limit_interval_sec}}
StartLimitBurst={{start_limit_burst}}
""".strip()
            )
            findings = validate_local_agent_templates.validate(root)
        self.assertTrue(any("AuthFile={{authfile}}" in f.message for f in findings))


if __name__ == "__main__":
    unittest.main()
