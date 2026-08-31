"""Pipeline orchestration.

Runs the whole analysis under the firewall, assembles the Article 30 draft, and
writes deterministic artifacts to ``artifacts/``. All JSON is written with sorted
keys and no wall-clock timestamps, so repeated runs are byte-identical. A
manifest records the SHA-256 of every artifact for a determinism check.
"""
from __future__ import annotations

import csv
import glob
import hashlib
import io
import json
from pathlib import Path

from . import article30, firewall
from .ai_draft import enhance_record
from .code_scanner import scan_code
from .config import ARTIFACTS_DIR, CATEGORIES, SAMPLE_APP_DIR, SCHEMA_FILE
from .flow_graph import build_graph
from .schema_scanner import scan_schema


def _summary(schema, code, graph):
    pii_cols = [c for c in schema if c["is_pii"]]
    by_category = {}
    for c in pii_cols:
        by_category[c["category"]] = by_category.get(c["category"], 0) + 1
    transfers = [d for d in graph["destinations"]
                 if d["kind"] == "external_service" and d["third_country"]]
    recipients = [d for d in graph["destinations"] if d["kind"] == "external_service"]
    dest_kinds = {}
    for d in graph["destinations"]:
        dest_kinds[d["kind"]] = dest_kinds.get(d["kind"], 0) + 1
    return {
        "total_columns": len(schema),
        "pii_columns": len(pii_cols),
        "special_columns": sum(1 for c in pii_cols if c["special"]),
        "tables_with_pii": len(sorted({c["table"] for c in pii_cols})),
        "pii_by_category": {k: by_category.get(k, 0) for k in sorted(by_category)},
        "category_labels": {k: v["label"] for k, v in CATEGORIES.items()},
        "collection_points": len(code["collection_points"]),
        "flows": len(code["flows"]),
        "processing_activities": len(graph["activities"]),
        "external_recipients": len(recipients),
        "cross_border_transfers": len(transfers),
        "destination_kinds": dest_kinds,
    }


def _pii_columns_csv(schema) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["table", "column", "sql_type", "category", "special",
                     "confidence", "rule"])
    for c in schema:
        if c["is_pii"]:
            writer.writerow([c["table"], c["column"], c["sql_type"], c["category"],
                             c["special"], c["confidence"], c["rule"]])
    return buf.getvalue()


def run_pipeline(use_ai: bool = True) -> dict:
    """Run the full pipeline and return the assembled result (no disk writes)."""
    firewall.assert_static_clean()

    with firewall.sealed():
        schema = scan_schema(SCHEMA_FILE)
        code = scan_code(sorted(glob.glob(str(SAMPLE_APP_DIR / "*.py"))))
        graph = build_graph(schema, code)
        record = article30.build_record(schema, code, graph)

    # AI refinement is optional and network-bound; it changes prose only.
    if use_ai:
        record = enhance_record(record)
    else:
        record.setdefault("ai_status", "skipped")

    summary = _summary(schema, code, graph)
    return {"schema": schema, "code": code, "graph": graph,
            "record": record, "summary": summary}


def _dump_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def write_artifacts(result: dict, out_dir: Path = ARTIFACTS_DIR) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "scan.json": _dump_json({"schema": result["schema"], "code": result["code"],
                                 "graph": result["graph"], "summary": result["summary"]}),
        "article30.json": _dump_json(result["record"]),
        "article30.md": article30.to_markdown(result["record"]),
        "pii_columns.csv": _pii_columns_csv(result["schema"]),
    }
    manifest = {}
    for name, content in files.items():
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        manifest[name] = hashlib.sha256(content.encode("utf-8")).hexdigest()
    (out_dir / "manifest.json").write_text(_dump_json(manifest), encoding="utf-8")
    return manifest


def main() -> None:
    result = run_pipeline(use_ai=True)
    manifest = write_artifacts(result)
    s = result["summary"]
    print("PIICompass pipeline complete.")
    print(f"  Columns scanned:        {s['total_columns']}")
    print(f"  PII columns flagged:    {s['pii_columns']} "
          f"({s['special_columns']} special-category)")
    print(f"  Processing activities:  {s['processing_activities']}")
    print(f"  Data flows:             {s['flows']}")
    print(f"  External recipients:    {s['external_recipients']}")
    print(f"  Cross-border transfers: {s['cross_border_transfers']}")
    print(f"  AI drafting:            {result['record'].get('ai_status')}")
    print("  Artifacts written to artifacts/:")
    for name, digest in sorted(manifest.items()):
        print(f"    {name:18} sha256={digest[:16]}...")


if __name__ == "__main__":
    main()
