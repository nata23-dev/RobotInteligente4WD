"""Regresiones del auditor con secretos sintéticos generados en repos temporales."""

import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import uuid
from scripts import audit_publication as audit


class PublicationAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run_git("init", "--quiet", "--initial-branch=main")
        self.run_git("config", "user.name", "Auditoria fixture")
        self.run_git("config", "user.email", "fixture@example.invalid")
        (self.root / ".gitignore").write_text("config.local.json\n", encoding="utf-8")
        self.value = "fixture-" + uuid.uuid4().hex
        (self.root / "config.local.json").write_text(
            json.dumps({"api_key": self.value}), encoding="utf-8"
        )
        (self.root / "README.md").write_text("Sin credenciales\n", encoding="utf-8")
        self.run_git("add", ".gitignore", "README.md")
        self.run_git("commit", "--quiet", "-m", "base de prueba")

    def tearDown(self):
        self.temp.cleanup()

    def run_git(self, *args):
        return subprocess.check_output(
            [
                "git",
                "-c",
                "core.hooksPath=hooks-no-existentes",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=self.root,
            stderr=subprocess.STDOUT,
        )

    def inspect(self):
        with patch.object(audit, "ROOT", self.root):
            report = audit.audit()
        self.assertNotIn(self.value, json.dumps(report))
        return report

    def test_historical_encoded_secret_survives_current_removal(self):
        encoded = base64.b64encode(self.value.encode()).decode()
        (self.root / "README.md").write_text(encoded, encoding="utf-8")
        self.run_git("add", "README.md")
        self.run_git("commit", "--quiet", "-m", "fixture historico")
        (self.root / "README.md").write_text("Contenido limpio\n", encoding="utf-8")
        self.run_git("add", "README.md")
        self.run_git("commit", "--quiet", "-m", "retira fixture actual")
        report = self.inspect()
        self.assertFalse(report["success"])
        self.assertTrue(any(f["scope"] == "historial" for f in report["findings"]))

    def test_staging_is_scanned_separately_from_clean_worktree(self):
        (self.root / "README.md").write_text(self.value, encoding="utf-8")
        self.run_git("add", "README.md")
        (self.root / "README.md").write_text("Contenido limpio\n", encoding="utf-8")
        report = self.inspect()
        self.assertFalse(report["success"])
        self.assertTrue(any(f["scope"] == "index" for f in report["findings"]))

    def test_private_paths_and_reproducible_templates(self):
        for name in (
            "config.local.json",
            ".env",
            "firmware/secrets.h",
            ".venv/a.py",
            "evidencias/captura.png",
            "respaldo.zip",
        ):
            self.assertTrue(audit.private_path(name), name)
        for name in (
            "config.example.json",
            ".env.example",
            "hardware/bridge.py",
            "dataset/capture.py",
            "firmware/Robot4WD_Firmware_V1/Robot4WD_Firmware_V1.ino",
        ):
            self.assertFalse(audit.private_path(name), name)
        self.assertTrue(self.inspect()["success"])
