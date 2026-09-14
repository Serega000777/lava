from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from typing import Any

from bootstrap_session import extract_cookie
from check_zap_report import main
from prepare_openapi import InvalidOpenApi, filter_schema
from validate_compose_config import validate_compose_config


class BootstrapSessionTests(unittest.TestCase):
    def test_extract_cookie_handles_multiple_set_cookie_headers(self) -> None:
        headers = [
            "other=value; Path=/; HttpOnly",
            "lava_session=secret-token; Path=/; Secure; HttpOnly; SameSite=lax",
        ]

        self.assertEqual(extract_cookie(headers, "lava_session"), "secret-token")

    def test_extract_cookie_rejects_missing_cookie(self) -> None:
        with self.assertRaises(RuntimeError):
            extract_cookie(["other=value; Path=/"], "lava_session")


class ZapPolicyTests(unittest.TestCase):
    def run_policy(self, report: object) -> tuple[int, str, str]:
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(["check_zap_report.py", str(report_path)])
        return result, stdout.getvalue(), stderr.getvalue()

    def test_policy_allows_medium_and_lower_findings(self) -> None:
        report = {
            "site": [
                {
                    "alerts": [
                        {"riskcode": "2", "pluginid": "10001", "name": "Medium"},
                        {"riskcode": "1", "pluginid": "10002", "name": "Low"},
                        {"riskcode": "0", "pluginid": "10003", "name": "Info"},
                    ]
                }
            ]
        }

        result, stdout, stderr = self.run_policy(report)

        self.assertEqual(result, 0)
        self.assertIn("High=0, Medium=1, Low=1, Informational=1", stdout)
        self.assertEqual(stderr, "")

    def test_policy_rejects_high_findings_without_printing_evidence(self) -> None:
        report = {
            "site": [
                {
                    "alerts": [
                        {
                            "riskcode": "3",
                            "pluginid": "40018",
                            "name": "SQL Injection\nvariant",
                            "evidence": "sensitive-response-body",
                        }
                    ]
                }
            ]
        }

        result, _, stderr = self.run_policy(report)

        self.assertEqual(result, 1)
        self.assertIn("40018: SQL Injection variant", stderr)
        self.assertNotIn("sensitive-response-body", stderr)

    def test_policy_rejects_malformed_reports(self) -> None:
        result, _, stderr = self.run_policy({"site": {}})

        self.assertEqual(result, 1)
        self.assertIn("site list", stderr)

    def test_policy_rejects_empty_scans(self) -> None:
        result, _, stderr = self.run_policy({"site": []})

        self.assertEqual(result, 1)
        self.assertIn("at least one scanned site", stderr)


class OpenApiPreparationTests(unittest.TestCase):
    def test_filter_schema_removes_auth_and_internal_paths(self) -> None:
        schema = {
            "openapi": "3.1.0",
            "paths": {
                "/auth/logout": {"post": {}},
                "/internal/metrics": {"get": {}},
                "/me": {"get": {}, "patch": {}},
                "/listings": {"get": {}},
                "/authors": {"get": {}},
            },
        }

        filtered = filter_schema(schema)

        self.assertEqual(set(filtered["paths"]), {"/me", "/listings", "/authors"})
        self.assertIn("/auth/logout", schema["paths"])

    def test_filter_schema_requires_authenticated_probe(self) -> None:
        with self.assertRaises(InvalidOpenApi):
            filter_schema({"openapi": "3.1.0", "paths": {"/health": {"get": {}}}})


class ComposeCredentialTests(unittest.TestCase):
    def compose_config(self) -> dict[str, Any]:
        return {
            "services": {
                "api": {
                    "environment": {
                        "DATABASE_URL": (
                            "postgresql+asyncpg://lava:strong-password@postgres:5432/lava"
                        ),
                        "S3_ACCESS_KEY": "lava-dast",
                        "S3_SECRET_KEY": "strong-object-storage-secret",
                    }
                },
                "postgres": {
                    "environment": {
                        "POSTGRES_DB": "lava",
                        "POSTGRES_USER": "lava",
                        "POSTGRES_PASSWORD": "strong-password",
                    }
                },
                "minio": {
                    "environment": {
                        "MINIO_ROOT_USER": "lava-dast",
                        "MINIO_ROOT_PASSWORD": "strong-object-storage-secret",
                    }
                },
            }
        }

    def test_validator_accepts_consistent_credentials(self) -> None:
        validate_compose_config(self.compose_config())

    def test_validator_rejects_shadowed_postgres_password(self) -> None:
        config = self.compose_config()
        config["services"]["postgres"]["environment"]["POSTGRES_PASSWORD"] = (
            "ambient-runner-password"
        )

        with self.assertRaisesRegex(ValueError, "Postgres passwords differ"):
            validate_compose_config(config)


if __name__ == "__main__":
    unittest.main()
