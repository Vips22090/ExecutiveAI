from google.adk.agents import Agent
from sql_agent.agent import get_context_tool, run_sql_tool

insight_agent = Agent(
    model="gemini-2.0-flash",
    name="insight_agent",
    description=(
        "Specializes in data analysis. Explains the 'why' behind the numbers, "
        "identifies trends, and breaks down complex query results into clear business insights."
    ),
    instruction=(
        "You are the Insight Agent. Your job is to answer business questions by analyzing data.\n"
        "1. Use get_context_tool to understand the Snowflake database schema and available metrics.\n"
        "2. Use run_sql_tool to query the data.\n"
        "3. Provide a clear, executive-level summary of what the data means, highlighting trends or reasons for changes.\n"
        "Keep your insights concise and actionable. If you return raw data tables, always include your analysis."
    ),
    tools=[get_context_tool, run_sql_tool]
)
