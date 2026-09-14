"""Validate the ZAP JSON report and enforce Lava's DAST risk policy."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

RISK_NAMES = {"0": "Informational", "1": "Low", "2": "Medium", "3": "High"}


class InvalidReport(ValueError):
    """Raised when a scanner report does not match the expected safe subset."""


def load_alerts(path: Path) -> list[dict[str, Any]]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InvalidReport(f"cannot read valid JSON from {path}: {error}") from error

    if not isinstance(report, dict) or not isinstance(report.get("site"), list):
        raise InvalidReport("report must contain a site list")
    if not report["site"]:
        raise InvalidReport("report must contain at least one scanned site")

    alerts: list[dict[str, Any]] = []
    for site in report["site"]:
        if not isinstance(site, dict) or not isinstance(site.get("alerts"), list):
            raise InvalidReport("every site must contain an alerts list")
        for alert in site["alerts"]:
            if not isinstance(alert, dict):
                raise InvalidReport("every alert must be an object")
            risk_code = str(alert.get("riskcode", ""))
            if risk_code not in RISK_NAMES:
                raise InvalidReport(f"alert contains unsupported risk code {risk_code!r}")
            alerts.append(alert)
    return alerts


def safe_alert_label(alert: dict[str, Any]) -> str:
    plugin_id = " ".join(str(alert.get("pluginid", "unknown")).split())[:32]
    name = " ".join(str(alert.get("name") or alert.get("alert") or "unnamed").split())
    return f"{plugin_id}: {name[:160]}"


def enforce_policy(alerts: list[dict[str, Any]]) -> None:
    counts = Counter(RISK_NAMES[str(alert["riskcode"])] for alert in alerts)
    summary = ", ".join(
        f"{name}={counts.get(name, 0)}"
        for name in ("High", "Medium", "Low", "Informational")
    )
    print(f"ZAP alert summary: {summary}")

    high_alerts = [alert for alert in alerts if str(alert["riskcode"]) == "3"]
    if high_alerts:
        print("Blocking HIGH risk alerts:", file=sys.stderr)
        for alert in high_alerts[:20]:
            print(f"- {safe_alert_label(alert)}", file=sys.stderr)
        if len(high_alerts) > 20:
            print(f"- ... and {len(high_alerts) - 20} more", file=sys.stderr)
        raise RuntimeError("DAST policy rejects HIGH risk alerts")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_zap_report.py <zap-report.json>", file=sys.stderr)
        return 2
    try:
        enforce_policy(load_alerts(Path(argv[1])))
    except (InvalidReport, RuntimeError) as error:
        print(f"DAST policy failed: {error}", file=sys.stderr)
        return 1
    print("DAST policy passed: no HIGH risk alerts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
