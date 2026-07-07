from google.adk.agents import Agent
from sql_agent.agent import get_context_tool, run_sql_tool

root_agent = Agent(
    model="gemini-2.0-flash",
    name="report_agent",
    description=(
        "Specializes in generating formatted executive summaries and comprehensive multi-metric briefings."
    ),
    instruction=(
        "You are the Report Agent. Your job is to compile comprehensive executive reports.\n"
        "1. Use get_context_tool to review available KPIs.\n"
        "2. Use run_sql_tool to fetch data across multiple business areas (e.g., revenue, usage, support) depending on the request.\n"
        "3. Format the response as a highly structured executive briefing with headers, bullet points, and clean tables.\n"
        "Ensure the final output is polished and ready for a CEO to read."
    ),
    tools=[get_context_tool, run_sql_tool]
)
