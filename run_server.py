"""
run_server.py
─────────────
Starts the ExecutiveAI ADK backend AND serves the dashboard
from the same port (8000) — same origin, zero CORS issues.

Usage:
    .venv\Scripts\python run_server.py

Then open the dashboard at http://127.0.0.1:8000/dashboard/
"""

import uvicorn
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from google.adk.cli.fast_api import get_fast_api_app

app = get_fast_api_app(
    agents_dir=".",
    web=True,
    host="127.0.0.1",
    port=8000,
)

# Serve the dashboard folder as static files at /dashboard
DASHBOARD_DIR = Path(__file__).parent / "dashboard"
app.mount("/dashboard", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")

# Redirect root / to the dashboard
@app.get("/")
def root_redirect():
    return RedirectResponse(url="/dashboard/")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("  ExecutiveAI — starting…")
    print("  Dashboard → http://127.0.0.1:8000/dashboard/")
    print("  ADK Dev UI → http://127.0.0.1:8000/dev-ui")
    print("="*60 + "\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
