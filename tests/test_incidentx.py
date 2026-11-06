"""
Offline unit tests for IncidentX agent tools, log parser, and report generator.
No API key or network required — these exercise the deterministic Python logic.
"""

import json
import os

import pytest

from agent.tools import (
    classify_incident_severity,
    correlate_service_errors,
    execute_remediation_action,
    fetch_runbook_remediation,
    parse_and_filter_logs,
    verify_service_health,
    ALL_TOOLS,
)
from utils.log_parser import parse_log_file
from utils.report_generator import generate_postmortem_report

SAMPLE_LOG = json.dumps([
    {"timestamp": "2024-11-07T14:00:00Z", "service": "auth-db", "level": "ERROR", "message": "Connection pool exhausted: 100/100 in use"},
    {"timestamp": "2024-11-07T14:01:00Z", "service": "auth-service", "level": "ERROR", "message": "Cannot acquire connection — 504 upstream timeout"},
    {"timestamp": "2024-11-07T14:02:00Z", "service": "frontend", "level": "CRITICAL", "message": "Checkout flow unavailable"},
])


def test_all_tools_registered():
    assert len(ALL_TOOLS) == 6
    assert {t.name for t in ALL_TOOLS} == {
        "parse_and_filter_logs",
        "correlate_service_errors",
        "classify_incident_severity",
        "fetch_runbook_remediation",
        "execute_remediation_action",
        "verify_service_health",
    }


def test_parse_and_filter_logs_groups_by_service():
    out = parse_and_filter_logs.invoke({"log_text": SAMPLE_LOG})
    assert "PARSED LOG SUMMARY" in out
    assert "[SERVICE: auth-db]" in out
    assert "pool exhausted" in out


def test_parse_and_filter_logs_severity_filter():
    out = parse_and_filter_logs.invoke({"log_text": SAMPLE_LOG, "severity_filter": "CRITICAL"})
    assert "frontend" in out
    assert "auth-service" not in out


def test_parse_and_filter_logs_handles_plain_text():
    out = parse_and_filter_logs.invoke({"log_text": "2024-11-07 ERROR payment-service: HTTP 503"})
    assert "payment-service" in out


def test_correlate_identifies_root_cause_candidate():
    out = correlate_service_errors.invoke({"log_text": SAMPLE_LOG})
    assert "FAILURE CHAIN SUMMARY" in out
    assert "auth-db" in out
    assert "auth-db → auth-service → frontend" in out


def test_classify_severity_db_pool():
    out = classify_incident_severity.invoke({"log_summary": "Connection pool exhausted. Cannot acquire connection."})
    assert "Database Connection Pool Exhaustion" in out
    assert "CRITICAL" in out


def test_classify_severity_oom():
    out = classify_incident_severity.invoke({"log_summary": "OutOfMemoryError: Java heap space, OOMKiller terminated pod"})
    assert "JVM Memory Leak" in out
    assert "HIGH" in out


def test_classify_severity_rate_limit():
    out = classify_incident_severity.invoke({"log_summary": "HTTP 429 rate limit triggered, volumetric attack from single subnet"})
    assert "Rate Limit" in out
    assert "CRITICAL" in out


def test_execute_remediation_has_status():
    out = execute_remediation_action.invoke({"action_type": "kill_idle_db_connections", "target_service": "auth-db"})
    assert "STATUS:" in out
    assert "auth-db" in out


def test_verify_health_all_services():
    out = verify_service_health.invoke({"service_names": "auth-db, auth-service"})
    assert "ALL SERVICES HEALTHY" in out


def test_verify_health_requires_services():
    out = verify_service_health.invoke({"service_names": ""})
    assert out.startswith("ERROR")


def test_fetch_runbook_keyword_routing():
    out = fetch_runbook_remediation.invoke({"incident_type": "JVM Memory Leak"})
    assert "memory_leak_oom" in out


@pytest.mark.parametrize("name,scenario", [
    ("outage_a_db_pool", "db_connection_exhaustion.md"),
    ("outage_b_memory_leak", "memory_leak_oom.md"),
    ("outage_c_rate_limit", "api_rate_limit.md"),
])
def test_scenario_files_are_parseable(name, scenario):
    root = os.path.join(os.path.dirname(__file__), "..")
    with open(os.path.join(root, "data", "scenarios", f"{name}.json"), encoding="utf-8") as f:
        entries = json.load(f)
    assert isinstance(entries, list) and len(entries) > 0
    assert all("service" in e and "level" in e and "message" in e for e in entries)
    assert os.path.exists(os.path.join(root, "data", "runbooks", scenario))


def test_log_parser_json_csv_and_text():
    assert json.loads(parse_log_file(SAMPLE_LOG, "log.json")) == json.loads(SAMPLE_LOG)
    csv_rows = json.loads(parse_log_file("service,level,message\nauth-db,ERROR,pool exhausted", "log.csv"))
    assert csv_rows[0]["service"] == "auth-db" and csv_rows[0]["level"] == "ERROR"
    txt = json.loads(parse_log_file("[2024-11-07T14:00:00Z] [WARN] [svc] slow query", "log.txt"))
    assert txt[0]["level"] == "WARN"


def test_report_generator_contains_sections():
    steps = [{"type": "action", "tool": "correlate_service_errors", "tool_input": "abc", "observation": "chain"}]
    report = generate_postmortem_report("Test Outage", "Root cause: pool leak.", steps)
    assert "INCIDENT POST-MORTEM REPORT" in report
    assert "Test Outage" in report
    assert "correlate_service_errors" in report
