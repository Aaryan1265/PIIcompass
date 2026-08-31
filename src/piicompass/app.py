"""FastAPI application: the PIICompass dashboard.

Runs the deterministic pipeline once at startup (and again on demand), evaluates
the result against the sealed ground truth, and renders everything with the
locked design system. Every panel maps to real computed output.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # noqa: BLE001 - dotenv is optional
    pass

from . import article30, render_svg
from .config import ARTIFACTS_DIR, PROJECT_ROOT
from .evaluate import evaluate
from .pipeline import run_pipeline, write_artifacts

TEMPLATES_DIR = PROJECT_ROOT / "templates"
STATIC_DIR = PROJECT_ROOT / "static"

_ALLOWED_ARTIFACTS = {
    "scan.json", "article30.json", "article30.md", "pii_columns.csv", "manifest.json",
}

app = FastAPI(title="PIICompass")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# In-memory cache of the latest run.
_state: dict = {}


def _refresh() -> None:
    """Run the pipeline, evaluate, write artifacts, and cache everything."""
    result = run_pipeline(use_ai=True)
    write_artifacts(result)
    result["evaluation"] = evaluate(result["schema"])
    _state["result"] = result


@app.on_event("startup")
def _startup() -> None:
    _refresh()


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    result = _state.get("result")
    if result is None:
        _refresh()
        result = _state["result"]

    record = result["record"]
    transfer_recipients = {t["recipient"] for t in record["third_country_transfers"]}
    pii_columns = [c for c in result["schema"] if c["is_pii"]]

    context = {
        "summary": result["summary"],
        "graph": result["graph"],
        "record": record,
        "evaluation": result["evaluation"],
        "pii_columns": pii_columns,
        "transfer_recipients": transfer_recipients,
        "placeholder": article30.PLACEHOLDER,
        "flow_map_svg": render_svg.flow_map_svg(result["graph"]),
        "category_bar_svg": render_svg.category_bar_svg(result["summary"]),
    }
    return templates.TemplateResponse(request, "dashboard.html", context)


@app.post("/rescan")
def rescan():
    _refresh()
    return RedirectResponse(url="/", status_code=303)


@app.get("/artifact/{name}")
def artifact(name: str):
    if name not in _ALLOWED_ARTIFACTS:
        raise HTTPException(status_code=404, detail="Unknown artifact")
    path = Path(ARTIFACTS_DIR) / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact not generated yet")
    return FileResponse(str(path), filename=name)


@app.get("/health")
def health():
    return {"status": "ok", "cached_run": "result" in _state}
