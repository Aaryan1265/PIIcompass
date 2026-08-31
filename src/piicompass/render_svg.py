"""Server-side inline SVG rendering.

No charting library and no CDN. Colours are applied via CSS classes (defined in
static/styles.css) so every fill and stroke resolves to a design token rather
than a hardcoded hex. Two renderers:

  flow_map_svg  : the data-flow map (processing activities -> destinations),
                  with cross-border transfer edges highlighted in the accent and
                  special-category edges dashed and marked.
  category_bar_svg : PII fields by category, with the single most sensitive
                     category (health / special) drawn in the accent colour.
"""
from __future__ import annotations

from html import escape

_KIND_ORDER = {"datastore": 0, "external_service": 1, "export": 2, "log": 3}
_KIND_SUB = {"datastore": "data store", "external_service": "recipient",
             "export": "file export", "log": "logs"}


def _esc(text: str) -> str:
    return escape(str(text), quote=True)


def _bezier(x1, y1, x2, y2) -> str:
    dx = (x2 - x1) * 0.45
    return f"M{x1:.1f},{y1:.1f} C{x1 + dx:.1f},{y1:.1f} {x2 - dx:.1f},{y2:.1f} {x2:.1f},{y2:.1f}"


def flow_map_svg(graph: dict) -> str:
    activities = graph["activities"]
    destinations = sorted(
        graph["destinations"],
        key=lambda d: (_KIND_ORDER.get(d["kind"], 9), d["label"]),
    )

    node_h, vgap = 34, 12
    lw, rw = 158, 214
    width = 792
    lx, rx = 16, width - 16 - rw

    def block(nodes):
        return len(nodes) * node_h + max(0, len(nodes) - 1) * vgap

    height = max(block(activities), block(destinations)) + 56
    l_top = (height - block(activities)) / 2
    r_top = (height - block(destinations)) / 2

    a_pos = {a["id"]: l_top + i * (node_h + vgap) for i, a in enumerate(activities)}
    d_pos = {d["id"]: r_top + i * (node_h + vgap) for i, d in enumerate(destinations)}

    parts = [
        f'<svg viewBox="0 0 {width} {int(height)}" role="img" '
        f'aria-label="PII data-flow map" class="flowmap" '
        f'xmlns="http://www.w3.org/2000/svg">'
    ]

    # Column headers.
    parts.append(f'<text x="{lx}" y="20" class="flow-col">Processing activities</text>')
    parts.append(f'<text x="{rx}" y="20" class="flow-col">Destinations</text>')

    # Edges first so nodes sit on top.
    for e in graph["edges"]:
        if e["source"] not in a_pos or e["target"] not in d_pos:
            continue
        y1 = a_pos[e["source"]] + node_h / 2
        y2 = d_pos[e["target"]] + node_h / 2
        cls = ["edge"]
        if e["third_country"]:
            cls.append("transfer")
        if e["special"]:
            cls.append("special")
        cats = ", ".join(e["categories"])
        tip = f"{e['source']} to {e['target'].split(':', 1)[-1]}: {cats}"
        if e["third_country"]:
            tip += " (cross-border transfer)"
        parts.append(
            f'<path class="{" ".join(cls)}" d="{_bezier(lx + lw, y1, rx, y2)}" '
            f'data-src="{_esc(e["source"])}" data-dst="{_esc(e["target"])}">'
            f'<title>{_esc(tip)}</title></path>'
        )

    # Activity nodes.
    for a in activities:
        y = a_pos[a["id"]]
        mark = " *" if a["special"] else ""
        parts.append(
            f'<g class="node activity" data-node="{_esc(a["id"])}">'
            f'<rect x="{lx}" y="{y:.1f}" width="{lw}" height="{node_h}" rx="6"/>'
            f'<text x="{lx + 10}" y="{y + 14:.1f}" class="node-label">{_esc(a["function"])}{mark}</text>'
            f'<text x="{lx + 10}" y="{y + 27:.1f}" class="node-sub">{_esc(a["file"])}</text>'
            f'</g>'
        )

    # Destination nodes.
    for d in destinations:
        y = d_pos[d["id"]]
        sub = _KIND_SUB.get(d["kind"], d["kind"])
        if d["kind"] == "external_service" and d.get("country"):
            sub = f'{sub} - {d["country"]}'
            if d.get("third_country"):
                sub += " (transfer)"
        mark = " *" if d["special"] else ""
        cls = "node destination" + (" xborder" if d.get("third_country") else "")
        parts.append(
            f'<g class="{cls}" data-node="{_esc(d["id"])}">'
            f'<rect x="{rx}" y="{y:.1f}" width="{rw}" height="{node_h}" rx="6"/>'
            f'<text x="{rx + 10}" y="{y + 14:.1f}" class="node-label">{_esc(d["label"])}{mark}</text>'
            f'<text x="{rx + 10}" y="{y + 27:.1f}" class="node-sub">{_esc(sub)}</text>'
            f'</g>'
        )

    parts.append("</svg>")
    return "".join(parts)


def category_bar_svg(summary: dict) -> str:
    counts = summary["pii_by_category"]
    labels = summary["category_labels"]
    items = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    if not items:
        return '<svg viewBox="0 0 10 10"></svg>'

    row_h, gap, top, left = 30, 10, 12, 132
    width, bar_max = 520, 300
    height = top + len(items) * (row_h + gap)
    max_count = max(c for _k, c in items) or 1

    parts = [
        f'<svg viewBox="0 0 {width} {int(height)}" role="img" '
        f'aria-label="PII fields by category" class="barchart" '
        f'xmlns="http://www.w3.org/2000/svg">'
    ]
    for i, (key, count) in enumerate(items):
        y = top + i * (row_h + gap)
        bw = max(2, bar_max * count / max_count)
        focus = " focus" if key == "health" else ""
        label = labels.get(key, key)
        parts.append(
            f'<text x="{left - 10}" y="{y + row_h / 2 + 4:.1f}" class="chart-label" '
            f'text-anchor="end">{_esc(label)}</text>'
        )
        parts.append(
            f'<rect x="{left}" y="{y:.1f}" width="{bw:.1f}" height="{row_h}" rx="4" '
            f'class="bar{focus}"><title>{_esc(label)}: {count}</title></rect>'
        )
        parts.append(
            f'<text x="{left + bw + 8:.1f}" y="{y + row_h / 2 + 4:.1f}" '
            f'class="chart-value tabular">{count}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)
