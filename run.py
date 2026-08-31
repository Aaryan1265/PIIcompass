"""Single-command entry point.

    python run.py

Adds src/ to the import path, loads .env if present, prints a scan summary, and
starts the dashboard at http://127.0.0.1:8000. Set HOST or PORT env vars to
override the bind address.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # noqa: BLE001 - optional
    pass


def main() -> None:
    import uvicorn

    from piicompass.app import app
    from piicompass.pipeline import main as pipeline_main

    # Generate artifacts and print a summary up front so CLI users see results
    # even before opening the browser.
    pipeline_main()

    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"\nDashboard: http://{host}:{port}\n")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
