"""Optional AI drafting layer.

If an Anthropic API key is configured, this refines the prose of the Article 30
record: it polishes the technical-and-organisational-measures narrative and
tightens each purpose sentence. Nothing factual is delegated to the model. The
categories, recipients and transfers are all decided by the deterministic scan;
the model only rewrites sentences, and any field it touches is recorded in
``ai_assisted_fields`` so a reviewer knows exactly what to double-check.

If no key is set, or the call fails for any reason, the record is returned
unchanged and the caller keeps the deterministic defaults. Absence of AI is a
supported, first-class mode, not an error.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .config import anthropic_api_key, anthropic_model

_ENDPOINT = "https://api.anthropic.com/v1/messages"
_TIMEOUT_SECONDS = 30


def available() -> bool:
    return anthropic_api_key() is not None


def _call_anthropic(prompt: str) -> str | None:
    key = anthropic_api_key()
    if not key:
        return None
    body = json.dumps({
        "model": anthropic_model(),
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        _ENDPOINT, data=body, method="POST",
        headers={
            "content-type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
        return None
    parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
    text = "".join(parts).strip()
    return text or None


def _extract_json(text: str) -> dict | None:
    cleaned = text.replace("```json", "").replace("```", "").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError:
        return None


def enhance_record(record: dict) -> dict:
    """Return the record with AI-refined prose, or unchanged if AI is unavailable."""
    if not available():
        record["ai_status"] = "disabled (no ANTHROPIC_API_KEY); deterministic draft used"
        return record

    purposes_in = [{"activity": p["activity"], "purpose": p["purpose"],
                    "data_categories": p["data_categories"]} for p in record["purposes"]]
    prompt = (
        "You are helping draft a GDPR Article 30 record of processing activities. "
        "Do not invent facts, recipients, retention periods or legal bases. Only "
        "rewrite the given sentences to be clear and professional. Return ONLY a "
        "JSON object, no preamble and no markdown fences, with exactly two keys:\n"
        '  "security_measures": a single polished paragraph rewriting the input '
        "measures text, adding no new specific claims;\n"
        '  "purposes": a list of objects {"activity", "purpose"} rewriting each '
        "purpose sentence more precisely given its data categories.\n\n"
        "INPUT security_measures:\n" + record["security_measures"] + "\n\n"
        "INPUT purposes (JSON):\n" + json.dumps(purposes_in)
    )

    raw = _call_anthropic(prompt)
    if not raw:
        record["ai_status"] = "call failed; deterministic draft retained"
        return record

    parsed = _extract_json(raw)
    if not parsed:
        record["ai_status"] = "unparseable response; deterministic draft retained"
        return record

    assisted = []
    if isinstance(parsed.get("security_measures"), str) and parsed["security_measures"].strip():
        record["security_measures"] = parsed["security_measures"].strip()
        assisted.append("security_measures")

    if isinstance(parsed.get("purposes"), list):
        by_activity = {p.get("activity"): p.get("purpose") for p in parsed["purposes"]
                       if isinstance(p, dict)}
        touched = False
        for p in record["purposes"]:
            new = by_activity.get(p["activity"])
            if isinstance(new, str) and new.strip():
                p["purpose"] = new.strip()
                touched = True
        if touched:
            assisted.append("purposes")

    record["ai_assisted_fields"] = assisted
    record["ai_status"] = f"enhanced ({', '.join(assisted)})" if assisted else "no changes applied"
    return record
