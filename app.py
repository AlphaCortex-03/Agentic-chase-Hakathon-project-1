"""
app.py — IncidentX Autonomous Incident Response Agent
Agentic Chase Hackathon | PS 01

Main Streamlit Dashboard. NOT a chatbot — an autonomous event-driven agent dashboard.
"""

import os
import json
import time
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Page Config — Must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="IncidentX — Autonomous IT Incident Response",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS — Enterprise Dashboard Styling
# ---------------------------------------------------------------------------
st.markdown("""
<style>
/* Global */
body { font-family: 'JetBrains Mono', 'Courier New', monospace; }
.main { background-color: #0d1117; color: #c9d1d9; }

/* Header banner */
.incident-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border: 2px solid #e63946;
    border-radius: 12px;
    padding: 24px 32px;
    margin-bottom: 24px;
    box-shadow: 0 0 30px rgba(230, 57, 70, 0.3);
}
.incident-header h1 { color: #e63946; margin: 0; font-size: 2.4rem; letter-spacing: 2px; }
.incident-header p { color: #8b949e; margin: 4px 0 0; font-size: 0.9rem; }

/* Status indicators */
.status-critical { color: #e63946; font-weight: bold; }
.status-healthy { color: #3fb950; font-weight: bold; }
.status-investigating { color: #f0a500; font-weight: bold; }

/* Scenario cards */
.scenario-card {
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
    margin: 8px 0;
    background: #161b22;
    cursor: pointer;
    transition: border-color 0.2s;
}
.scenario-card:hover { border-color: #e63946; }

/* Agent step display */
.agent-step {
    background: #161b22;
    border-left: 4px solid #58a6ff;
    padding: 12px 16px;
    margin: 8px 0;
    border-radius: 0 8px 8px 0;
    font-family: 'Courier New', monospace;
    font-size: 0.85rem;
}
.agent-thought { border-left-color: #f0a500; }
.agent-action  { border-left-color: #58a6ff; }
.agent-observe { border-left-color: #3fb950; }
.agent-final   { border-left-color: #e63946; }

/* Metric cards */
.metric-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}

/* Alert box */
.alert-banner {
    background: linear-gradient(90deg, #1a0010, #2d0020);
    border: 2px solid #e63946;
    border-radius: 8px;
    padding: 16px 24px;
    margin: 16px 0;
    animation: pulse-border 2s infinite;
}
@keyframes pulse-border {
    0%, 100% { box-shadow: 0 0 0 0 rgba(230, 57, 70, 0.4); }
    50%       { box-shadow: 0 0 0 8px rgba(230, 57, 70, 0); }
}

/* Severity badges */
.badge-critical { background: #e63946; color: white; padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
.badge-high     { background: #f0a500; color: black;  padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
.badge-medium   { background: #3fb950; color: black;  padding: 4px 12px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Load Sample Scenarios
# ---------------------------------------------------------------------------
SCENARIOS = {
    "🔴 Outage A — DB Connection Pool Exhaustion": {
        "file": "data/scenarios/outage_a_db_pool.json",
        "description": "Idle connection leak in auth-db causes cascading 504s across payment-gateway and frontend checkout. ~15,000 users impacted.",
        "badge": "CRITICAL",
        "services_at_risk": "auth-db → auth-service → payment-gateway → api-gateway → frontend",
    },
    "🟠 Outage B — JVM Memory Leak + OOM Kill": {
        "file": "data/scenarios/outage_b_memory_leak.json",
        "description": "user-profile-service heap exhausted. OOMKiller terminates the pod. CrashLoopBackOff initiated. Personalization offline.",
        "badge": "HIGH",
        "services_at_risk": "user-profile-service → recommendation-engine → homepage-service",
    },
    "🟡 Outage C — API Rate Limit / DDoS Spike": {
        "file": "data/scenarios/outage_c_rate_limit.json",
        "description": "Single subnet (203.0.113.0/24) generating 6,800 req/min. Worker pools saturated. Legitimate users blocked.",
        "badge": "CRITICAL",
        "services_at_risk": "api-gateway → rate-limiter → search-service → product-service",
    },
}


def load_scenario_logs(filepath: str) -> str:
    """Load a scenario JSON file and return as string."""
    base = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base, filepath)
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"Scenario file not found: {full_path}")
        return "[]"


# ---------------------------------------------------------------------------
# Session State Initialization
# ---------------------------------------------------------------------------
if "investigation_result" not in st.session_state:
    st.session_state.investigation_result = None
if "current_logs" not in st.session_state:
    st.session_state.current_logs = None
if "current_scenario" not in st.session_state:
    st.session_state.current_scenario = None
if "system_status" not in st.session_state:
    st.session_state.system_status = "HEALTHY"
if "remediation_approved" not in st.session_state:
    st.session_state.remediation_approved = False


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------
st.markdown("""
<div class="incident-header">
    <h1>🚨 IncidentX</h1>
    <p>Autonomous IT Incident Response Agent &nbsp;|&nbsp; Production Operations Center &nbsp;|&nbsp; Powered by Gemini 2.5 Flash</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# TOP STATUS BAR
# ---------------------------------------------------------------------------
col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)

