"""
tools.py — All 6 diagnostic tool functions that the IncidentX Agent can call.

These are real Python functions registered as LangChain tools.
The agent (Gemini) autonomously decides when and how to call each tool.
"""

import json
import random
import re
from datetime import datetime, timezone
from typing import Optional

from langchain.tools import tool


# ---------------------------------------------------------------------------
# TOOL 1: Parse and Filter Logs
# ---------------------------------------------------------------------------
@tool
def parse_and_filter_logs(log_text: str, severity_filter: str = "ALL") -> str:
    """
    Parse raw log text (JSON array or plain text) and filter by severity level.
    Use this tool first to understand what events are present in the incident logs.

    Args:
        log_text: Raw log content as a string (JSON array of log objects, or plain text lines).
        severity_filter: One of 'ALL', 'ERROR', 'WARN', 'CRITICAL', 'ALERT'. Defaults to 'ALL'.

    Returns:
        A structured summary of parsed log entries grouped by service and severity.
    """
    try:
        entries = json.loads(log_text)
    except (json.JSONDecodeError, TypeError):
        # Fallback: treat as plain-text log lines
        entries = []
        for line in str(log_text).splitlines():
            line = line.strip()
            if not line:
                continue
            level = "INFO"
            for lvl in ["CRITICAL", "ALERT", "ERROR", "WARN", "INFO", "DEBUG"]:
                if lvl in line.upper():
                    level = lvl
                    break
            entries.append({"timestamp": "", "service": "unknown", "level": level, "message": line})

    if not entries:
        return "No log entries found in input."

    # Apply severity filter
    if severity_filter != "ALL":
        allowed = severity_filter.upper().split(",")
        entries = [e for e in entries if e.get("level", "").upper() in allowed]

    # Group by service
    services = {}
    for entry in entries:
        svc = entry.get("service", "unknown")
        services.setdefault(svc, []).append(entry)

    lines = [f"=== PARSED LOG SUMMARY === ({len(entries)} entries after filtering) ===\n"]
    for svc, logs in services.items():
        lines.append(f"\n[SERVICE: {svc}] — {len(logs)} entries")
        for log in logs:
            ts = log.get("timestamp", "N/A")
            level = log.get("level", "INFO")
            msg = log.get("message", "")
            lines.append(f"  [{ts}] [{level}] {msg}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# TOOL 2: Correlate Service Errors (Identify Cascading Failure Chain)
# ---------------------------------------------------------------------------
@tool
def correlate_service_errors(log_text: str, time_window_seconds: int = 300) -> str:
    """
    Correlate error events across multiple services within a time window to identify
    cascading failure chains. This reveals which service failed FIRST and caused
    downstream failures in dependent services.

    Args:
        log_text: Raw log content as a JSON string (array of log objects with timestamps).
        time_window_seconds: The time window in seconds within which to correlate events. Default is 300 (5 minutes).

    Returns:
        A cascading failure chain analysis showing the temporal sequence of service failures.
    """
    try:
        entries = json.loads(log_text)
    except (json.JSONDecodeError, TypeError):
        return "ERROR: Could not parse log entries as JSON for correlation."

    # Filter only error-level entries
    error_entries = [
        e for e in entries
        if e.get("level", "").upper() in ["ERROR", "CRITICAL", "ALERT", "WARN"]
    ]

    if not error_entries:
        return "No error-level entries found for correlation analysis."

    # Sort by timestamp
    def parse_ts(ts_str):
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.min.replace(tzinfo=timezone.utc)

    error_entries.sort(key=lambda e: parse_ts(e.get("timestamp", "")))

    # Find first failure (anchor point)
    anchor = error_entries[0]
    anchor_time = parse_ts(anchor.get("timestamp", ""))

    # Build timeline with relative times
    chain = []
    for entry in error_entries:
        entry_time = parse_ts(entry.get("timestamp", ""))
        delta = (entry_time - anchor_time).total_seconds()
        chain.append({
            "delta_seconds": delta,
            "service": entry.get("service", "unknown"),
            "level": entry.get("level", ""),
            "message": entry.get("message", "")[:120]
        })

    output = ["=== CASCADING FAILURE CHAIN ANALYSIS ===\n"]
    output.append(f"Correlation window: {time_window_seconds} seconds")
    output.append(f"First failure detected at: {anchor.get('timestamp', 'unknown')}\n")
    output.append("FAILURE TIMELINE (relative to first event):\n")

    seen_services = []
    for event in chain:
        t = event["delta_seconds"]
        svc = event["service"]
        is_new = svc not in seen_services
        if is_new:
            seen_services.append(svc)
            arrow = "🔴 ROOT CAUSE CANDIDATE →" if len(seen_services) == 1 else f"⬇ CASCADE TO '{svc}' →"
        else:
            arrow = f"   (continued '{svc}') →"
        output.append(f"  T+{int(t):>4}s  {arrow}  [{event['level']}] {event['message']}")

    output.append(f"\n=== FAILURE CHAIN SUMMARY ===")
    output.append(f"Affected services (in order of first failure): {' → '.join(seen_services)}")
    output.append(f"Root cause candidate: '{seen_services[0]}' (failed first at T+0s)")

    return "\n".join(output)


# ---------------------------------------------------------------------------
# TOOL 3: Classify Incident Type and Severity
# ---------------------------------------------------------------------------
@tool
def classify_incident_severity(log_summary: str) -> str:
    """
    Classify the incident type and assign a severity level (Low / Medium / High / Critical)
    based on the log summary. Also identifies the blast radius (impact scope).

    Args:
        log_summary: A text summary of the incident from parse_and_filter_logs or correlate_service_errors.

    Returns:
        Incident classification with severity level, incident type, and blast radius.
    """
    summary_upper = log_summary.upper()

    # Determine incident type
    if any(kw in summary_upper for kw in ["POOL EXHAUSTED", "TOO MANY CONNECTIONS", "CANNOT ACQUIRE"]):
        incident_type = "Database Connection Pool Exhaustion"
        severity = "CRITICAL"
        blast_radius = "Full service outage — all users unable to complete authenticated transactions"
    elif any(kw in summary_upper for kw in ["OUTOFMEMORYERROR", "OOM", "HEAP SPACE", "OOMKILLER", "SIGKILL"]):
        incident_type = "JVM Memory Leak / Out-Of-Memory Kill"
        severity = "HIGH"
        blast_radius = "Specific service offline — dependent services degraded, personalization/recommendations unavailable"
    elif any(kw in summary_upper for kw in ["429", "RATE LIMIT", "DDOS", "VOLUMETRIC", "BOTNET", "SUBNET"]):
        incident_type = "API Rate Limit Breach / Suspected DDoS Attack"
        severity = "CRITICAL"
        blast_radius = "API layer saturated — legitimate users experiencing 503s and extreme latency"
    elif any(kw in summary_upper for kw in ["504", "GATEWAY TIMEOUT", "UPSTREAM"]):
        incident_type = "Cascading API Gateway Timeout"
        severity = "HIGH"
        blast_radius = "End-users receiving errors — revenue-impacting if payment or checkout involved"
    elif any(kw in summary_upper for kw in ["CRASHLOOPBACKOFF", "EXIT CODE 137", "POD RESTART"]):
        incident_type = "Kubernetes Pod CrashLoopBackOff"
        severity = "HIGH"
        blast_radius = "Service unavailable — Kubernetes restarting pod repeatedly, users seeing 503"
    elif any(kw in summary_upper for kw in ["DNS", "NETWORK POLICY", "CONNECTION REFUSED"]):
        incident_type = "Network Connectivity Failure"
        severity = "MEDIUM"
        blast_radius = "Inter-service communication disrupted — partial feature degradation"
    else:
        incident_type = "Unclassified Service Anomaly"
        severity = "MEDIUM"
        blast_radius = "Unknown impact — further investigation required"

    # Count critical/error events
    critical_count = summary_upper.count("CRITICAL")
    error_count = summary_upper.count("ERROR")
    alert_count = summary_upper.count("ALERT")

    output = [
        "=== INCIDENT CLASSIFICATION REPORT ===\n",
        f"Incident Type    : {incident_type}",
        f"Severity Level   : ⚠️  {severity}",
        f"Blast Radius     : {blast_radius}",
        f"",
        f"Event Counts:",
        f"  🔴 CRITICAL events : {critical_count}",
        f"  🟠 ERROR events    : {error_count}",
        f"  🚨 ALERT events    : {alert_count}",
        f"",
        f"SLA Impact: {'YES — SLA breach likely' if severity == 'CRITICAL' else 'At risk' if severity == 'HIGH' else 'Monitoring required'}",
        f"On-call escalation required: {'YES' if severity in ['CRITICAL', 'HIGH'] else 'NO'}"
    ]

    return "\n".join(output)


# ---------------------------------------------------------------------------
# TOOL 4: Fetch Runbook Remediation (RAG-powered)
# ---------------------------------------------------------------------------
@tool
def fetch_runbook_remediation(incident_type: str) -> str:
    """
    Search the engineering runbook knowledge base for validated remediation steps
    matching the identified incident type. Uses keyword matching against available runbooks.

    Args:
        incident_type: The type of incident identified (e.g., 'Database Connection Pool Exhaustion',
                       'JVM Memory Leak', 'DDoS Attack', 'Network Timeout').

    Returns:
        Relevant runbook content with specific remediation steps for this incident type.
    """
    # Import the RAG module
    try:
        from agent.runbook_rag import search_runbooks
        result = search_runbooks(incident_type)
        return result
    except Exception as e:
        # Fallback: keyword-based routing
        itype = incident_type.upper()
        if any(kw in itype for kw in ["DATABASE", "CONNECTION", "POOL", "POSTGRES", "MYSQL"]):
            runbook = "db_connection_exhaustion"
        elif any(kw in itype for kw in ["MEMORY", "OOM", "HEAP", "JVM", "LEAK"]):
            runbook = "memory_leak_oom"
        elif any(kw in itype for kw in ["RATE", "DDOS", "429", "VOLUMETRIC", "ATTACK"]):
            runbook = "api_rate_limit"
        elif any(kw in itype for kw in ["NETWORK", "TIMEOUT", "DNS", "CONNECTIVITY"]):
            runbook = "network_timeout"
        else:
            runbook = "service_restart"

        import os
        base = os.path.join(os.path.dirname(__file__), "..", "data", "runbooks")
        path = os.path.join(base, f"{runbook}.md")
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return f"=== RUNBOOK RETRIEVED: {runbook}.md ===\n\n{content}"
        except FileNotFoundError:
            return f"ERROR: Runbook '{runbook}.md' not found. Check /data/runbooks directory."


# ---------------------------------------------------------------------------
# TOOL 5: Execute Remediation Action (Simulated)
# ---------------------------------------------------------------------------
@tool
def execute_remediation_action(action_type: str, target_service: str) -> str:
    """
    Execute (or simulate) a remediation action against a target service.
    This tool simulates real production actions like killing idle DB connections,
    restarting pods, blocking IPs, or adjusting resource limits.

    Args:
        action_type: The remediation action to execute. Examples:
                     'kill_idle_db_connections', 'restart_pod', 'block_ip_subnet',
                     'scale_up_replicas', 'increase_pool_size', 'flush_cache'
        target_service: The name of the service or resource to target (e.g., 'auth-db', 'payment-gateway').

    Returns:
        Execution log showing what was done and the simulated system response.
    """
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    action = action_type.lower()

    if "kill_idle" in action or "connection" in action:
        output = [
            f"[{timestamp}] EXECUTING: Kill idle database connections on '{target_service}'",
            f"  → Querying pg_stat_activity for idle connections > 5 min...",
            f"  → Found: 47 idle connections (avg idle time: 18.3 min)",
            f"  → Terminating connections... ✅ 47 connections killed",
            f"  → Current pool utilization: 23/100 (was: 100/100)",
            f"  → Connection pool pressure: NORMAL",
            f"STATUS: ✅ Action completed successfully in 2.1s"
        ]
    elif "restart" in action or "pod" in action:
        output = [
            f"[{timestamp}] EXECUTING: Rolling restart of pod/service '{target_service}'",
            f"  → Triggering: kubectl rollout restart deployment/{target_service}",
            f"  → Old pod terminating... (graceful shutdown: 15s)",
            f"  → New pod starting...",
            f"  → Health check: /health → HTTP 200 OK (latency: 42ms)",
            f"  → Readiness probe: /ready → HTTP 200 OK",
            f"  → Rollout completed. All replicas healthy.",
            f"STATUS: ✅ Pod restarted successfully in 28s"
        ]
    elif "block" in action or "ip" in action or "subnet" in action:
        output = [
            f"[{timestamp}] EXECUTING: Block attacking subnet for '{target_service}'",
            f"  → Identifying top-offending subnet...",
            f"  → Subnet identified: 203.0.113.0/24 (generating 6,800 req/min)",
            f"  → Adding to WAF blocklist: 203.0.113.0/24",
            f"  → WAF rule created: Block all ingress from 203.0.113.0/24",
            f"  → iptables rule applied at kernel level",
            f"  → Traffic from subnet: 0 req/min (blocked ✅)",
            f"  → Legitimate traffic restoring to baseline...",
            f"STATUS: ✅ Subnet blocked successfully in 3.4s"
        ]
    elif "scale" in action or "replica" in action:
        output = [
            f"[{timestamp}] EXECUTING: Scale up replicas for '{target_service}'",
            f"  → Current replicas: 3",
            f"  → Target replicas: 8",
            f"  → Triggering: kubectl scale deployment/{target_service} --replicas=8",
            f"  → New pods starting... (5 pods being provisioned)",
            f"  → All 8 pods healthy and serving traffic",
            f"STATUS: ✅ Scaled from 3 → 8 replicas in 45s"
        ]
    elif "pool" in action or "increase" in action:
        output = [
            f"[{timestamp}] EXECUTING: Increase connection pool size for '{target_service}'",
            f"  → Current pool max: 100",
            f"  → New pool max: 200",
            f"  → Applying config change via kubectl set env...",
            f"  → Service reloading config (no downtime)...",
            f"  → Pool size updated: 200 max connections",
            f"STATUS: ✅ Pool size increased in 5.2s"
        ]
    else:
        output = [
            f"[{timestamp}] EXECUTING: {action_type} on '{target_service}'",
            f"  → Sending command to operations automation layer...",
            f"  → Command acknowledged and executed",
            f"  → System response: OK",
            f"STATUS: ✅ Action completed"
        ]

    return "\n".join(output)


# ---------------------------------------------------------------------------
# TOOL 6: Verify Service Health Post-Remediation
# ---------------------------------------------------------------------------
@tool
def verify_service_health(service_names: str) -> str:
    """
    Run health checks on one or more services to verify they have recovered
    after remediation actions. Call this as the final step to confirm resolution.

    Args:
        service_names: Comma-separated list of service names to verify
                       (e.g., 'auth-db,auth-service,payment-gateway').

    Returns:
        Health check results for each service, confirming recovery or identifying lingering issues.
    """
    services = [s.strip() for s in service_names.split(",") if s.strip()]
    if not services:
        return "ERROR: No service names provided."

    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    output = [f"=== SERVICE HEALTH VERIFICATION === [{timestamp}]\n"]

    overall_healthy = True
    for svc in services:
        # Simulate health check results (all healthy after remediation)
        latency = random.randint(20, 95)
        status = "HEALTHY"
        http_code = 200
        output.append(f"  🔍 Checking: {svc}")
        output.append(f"      Endpoint   : http://{svc}/health")
        output.append(f"      HTTP Status: {http_code} OK")
        output.append(f"      Latency    : {latency}ms")
        output.append(f"      Status     : ✅ {status}")
        output.append("")

    output.append("=" * 50)
    if overall_healthy:
        output.append("🟢 ALL SERVICES HEALTHY — Incident RESOLVED ✅")
        output.append(f"Incident closed at: {timestamp}")
    else:
        output.append("🔴 SOME SERVICES STILL DEGRADED — Further investigation required")

    return "\n".join(output)


# ---------------------------------------------------------------------------
# Tool registry for the agent
# ---------------------------------------------------------------------------
ALL_TOOLS = [
    parse_and_filter_logs,
    correlate_service_errors,
    classify_incident_severity,
    fetch_runbook_remediation,
    execute_remediation_action,
    verify_service_health,
]
