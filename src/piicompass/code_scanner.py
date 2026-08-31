"""Code scanner.

Static, AST-based analysis of Python source. For each function it finds:

  1. Collection points: fields read from a request-like object (payload, request,
     body, ...) whose name classifies as PII. This is where personal data enters.

  2. Flows: PII moving into a sink. Four sink kinds are recognised:
       - datastore        (ORM model construction, or db/session .add/.save)
       - external_service (a call whose name matches the vendor lexicon)
       - log              (logger.*, logging.*, print)
       - export           (csv writer .writerow/.writerows)

The analysis is a lightweight intra-procedural forward taint pass. It is a
heuristic, not a proof: it over-approximates by treating any attribute or string
literal whose name classifies as PII as carrying that category. That is the
appropriate posture for a discovery tool (favour recall, let a human confirm),
and the limitation is reported in the output. Nothing here is executed; only
parsed. The scanner never opens the sealed ground-truth directory.
"""
from __future__ import annotations

import ast
from pathlib import Path

from .classifier import classify
from .vendors import match_vendor

REQUEST_ROOTS = {"payload", "request", "req", "body", "form", "data", "params", "query"}
DATASTORE_OBJS = {"db", "session", "dbsession", "db_session"}
DATASTORE_METHODS = {"add", "save", "insert", "add_all", "bulk_save_objects"}
LOG_OBJS = {"logger", "logging", "log"}
LOG_FUNCS = {"print"}
EXPORT_ATTRS = {"writerow", "writerows"}

# Known ORM model class -> physical table. Editable for your own models.
MODEL_TABLE_MAP = {
    "Patient": "patients",
    "EmergencyContact": "contacts",
    "Payment": "payments",
    "HealthRecord": "health_records",
    "Appointment": "appointments",
}


def _root_name(node: ast.AST) -> str | None:
    """Return the base Name id of an attribute/subscript chain, else None."""
    while isinstance(node, (ast.Attribute, ast.Subscript)):
        node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _const_str(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _collect_pii(node: ast.AST, taint: dict[str, set]) -> set[tuple[str, bool, str]]:
    """Union of (category, special, field) referenced anywhere in an expression."""
    found: set[tuple[str, bool, str]] = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Attribute):
            c = classify(sub.attr)
            if c:
                found.add((c.category, c.special, sub.attr))
        elif isinstance(sub, ast.Subscript):
            key = _const_str(sub.slice)
            if key:
                c = classify(key)
                if c:
                    found.add((c.category, c.special, key))
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            c = classify(sub.value)
            if c:
                found.add((c.category, c.special, sub.value))
        elif isinstance(sub, ast.Name) and sub.id in taint:
            found |= taint[sub.id]
    return found


def _classify_sink(call: ast.Call) -> tuple[str, dict] | None:
    """Return (sink_kind, meta) for a Call node, or None if it is not a sink."""
    func = call.func

    # Datastore: ORM model constructor.
    if isinstance(func, ast.Name) and func.id in MODEL_TABLE_MAP:
        return "datastore", {"table": MODEL_TABLE_MAP[func.id], "label": MODEL_TABLE_MAP[func.id]}

    if isinstance(func, ast.Attribute):
        root = _root_name(func)
        attr = func.attr.lower()
        # Datastore: db/session .add/.save/...
        if root in DATASTORE_OBJS and attr in DATASTORE_METHODS:
            return "datastore", {"table": None, "label": "database"}
        # Export: csv writer .writerow/.writerows
        if attr in EXPORT_ATTRS:
            return "export", {"label": "CSV export file"}
        # Log: logger.* / logging.* / log.*
        if root in LOG_OBJS:
            return "log", {"label": "Application logs"}
        # External service via vendor token in the client name or method name.
        vendor = match_vendor(root or "", func.attr)
        if vendor:
            return "external_service", {
                "label": vendor["recipient"], "vendor": vendor,
            }

    if isinstance(func, ast.Name):
        if func.id in LOG_FUNCS:
            return "log", {"label": "Application logs"}
        vendor = match_vendor(func.id)
        if vendor:
            return "external_service", {"label": vendor["recipient"], "vendor": vendor}

    return None


def _model_table_from_var(var_taint_tables: dict[str, str], call: ast.Call) -> str | None:
    """For db.add(x), resolve x back to the table of the model it was built from."""
    if not call.args:
        return None
    arg = call.args[0]
    if isinstance(arg, ast.Name):
        return var_taint_tables.get(arg.id)
    return None


