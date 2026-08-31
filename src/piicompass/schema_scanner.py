"""Schema scanner.

Parse CREATE TABLE statements from a SQL file and classify each column. The
parser is intentionally small and forgiving: it handles the common column-per-
line DDL that most schemas and ORMs emit. It never executes SQL.
"""
from __future__ import annotations

import re
from pathlib import Path

from .classifier import classify

_CREATE_RE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[\"`]?(\w+)[\"`]?\s*\((.*?)\)\s*;",
    re.IGNORECASE | re.DOTALL,
)

# Tokens that begin a table-level constraint line rather than a column.
_CONSTRAINT_STARTS = (
    "primary", "foreign", "unique", "constraint", "check", "key", "index",
)


def _strip_comments(sql: str) -> str:
    # Remove -- line comments while preserving structure.
    out_lines = []
    for line in sql.splitlines():
        idx = line.find("--")
        out_lines.append(line[:idx] if idx != -1 else line)
    return "\n".join(out_lines)


def _split_columns(body: str) -> list[str]:
    """Split a table body on top-level commas (ignoring commas inside parens)."""
    parts, depth, current = [], 0, []
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def scan_schema(schema_path: str | Path) -> list[dict]:
    """Return one record per column, sorted by (table, column) for determinism."""
    text = _strip_comments(Path(schema_path).read_text(encoding="utf-8"))
    records: list[dict] = []

    for match in _CREATE_RE.finditer(text):
        table = match.group(1)
        for raw_col in _split_columns(match.group(2)):
            first = raw_col.split()[0].strip('"`').lower() if raw_col.split() else ""
            if not first or first in _CONSTRAINT_STARTS:
                continue
            column = raw_col.split()[0].strip('"`')
            col_type = raw_col.split()[1] if len(raw_col.split()) > 1 else ""
            result = classify(column)
            records.append({
                "table": table,
                "column": column,
                "sql_type": col_type,
                "is_pii": result is not None,
                "category": result.category if result else None,
                "special": bool(result.special) if result else False,
                "confidence": round(result.confidence, 3) if result else None,
                "rule": result.rule if result else None,
                "rationale": result.rationale if result else None,
            })

    records.sort(key=lambda r: (r["table"], r["column"]))
    return records