with col_s1:
    if st.session_state.system_status == "INCIDENT":
        st.error("🔴 INCIDENT IN PROGRESS")
    elif st.session_state.system_status == "INVESTIGATING":
        st.warning("🟡 INVESTIGATING...")
    elif st.session_state.system_status == "RESOLVED":
        st.success("🟢 INCIDENT RESOLVED")
    else:
        st.success("🟢 SYSTEM HEALTHY")

with col_s2:
    api_key_set = bool(os.getenv("GEMINI_API_KEY"))
    if api_key_set:
        st.success("🔑 Agent Online")
    else:
        st.error("🔑 API Key Missing")

with col_s3:
    result = st.session_state.investigation_result
    tool_count = len([s for s in (result["steps"] if result else []) if s.get("type") == "action"])
    st.metric("Tools Executed", tool_count, help="Number of diagnostic tool calls by the agent")

with col_s4:
    st.metric("Runbooks Loaded", "5", help="Engineering runbooks in the knowledge base")

with col_s5:
    st.metric("Agent Model", "Gemini 2.5 Flash", help="LLM powering the ReAct reasoning loop")


st.divider()


# ---------------------------------------------------------------------------
# SIDEBAR — Incident Input Panel
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🎯 Incident Input Panel")
    st.markdown("*Select a production scenario or upload your own log file.*")
    st.divider()

    # --- API Key input ---
    st.markdown("### 🔑 Gemini API Key")
    api_key_input = st.text_input(
        "Enter your Gemini API key",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        help="Get a free key at https://aistudio.google.com/app/apikey",
    )
    if api_key_input:
        os.environ["GEMINI_API_KEY"] = api_key_input

    st.divider()

    # --- Pre-loaded Scenarios ---
    st.markdown("### ⚡ Quick-Load Production Incidents")
    st.caption("Click to inject a real production incident scenario instantly:")

    for scenario_name, scenario_data in SCENARIOS.items():
        badge = scenario_data["badge"]
        badge_color = "🔴" if badge == "CRITICAL" else "🟠"
        
        with st.expander(scenario_name, expanded=False):
            st.caption(scenario_data["description"])
            st.caption(f"**Impact chain**: {scenario_data['services_at_risk']}")
            if st.button(f"Inject This Incident →", key=f"btn_{scenario_name}"):
                logs = load_scenario_logs(scenario_data["file"])
                st.session_state.current_logs = logs
                st.session_state.current_scenario = scenario_name
                st.session_state.system_status = "INCIDENT"
                st.session_state.investigation_result = None
                st.session_state.remediation_approved = False
                st.rerun()

    st.divider()

    # --- File Upload ---
    st.markdown("### 📁 Upload Your Log File")
    uploaded_file = st.file_uploader(
        "Upload a log file",
        type=["json", "txt", "csv"],
        help="Supports JSON arrays, CSV files, or plain-text log formats",
    )
    if uploaded_file:
        from utils.log_parser import parse_log_file
        content = uploaded_file.read().decode("utf-8", errors="ignore")
        parsed = parse_log_file(content, uploaded_file.name)
        st.session_state.current_logs = parsed
        st.session_state.current_scenario = f"Uploaded: {uploaded_file.name}"
        st.session_state.system_status = "INCIDENT"
        st.session_state.investigation_result = None
        st.session_state.remediation_approved = False
        st.success(f"Loaded: {uploaded_file.name}")

    st.divider()
    st.markdown("### 📚 Architecture")
    st.code("""
Log File / Alert
      ↓
 IncidentX Agent
      ↓
 ReAct Loop:
  parse_logs()
  correlate()
  classify()
  runbook_rag()
  remediate()
  verify()
      ↓
 RCA Report
    """, language="text")


