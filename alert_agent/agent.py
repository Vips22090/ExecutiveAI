from google.adk.agents import Agent
from sql_agent.agent import get_context_tool, run_sql_tool

alert_agent = Agent(
    model="gemini-2.0-flash",
    name="alert_agent",
    description=(
        "Specializes in detecting anomalies, spikes, drops, or threshold breaches in recent data."
    ),
    instruction=(
        "You are the Alert Agent. Your job is to scan recent data for anomalies or issues.\n"
        "1. Use get_context_tool to check available metrics.\n"
        "2. Use run_sql_tool to pull recent data and compare it to historical baselines.\n"
        "3. Highlight significant deviations, sudden drops, or concerning spikes.\n"
        "Start your response with a clear alert (e.g., '⚠️ CRITICAL' or 'ℹ️ NOTICE') if an anomaly is found."
    ),
    tools=[get_context_tool, run_sql_tool]
)
