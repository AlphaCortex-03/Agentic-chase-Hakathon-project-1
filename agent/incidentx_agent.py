"""
incidentx_agent.py — Core IncidentX ReAct Agent using LangChain + Gemini.

This is NOT a chatbot. It is an event-driven autonomous incident response agent
that uses tool-calling in a multi-step Reason -> Act -> Observe loop.
"""

import os
import json
from typing import Generator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.callbacks.base import BaseCallbackHandler
from dotenv import load_dotenv

from agent.tools import ALL_TOOLS

load_dotenv()

# ---------------------------------------------------------------------------
# SYSTEM PROMPT — Defines the agent's persona, goals, and constraints
# ---------------------------------------------------------------------------
INCIDENTX_SYSTEM_PROMPT = """You are IncidentX, an elite autonomous IT incident response agent.
You are deployed in a production operations center. You are NOT a general-purpose chatbot.
Your ONLY job is to investigate IT incidents from system logs and autonomously resolve them.

## YOUR MISSION
Given a set of system logs or an incident alert, you MUST:
1. Use parse_and_filter_logs to understand the raw log data first
2. Use correlate_service_errors to find which service failed first (the root cause)
3. Use classify_incident_severity to assign severity and assess business impact
4. Use fetch_runbook_remediation to retrieve validated engineering remediation steps
5. Propose execute_remediation_action to simulate executing the fix
6. Use verify_service_health to confirm the incident is resolved

## STRICT RULES
- You MUST use tools in logical sequence. Never skip correlation and classification steps.
- You MUST call correlate_service_errors before assigning a root cause.
- You MUST fetch the runbook BEFORE proposing any remediation.
- You NEVER say "I cannot help". You investigate until you find the answer.
- You speak like a Senior Site Reliability Engineer (SRE), not like a chatbot.
- Always end your investigation with a verification step using verify_service_health.
- Your analysis must be specific, citing exact timestamps, service names, and error messages.

## TOOLS AVAILABLE
{tools}

Tool names: {tool_names}

## HOW TO USE TOOLS
Use this EXACT format for every step:
Thought: [Your engineering reasoning about what to do next]
Action: [exact tool name from the list above]
Action Input: [the tool argument as a string]
Observation: [the tool will provide this output]

After all steps, write:
Thought: I now have enough information to provide the complete Root Cause Analysis.
Final Answer: [Your complete RCA report]

{agent_scratchpad}

Input: {input}"""


# ---------------------------------------------------------------------------
# Step Callback — Streams each agent step back to the UI in real-time
# ---------------------------------------------------------------------------
class StepStreamCallback(BaseCallbackHandler):
    """Captures agent steps and streams them to a list for UI display."""

    def __init__(self):
        self.steps = []

    def on_agent_action(self, action, **kwargs):
        self.steps.append({
            "type": "action",
            "thought": getattr(action, "log", ""),
            "tool": action.tool,
            "tool_input": action.tool_input,
        })

    def on_tool_end(self, output, **kwargs):
        if self.steps and self.steps[-1]["type"] == "action":
            self.steps[-1]["observation"] = str(output)[:1500]

    def on_agent_finish(self, finish, **kwargs):
        self.steps.append({
            "type": "final",
            "output": finish.return_values.get("output", "")
        })


# ---------------------------------------------------------------------------
# Build Agent
# ---------------------------------------------------------------------------
def build_agent(streaming: bool = False) -> AgentExecutor:
    """
    Builds and returns the IncidentX LangChain ReAct AgentExecutor.
    Uses Google Gemini 2.5 Flash with function-calling capability.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Create a .env file with:\n"
            "GEMINI_API_KEY=your_key_here\n\n"
            "Get your free key at: https://aistudio.google.com/app/apikey"
        )

    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.1,          # Low temperature for deterministic SRE-style reasoning
        max_output_tokens=4096,
    )

    prompt = PromptTemplate.from_template(INCIDENTX_SYSTEM_PROMPT)

    agent = create_react_agent(llm=llm, tools=ALL_TOOLS, prompt=prompt)

    executor = AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,
        max_iterations=12,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
    )
    return executor


# ---------------------------------------------------------------------------
# Main Investigation Function
# ---------------------------------------------------------------------------
def run_investigation(log_content: str) -> dict:
    """
    Runs the full autonomous incident investigation on the provided log content.

    Args:
        log_content: Raw log data as a string (JSON array or plain text).

    Returns:
        dict with keys:
          - 'steps': list of agent steps (thought/action/observation)
          - 'final_answer': the complete RCA report string
          - 'success': bool
    """
    callback = StepStreamCallback()

    try:
        executor = build_agent()

        input_prompt = f"""PRODUCTION INCIDENT ALERT — IMMEDIATE INVESTIGATION REQUIRED

The following system logs have been received. Begin autonomous investigation immediately.
Identify the root cause, classify severity, fetch the appropriate runbook, and propose remediation.

--- INCIDENT LOG DATA ---
{log_content}
--- END LOG DATA ---

Conduct a full investigation using all available tools. Do not ask for clarification. Act now."""

        result = executor.invoke(
            {"input": input_prompt},
            config={"callbacks": [callback]},
        )

        final_answer = result.get("output", "Investigation completed. See steps above for details.")

        # Parse intermediate steps from LangChain format
        steps = []
        for action, observation in result.get("intermediate_steps", []):
            steps.append({
                "type": "action",
                "thought": getattr(action, "log", ""),
                "tool": getattr(action, "tool", "unknown"),
                "tool_input": str(getattr(action, "tool_input", ""))[:300],
                "observation": str(observation)[:2000],
            })

        steps.append({"type": "final", "output": final_answer})

        return {
            "steps": steps,
            "final_answer": final_answer,
            "success": True,
        }

    except Exception as e:
        error_msg = str(e)
        # Provide a clearer error message for common issues
        friendly_msg = error_msg
        if "429" in error_msg or "quota" in error_msg.lower() or "ResourceExhausted" in error_msg:
            friendly_msg = (
                "⚠️ API Quota Exceeded — Your Gemini API key has hit its daily free-tier limit (20 req/day).\n\n"
                "Solutions:\n"
                "• Wait until tomorrow for the quota to reset\n"
                "• Use a different Gemini API key (get one free at https://aistudio.google.com/app/apikey)\n"
                "• Upgrade to a paid Gemini API tier for higher limits\n\n"
                f"Technical detail: {error_msg[:200]}"
            )
        elif "API key" in error_msg or "GEMINI_API_KEY" in error_msg:
            friendly_msg = (
                "⚠️ Invalid or Missing API Key — Please check your Gemini API key.\n\n"
                "Get a free key at: https://aistudio.google.com/app/apikey\n\n"
                f"Technical detail: {error_msg[:200]}"
            )
        return {
            "steps": [{"type": "error", "output": friendly_msg}],
            "final_answer": f"Investigation failed: {friendly_msg}",
            "success": False,
        }