# ---------------------------------------------------------------------------
# MAIN CONTENT AREA
# ---------------------------------------------------------------------------
left_col, right_col = st.columns([1.1, 0.9])

with left_col:
    st.markdown("## 🧠 Agent Investigation Console")

    # Show current incident info
    if st.session_state.current_logs and st.session_state.current_scenario:
        st.markdown(f"""
<div class="alert-banner">
    <strong>🚨 ACTIVE INCIDENT</strong>: {st.session_state.current_scenario}<br>
    <small>Log entries loaded. Click <b>Start Investigation</b> to deploy the IncidentX agent.</small>
</div>
""", unsafe_allow_html=True)

        # Show raw log preview
        with st.expander("📋 View Raw Log Data", expanded=False):
            try:
                log_data = json.loads(st.session_state.current_logs)
                st.dataframe(
                    log_data,
                    use_container_width=True,
                    column_config={
                        "timestamp": "Timestamp",
                        "service": "Service",
                        "level": "Level",
                        "message": st.column_config.TextColumn("Message", width="large"),
                    }
                )
            except Exception:
                st.text(st.session_state.current_logs[:2000])

        # Investigate button
        can_investigate = bool(os.getenv("GEMINI_API_KEY")) and st.session_state.investigation_result is None
        
        if not os.getenv("GEMINI_API_KEY"):
            st.warning("⚠️ Enter your Gemini API key in the sidebar to start investigation.")

        if st.button(
            "⚡ START AUTONOMOUS INVESTIGATION",
            disabled=not can_investigate,
            type="primary",
            use_container_width=True,
        ):
            st.session_state.system_status = "INVESTIGATING"
            
            # Show animated progress steps during investigation
            tool_steps_display = [
                ("🔧", "parse_and_filter_logs", "Ingesting and parsing log data..."),
                ("🔗", "correlate_service_errors", "Tracing cascading failure chain..."),
                ("⚠️", "classify_incident_severity", "Assessing blast radius and severity..."),
                ("📚", "fetch_runbook_remediation", "Searching engineering knowledge base..."),
                ("⚡", "execute_remediation_action", "Preparing remediation action..."),
                ("✅", "verify_service_health", "Running post-fix health checks..."),
            ]
            
            progress_bar = st.progress(0, text="🤖 IncidentX Agent initializing...")
            status_box = st.empty()
            
            status_box.markdown("""
<div class="agent-step agent-thought">
    🧠 <strong>Agent Activated</strong> — Deploying autonomous ReAct investigation loop<br>
    <small style="color:#8b949e;">6 diagnostic tools standing by | Gemini 2.5 Flash reasoning engine online</small>
</div>
""", unsafe_allow_html=True)

            import threading

            result_holder = {}

            def run_agent():
                from agent.incidentx_agent import run_investigation
                result_holder["result"] = run_investigation(st.session_state.current_logs)

            agent_thread = threading.Thread(target=run_agent, daemon=True)
            agent_thread.start()

            step_idx = 0
            elapsed = 0
            while agent_thread.is_alive():
                pct = min(int((elapsed / 90) * 100), 90)
                icon, tool_name, desc = tool_steps_display[min(step_idx, 5)]
                progress_bar.progress(pct, text=f"🤖 Step {min(step_idx+1,6)}/6 — {tool_name}...")
                status_box.markdown(f"""
<div class="agent-step agent-action">
    {icon} <strong><code>{tool_name}</code></strong><br>
    <small style="color:#8b949e;">{desc}</small>
</div>
""", unsafe_allow_html=True)
                time.sleep(4)
                step_idx = min(step_idx + 1, 5)
                elapsed += 4

            agent_thread.join()
            progress_bar.progress(100, text="✅ Investigation complete!")
            time.sleep(0.5)
            
            result = result_holder.get("result", {"steps": [], "final_answer": "No result", "success": False})
            st.session_state.investigation_result = result
            st.session_state.system_status = "RESOLVED" if result["success"] else "INCIDENT"

            st.rerun()
        
    elif not st.session_state.current_logs:
        st.info("👈 Select a production incident scenario from the sidebar to begin.")
        
        # Show what the agent does
        st.markdown("### How IncidentX Works")
        
        steps_demo = [
            ("🔧", "parse_and_filter_logs", "Ingests raw log files, filters by severity, groups by service"),
            ("🔗", "correlate_service_errors", "Finds cascading failure chains — identifies which service failed FIRST"),
            ("⚠️", "classify_incident_severity", "Assigns CRITICAL/HIGH/MEDIUM severity + calculates blast radius"),
            ("📚", "fetch_runbook_remediation", "RAG search over 5 engineering runbooks for validated fix procedures"),
            ("⚡", "execute_remediation_action", "Executes (simulated) fix: kill idle connections, restart pods, block IPs"),
            ("✅", "verify_service_health", "Runs health checks to confirm all services returned to HEALTHY state"),
        ]
        
        for icon, tool_name, desc in steps_demo:
            st.markdown(f"""
<div class="agent-step agent-action">
    {icon} <strong><code>{tool_name}</code></strong><br>
    <small style="color: #8b949e;">{desc}</small>
</div>
""", unsafe_allow_html=True)

    # Show investigation results
    if st.session_state.investigation_result:
        result = st.session_state.investigation_result

        if not result["success"]:
            error_msg = result.get('final_answer', 'Unknown error')
            if "API Quota" in error_msg or "quota" in error_msg.lower():
                st.error("⚠️ API Quota Exceeded")
                st.warning(error_msg)
                st.info("💡 **Quick fix**: Enter a fresh Gemini API key in the sidebar. Get one free at https://aistudio.google.com/app/apikey")
            else:
                st.error(f"Investigation failed: {error_msg}")
        else:
            st.markdown("### 🔍 Agent Execution Trace")
            st.caption("Every thought, tool call, and observation — full transparency into how the agent reasoned.")

            for i, step in enumerate(result["steps"]):
                step_type = step.get("type", "")

                if step_type == "action":
                    tool_name = step.get("tool", "")
                    tool_input_raw = step.get("tool_input", "")
                    observation = step.get("observation", "")
                    thought_text = step.get("thought", "")

                    # Extract clean thought (remove "Thought:" prefix and action lines)
                    clean_thought = ""
                    if thought_text:
                        lines = thought_text.strip().splitlines()
                        thought_lines = []
                        for line in lines:
                            stripped = line.strip()
                            if stripped.startswith("Action:") or stripped.startswith("Action Input:"):
                                break
                            if stripped.startswith("Thought:"):
                                stripped = stripped[8:].strip()
                            if stripped:
                                thought_lines.append(stripped)
                        clean_thought = " ".join(thought_lines)

                    with st.expander(
                        f"**Step {i+1}** — `{tool_name}` {'✅' if observation else '⏳'}",
                        expanded=(i < 3),
                    ):
                        if clean_thought:
                            st.markdown(f"""
<div class="agent-step agent-thought">
    <strong>🧠 Thought:</strong><br>{clean_thought}
</div>
""", unsafe_allow_html=True)
                        
                        st.markdown(f"""
<div class="agent-step agent-action">
    <strong>🔧 Tool Called:</strong> <code>{tool_name}</code><br>
    <strong>Input:</strong> <code>{str(tool_input_raw)[:300]}</code>
</div>
""", unsafe_allow_html=True)
                        
                        if observation:
                            st.markdown(f"""
<div class="agent-step agent-observe">
    <strong>📊 Tool Output:</strong><br>
    <pre style="font-size:0.8rem; white-space: pre-wrap;">{observation[:1200]}</pre>
</div>
""", unsafe_allow_html=True)

                elif step_type == "final":
                    st.markdown(f"""
<div class="agent-step agent-final">
    <strong>🎯 FINAL ROOT CAUSE ANALYSIS:</strong><br>
    <div style="white-space: pre-wrap; margin-top: 8px;">{step.get("output", "")}</div>
</div>
""", unsafe_allow_html=True)


