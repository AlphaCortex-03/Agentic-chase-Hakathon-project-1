# IncidentX — Autonomous IT Incident Response Agent

![CI](https://github.com/AlphaCortex-03/Agentic-chase-Hakathon-project-1/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.12-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## Agentic Chase Hackathon | PS 01

## What is IncidentX?

**IncidentX** is a production-grade autonomous IT incident response agent. It is **not a chatbot**. It is an **event-driven, tool-using AI agent** that:

1. **Ingests** raw system log files (TXT, JSON, CSV) or simulated telemetry events
2. **Autonomously** runs a multi-step investigation using real diagnostic tools
3. **Correlates** cascading failure chains across microservices
4. **Retrieves** validated engineering runbooks using RAG (Retrieval-Augmented Generation)
5. **Generates** an executive-level Root Cause Analysis (RCA) report
6. **Proposes and executes** (simulated) remediation actions with human-in-the-loop approval
7. **Verifies** that the incident is resolved post-action

---

## Project Structure

```
├── app.py                      ← Main Streamlit dashboard (UI entry point)
├── agent/
│   ├── __init__.py
│   ├── incidentx_agent.py      ← Core ReAct agent loop (Gemini + Tool Calling)
│   ├── tools.py                ← All 6 diagnostic tools the agent can call
│   └── runbook_rag.py          ← Runbook knowledge base + vector search
├── data/
│   ├── scenarios/
│   │   ├── outage_a_db_pool.json       ← Sample: DB Connection Pool Exhaustion
│   │   ├── outage_b_memory_leak.json   ← Sample: Memory Leak + OOM Kill
│   │   └── outage_c_rate_limit.json    ← Sample: DDoS / API Rate Limit Spike
│   └── runbooks/
│       ├── db_connection_exhaustion.md
│       ├── memory_leak_oom.md
│       ├── api_rate_limit.md
│       ├── service_restart.md
│       └── network_timeout.md
├── utils/
│   ├── __init__.py
│   ├── log_parser.py           ← Parses TXT / JSON / CSV log files
│   └── report_generator.py     ← Generates downloadable incident post-mortem
├── tests/
│   └── test_incidentx.py       ← 17 offline unit tests (no API key needed)
├── .github/workflows/ci.yml    ← CI: installs deps, runs tests on every push
├── install.bat                 ← Windows: creates venv + installs dependencies
├── start.bat                   ← Windows: starts the Streamlit dashboard
├── .env.example                ← Environment variable template
├── requirements.txt
├── LICENSE
└── README.md
```

---

## Setup Instructions

### Step 1 — Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2 — Set Your Gemini API Key

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

Get your free API key from: https://aistudio.google.com/app/apikey

### Step 3 — Run the Application

```bash
streamlit run app.py
```

The dashboard will open in your browser at `http://localhost:8501`

> **Windows one-click**: run `install.bat` once to set everything up, then `start.bat` to launch.

---

## Testing & CI

The repo ships with **17 offline unit tests** covering the agent tools, log parser, scenario data, and post-mortem generator — no API key required:

```bash
pip install pytest
pytest -v
```

CI runs these tests automatically on every push and pull request via GitHub Actions.

---

## Security Notes

- Add your `GEMINI_API_KEY` to a local `.env` file (never commit it — `.env` is gitignored)
- All remediation actions are **simulated**; no destructive operations are performed
- See `.env.example` for the required variables

---

## Demo Flow (For Judges)

### Option 1: Pre-Loaded Production Incident Scenarios (Recommended for Demos)

Click any of the 3 quick-load buttons on the dashboard:

| Scenario | Type | Root Cause |
|---|---|---|
| 🔴 Outage A | DB Connection Pool Exhaustion | Cascading failure: Idle connection leak → API 504s → Frontend down |
| 🟠 Outage B | Memory Leak + OOM Kill | JVM heap overflow → Pod killed by kernel → Service unavailable |
| 🟡 Outage C | DDoS Rate Limit Spike | Single subnet hammering API → Rate limiter triggered → Legitimate users blocked |

### Option 2: Upload Your Own Log File

Upload any `.txt`, `.json`, or `.csv` log file from the sidebar.

---

## How the Agent Works (ReAct Loop)

The agent follows the **Reason → Act → Observe → Repeat** pattern:

```
Incoming Alert / Log File
        │
        ▼
[ Agent Thought: What type of incident is this? ]
        │
        ▼
[ Tool Call: parse_and_filter_logs() ]
        │
        ▼
[ Agent Thought: I see DB errors + API timeouts. Are they correlated? ]
        │
        ▼
[ Tool Call: correlate_service_errors() ]
        │
        ▼
[ Agent Thought: Root cause identified — DB pool at 100% capacity. Find the fix. ]
        │
        ▼
[ Tool Call: fetch_runbook_remediation() ]
        │
        ▼
[ Tool Call: classify_incident_severity() ]
        │
        ▼
[ Agent Thought: Compose RCA report and propose action. ]
        │
        ▼
[ Tool Call: fetch_runbook_remediation() ]
        │
        ▼
[ Human-in-the-Loop: Approve Remediation? ]
        │
        ▼
[ Tool Call: execute_remediation_action() ]
        │
        ▼
[ Tool Call: verify_service_health() ]
        │
        ▼
[ Incident Resolved ✅ ]
```

---

## Tech Stack

| Component | Technology |
|---|---|
| AI Model | Google Gemini 2.5 Flash (Function Calling) |
| Agent Framework | LangChain ReAct Agent |
| RAG (Runbook Search) | FAISS + LangChain Document Retriever |
| Dashboard | Streamlit |
| Data Visualization | Plotly Express |
| Log Parsing | Pandas |
| Environment | Python 3.10+ |

---

## Why IncidentX is NOT a Chatbot

| Feature | Generic Chatbot | IncidentX Agent |
|---|---|---|
| Trigger | User types a question | Log file event / simulated alert |
| Response mechanism | Single LLM prompt | Multi-step ReAct loop with real tool calls |
| Tools used | None | parse_logs, correlate_errors, search_runbooks, execute_remediation, verify_health |
| Output | "Try restarting your server" | Exact RCA, Severity Rating, Blast Radius, Downloadable Post-Mortem PDF |
| Human interaction | Constant prompting required | Autonomous investigation, human approves only the final fix |
| Value to enterprise | None | Reduces Mean Time to Resolution (MTTR) from hours to seconds |

---

## Team DOREMAN,

**Hackathon**: Agentic Chase — SCCSBS AOT  
**Problem Statement**: PS 01 — IncidentX: Autonomous IT Incident Response Agent  
**Event Date**: 7th November

## License

MIT — see [LICENSE](LICENSE).