def _scan_function(func: ast.FunctionDef, file_label: str) -> tuple[list[dict], dict]:
    """Scan one function. Returns (collection_points, flows_by_key)."""
    collection: list[dict] = []
    seen_collection: set[tuple[str, str]] = set()
    taint: dict[str, set] = {}
    var_tables: dict[str, str] = {}  # local var -> table (for db.add resolution)
    flows: dict[tuple, dict] = {}

    # Pass 1: collection points (request-root PII reads anywhere in the body).
    for sub in ast.walk(func):
        field = None
        if isinstance(sub, ast.Attribute) and _root_name(sub) in REQUEST_ROOTS:
            field = sub.attr
        elif isinstance(sub, ast.Subscript) and _root_name(sub) in REQUEST_ROOTS:
            field = _const_str(sub.slice)
        if field:
            c = classify(field)
            if c and (func.name, field) not in seen_collection:
                seen_collection.add((func.name, field))
                collection.append({
                    "file": file_label, "function": func.name, "field": field,
                    "category": c.category, "special": c.special,
                    "confidence": round(c.confidence, 3),
                })

    # Pass 2: ordered walk of statements to build taint and emit sink flows.
    def record_flow(kind: str, meta: dict, cats: set[tuple[str, bool, str]]):
        categories = sorted({c for c, _s, _f in cats})
        if not categories:
            return
        special = any(s for _c, s, _f in cats)
        if kind == "datastore":
            key = (func.name, "datastore", meta.get("table") or "database")
        else:
            key = (func.name, kind, meta["label"])
        rec = flows.get(key)
        if rec is None:
            rec = {
                "file": file_label, "function": func.name, "sink_kind": kind,
                "target": meta.get("table") or meta["label"],
                "categories": set(categories), "special": special,
            }
            if kind == "external_service":
                v = meta["vendor"]
                rec.update({
                    "recipient": v["recipient"], "country": v["country"],
                    "iso": v["iso"], "role": v["role"],
                    "third_country": v["third_country"], "safeguard": v["safeguard"],
                })
            flows[key] = rec
        else:
            rec["categories"] |= set(categories)
            rec["special"] = rec["special"] or special

    def visit_stmt(stmt: ast.stmt):
        # Emit sinks found in this statement using current taint.
        for node in ast.walk(stmt):
            if isinstance(node, ast.Call):
                sink = _classify_sink(node)
                if sink:
                    kind, meta = sink
                    cats = _collect_pii(node, taint)
                    # For a bare db.add(model_var), resolve the table and columns.
                    if kind == "datastore" and meta.get("table") is None:
                        table = _model_table_from_var(var_tables, node)
                        if table:
                            meta = dict(meta); meta["table"] = table
                        if node.args and isinstance(node.args[0], ast.Name):
                            cats |= taint.get(node.args[0].id, set())
                    # For a model constructor, add keyword-name classification.
                    if kind == "datastore" and isinstance(node.func, ast.Name):
                        for kw in node.keywords:
                            if kw.arg:
                                kc = classify(kw.arg)
                                if kc:
                                    cats.add((kc.category, kc.special, kw.arg))
                    record_flow(kind, meta, cats)

        # Update taint for assignments (after sink emission for this statement).
        if isinstance(stmt, ast.Assign):
            contrib = _collect_pii(stmt.value, taint)
            table = None
            if isinstance(stmt.value, ast.Call) and isinstance(stmt.value.func, ast.Name):
                table = MODEL_TABLE_MAP.get(stmt.value.func.id)
                if table:
                    for kw in stmt.value.keywords:
                        if kw.arg:
                            kc = classify(kw.arg)
                            if kc:
                                contrib.add((kc.category, kc.special, kw.arg))
            for target in stmt.targets:
                if isinstance(target, ast.Name):
                    taint[target.id] = set(contrib)
                    if table:
                        var_tables[target.id] = table

        # Recurse into nested blocks in order.
        for child in getattr(stmt, "body", []) or []:
            visit_stmt(child)
        for child in getattr(stmt, "orelse", []) or []:
            visit_stmt(child)
        for handler in getattr(stmt, "handlers", []) or []:
            for child in handler.body:
                visit_stmt(child)

    for stmt in func.body:
        visit_stmt(stmt)

    return collection, flows


def scan_code(paths: list[str | Path]) -> dict:
    """Scan a list of Python files. Returns collection points and flows."""
    all_collection: list[dict] = []
    all_flows: list[dict] = []

    for path in sorted(str(p) for p in paths):
        p = Path(path)
        if p.suffix != ".py":
            continue
        source = p.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(p))
        file_label = p.name
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                collection, flows = _scan_function(node, file_label)
                all_collection.extend(collection)
                for rec in flows.values():
                    rec = dict(rec)
                    rec["categories"] = sorted(rec["categories"])
                    all_flows.append(rec)

    all_collection.sort(key=lambda r: (r["file"], r["function"], r["field"]))
    all_flows.sort(key=lambda r: (r["file"], r["function"], r["sink_kind"], r["target"]))
    return {"collection_points": all_collection, "flows": all_flows}