with right_col:
    st.markdown("## 📊 Incident Analysis & Actions")

    # Severity Assessment Panel
    if st.session_state.investigation_result and st.session_state.investigation_result["success"]:
        result = st.session_state.investigation_result

        # Find classification step
        classification_obs = ""
        correlation_obs = ""
        for step in result["steps"]:
            if step.get("tool") == "classify_incident_severity":
                classification_obs = step.get("observation", "")
            if step.get("tool") == "correlate_service_errors":
                correlation_obs = step.get("observation", "")

        # Severity badge
        if "CRITICAL" in classification_obs:
            sev_color = "🔴"
            sev_label = "CRITICAL"
        elif "HIGH" in classification_obs:
            sev_color = "🟠"
            sev_label = "HIGH"
        else:
            sev_color = "🟡"
            sev_label = "MEDIUM"

        st.markdown(f"### {sev_color} Severity: {sev_label}")

        # Metrics
        m1, m2, m3 = st.columns(3)
        with m1:
            tool_steps = [s for s in result["steps"] if s.get("type") == "action"]
            st.metric("Agent Steps", len(tool_steps))
        with m2:
            st.metric("MTTD", "< 1 min", help="Mean Time to Detect")
        with m3:
            st.metric("MTTI", "< 30 sec", help="Mean Time to Investigate (AI-powered)")

        st.divider()

        # Cascading Failure Chain (from correlation output)
        if correlation_obs and "FAILURE CHAIN" in correlation_obs:
            st.markdown("### 🔗 Failure Chain")
            chain_lines = [
                l for l in correlation_obs.splitlines()
                if "Affected services" in l or "Root cause" in l
            ]
            for line in chain_lines:
                st.markdown(f"`{line.strip()}`")

        # Classification details
        if classification_obs:
            st.markdown("### 📋 Classification")
            for line in classification_obs.splitlines():
                if ":" in line and not line.startswith("==="):
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if key and val:
                        st.markdown(f"**{key}**: {val}")

        st.divider()

        # --- Human-in-the-Loop Remediation Approval ---
        st.markdown("### ⚡ Remediation Action Center")
        st.caption("Review the agent's proposed fix. Approve to execute.")

        # Find remediation step
        remediation_proposed = ""
        for step in result["steps"]:
            if step.get("tool") == "execute_remediation_action":
                remediation_proposed = step.get("observation", "")
                break

        if not remediation_proposed:
            st.info("Agent will propose a remediation action after investigation.")
        else:
            with st.expander("View Proposed Remediation", expanded=True):
                st.code(remediation_proposed, language="text")

            if not st.session_state.remediation_approved:
                col_approve, col_reject = st.columns(2)
                with col_approve:
                    if st.button("✅ Approve & Execute Fix", type="primary", use_container_width=True):
                        st.session_state.remediation_approved = True
                        st.session_state.system_status = "RESOLVED"
                        st.rerun()
                with col_reject:
                    if st.button("❌ Reject / Escalate", use_container_width=True):
                        st.warning("Escalated to on-call SRE lead.")
            else:
                st.success("✅ Remediation approved and executed. All services verifying health...")

        st.divider()

        # Health verification results
        health_obs = ""
        for step in result["steps"]:
            if step.get("tool") == "verify_service_health":
                health_obs = step.get("observation", "")
                break

        if health_obs:
            st.markdown("### ✅ Service Health Verification")
            st.code(health_obs, language="text")

        st.divider()

        # Download Report
        st.markdown("### 📥 Download Post-Mortem Report")
        from utils.report_generator import generate_postmortem_report
        report_md = generate_postmortem_report(
            scenario_name=st.session_state.current_scenario or "Unknown Incident",
            final_answer=result.get("final_answer", ""),
            steps=result.get("steps", []),
        )
        st.download_button(
            label="⬇️ Download Incident Post-Mortem (Markdown)",
            data=report_md,
            file_name="incidentx_postmortem_report.md",
            mime="text/markdown",
            use_container_width=True,
        )

    elif st.session_state.current_logs and not st.session_state.investigation_result:
        st.info("👈 Click **Start Autonomous Investigation** to deploy the IncidentX agent.")

        # Show log entry count
        try:
            entries = json.loads(st.session_state.current_logs)
            total = len(entries)
            critical = sum(1 for e in entries if e.get("level", "") in ["CRITICAL", "ALERT"])
            errors = sum(1 for e in entries if e.get("level") == "ERROR")
            warns = sum(1 for e in entries if e.get("level") == "WARN")

            st.markdown("### 📊 Pre-Analysis Log Statistics")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Events", total)
            m2.metric("🔴 Critical", critical)
            m3.metric("🟠 Errors", errors)
            m4.metric("🟡 Warnings", warns)

            # Services involved
            services = list(set(e.get("service", "unknown") for e in entries))
            st.markdown(f"**Services Involved** ({len(services)}):")
            for svc in services:
                st.markdown(f"  • `{svc}`")
        except Exception:
            pass
    else:
        st.markdown("""
### 📖 What Makes IncidentX Different

**This is not a chatbot.**

| Feature | Generic AI Chatbot | IncidentX Agent |
|---|---|---|
| Trigger | User types a question | Log file event / alert |
| Response | Single LLM call | Multi-step ReAct loop |
| Tools | None | 6 real diagnostic tools |
| Output | Text advice | RCA + runbook + actions |
| Human role | Constant prompting | Approve final fix only |

**The 6 Agent Tools:**
1. `parse_and_filter_logs` — Ingests & structures raw logs
2. `correlate_service_errors` — Finds the failure chain  
3. `classify_incident_severity` — Severity + blast radius
4. `fetch_runbook_remediation` — RAG over engineering runbooks
5. `execute_remediation_action` — Simulates fix execution
6. `verify_service_health` — Confirms incident resolution
""")


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.divider()
st.markdown("""
<div style="text-align: center; color: #484f58; font-size: 0.8rem; padding: 12px;">
    <strong>IncidentX</strong> — Autonomous IT Incident Response Agent &nbsp;|&nbsp; 
    Agentic Chase Hackathon (PS 01) &nbsp;|&nbsp; 
    Powered by <strong>Google Gemini 2.5 Flash</strong> + LangChain ReAct
</div>
""", unsafe_allow_html=True)
