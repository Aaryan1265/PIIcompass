"""Build the data-flow graph from scan results.

Produces three deterministic, sorted collections:

  activities   : processing functions, with the PII categories each collects.
  destinations : where data comes to rest or exits (tables, third-party
                 recipients, logs, file exports), with transfer metadata.
  edges        : function -> destination flows, tagged special / cross-border.
"""
from __future__ import annotations

from .config import CATEGORIES


def _dest_id(flow: dict) -> str:
    kind = flow["sink_kind"]
    if kind == "datastore":
        return f"table:{flow['target']}"
    if kind == "external_service":
        return f"recipient:{flow['recipient']}"
    if kind == "log":
        return "sink:logs"
    if kind == "export":
        return "sink:export"
    return f"sink:{flow['target']}"


def build_graph(schema: list[dict], code: dict) -> dict:
    collection = code["collection_points"]
    flows = code["flows"]

    # Activities: any function that collects PII or emits a flow.
    activity_cats: dict[str, set] = {}
    activity_file: dict[str, str] = {}
    activity_special: dict[str, bool] = {}
    for cp in collection:
        activity_cats.setdefault(cp["function"], set()).add(cp["category"])
        activity_file[cp["function"]] = cp["file"]
        activity_special[cp["function"]] = activity_special.get(cp["function"], False) or cp["special"]
    for fl in flows:
        activity_cats.setdefault(fl["function"], set()).update(fl["categories"])
        activity_file.setdefault(fl["function"], fl["file"])
        activity_special[fl["function"]] = activity_special.get(fl["function"], False) or fl["special"]

    activities = []
    for fn in sorted(activity_cats):
        cats = sorted(activity_cats[fn])
        activities.append({
            "id": fn,
            "function": fn,
            "file": activity_file.get(fn, ""),
            "categories": cats,
            "special": activity_special.get(fn, False),
        })

    # Table -> schema PII categories (what a table holds, independent of code).
    table_cats: dict[str, set] = {}
    table_special: dict[str, bool] = {}
    for col in schema:
        if col["is_pii"]:
            table_cats.setdefault(col["table"], set()).add(col["category"])
            table_special[col["table"]] = table_special.get(col["table"], False) or col["special"]

    # Destinations, merged across flows.
    destinations: dict[str, dict] = {}
    for fl in flows:
        did = _dest_id(fl)
        dest = destinations.get(did)
        if dest is None:
            dest = {
                "id": did, "kind": fl["sink_kind"], "categories": set(),
                "special": False, "country": None, "third_country": False,
                "safeguard": None, "role": None,
            }
            if fl["sink_kind"] == "datastore":
                dest["label"] = fl["target"]
                dest["categories"] |= table_cats.get(fl["target"], set())
                dest["special"] = table_special.get(fl["target"], False)
            elif fl["sink_kind"] == "external_service":
                dest["label"] = fl["recipient"]
                dest["country"] = fl["country"]
                dest["third_country"] = fl["third_country"]
                dest["safeguard"] = fl["safeguard"]
                dest["role"] = fl["role"]
            elif fl["sink_kind"] == "log":
                dest["label"] = "Application logs"
            elif fl["sink_kind"] == "export":
                dest["label"] = "CSV export file"
            destinations[did] = dest
        dest["categories"] |= set(fl["categories"])
        dest["special"] = dest["special"] or fl["special"]

    dest_list = []
    for did in sorted(destinations):
        d = destinations[did]
        d = dict(d)
        d["categories"] = sorted(d["categories"])
        dest_list.append(d)

    # Edges.
    edges = []
    for fl in flows:
        edges.append({
            "source": fl["function"],
            "target": _dest_id(fl),
            "categories": sorted(fl["categories"]),
            "special": fl["special"],
            "third_country": bool(fl.get("third_country")),
        })
    edges.sort(key=lambda e: (e["source"], e["target"]))

    return {
        "activities": activities,
        "destinations": dest_list,
        "edges": edges,
        "category_labels": {k: v["label"] for k, v in CATEGORIES.items()},
    }
