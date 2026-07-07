from google.adk.agents import Agent
from sql_agent.agent import get_context_tool, run_sql_tool

forecast_agent = Agent(
    model="gemini-2.0-flash",
    name="forecast_agent",
    description=(
        "Specializes in forecasting and projections. Uses historical data to predict future metrics."
    ),
    instruction=(
        "You are the Forecast Agent. Your job is to predict future business metrics based on historical data.\n"
        "1. Use get_context_tool to understand the schema.\n"
        "2. Use run_sql_tool to pull historical data needed for the forecast.\n"
        "3. Project future values (e.g., next month, next quarter) using reasonable trend estimation.\n"
        "Always state your assumptions (e.g., 'assuming current growth rate continues'). Present both the historical data and your projections clearly."
    ),
    tools=[get_context_tool, run_sql_tool]
)
