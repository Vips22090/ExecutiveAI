from google.adk.agents import Agent
from sql_agent import sql_agent
from insight_agent import insight_agent
from forecast_agent import forecast_agent
from alert_agent import alert_agent
from report_agent import report_agent

root_agent = Agent(
    model="gemini-2.0-flash",
    name="root_agent",
    description=(
        "Executive AI Coordinator. Understands business questions from the CEO "
        "and delegates all data retrieval to the sql_agent specialist."
    ),
    instruction=(
        "You are the Executive AI Coordinator. Your job is to route the user's question to the correct specialist agent.\n"
        "Look for a routing prefix in the user's prompt (e.g. [SQL_AGENT], [INSIGHT_AGENT]) and delegate the task to that specific agent.\n\n"
        "Routing Rules:\n"
        "- If prefix is [SQL_AGENT] -> delegate to sql_agent to fetch raw data.\n"
        "- If prefix is [INSIGHT_AGENT] -> delegate to insight_agent for analysis and trends.\n"
        "- If prefix is [FORECAST_AGENT] -> delegate to forecast_agent for future projections.\n"
        "- If prefix is [ALERT_AGENT] -> delegate to alert_agent for anomalies.\n"
        "- If prefix is [REPORT_AGENT] -> delegate to report_agent for comprehensive briefings.\n"
        "- If there is NO prefix -> default to sql_agent.\n\n"
        "Do not answer the question yourself. Just delegate."
    ),
    sub_agents=[sql_agent, insight_agent, forecast_agent, alert_agent, report_agent],
)
