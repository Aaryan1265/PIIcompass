"""Draft a GDPR Article 30(1) record of processing activities.

Everything the scan can evidence is filled in from the schema and code analysis:
the categories of personal data (c), the categories of recipients (d), and the
transfers to third countries with their safeguards (e). Fields the scan cannot
know are left as clearly marked placeholders for the controller or DPO to
complete, rather than being invented. The security-measures narrative (g) has a
deterministic default that the optional AI layer may refine.
"""
from __future__ import annotations

from .config import CATEGORIES

# Map a processing function to a plain-language purpose.
_PURPOSE_MAP = {
    "register_patient": "Registration and administration of patient accounts.",
    "add_emergency_contact": "Maintaining emergency contact details for patients.",
    "record_health": "Recording and managing clinical and health information.",
    "book_appointment": "Scheduling appointments and sending reminders.",
    "charge_patient": "Taking payment for services and issuing receipts.",
    "track_pageview": "Website and product analytics.",
    "export_patient_csv": "Bulk export of patient records for reporting.",
}

# Infer categories of data subjects from which PII-bearing tables exist.
_SUBJECTS_BY_TABLE = {
    "patients": "Patients",
    "contacts": "Emergency contacts (third parties)",
    "appointments": "Clinical staff",
    "audit_log": "Staff users",
    "analytics_events": "Website visitors",
}

_PLACEHOLDER = "TO BE COMPLETED BY THE CONTROLLER / DPO"
PLACEHOLDER = _PLACEHOLDER  # public alias for templates


def _humanize(fn: str) -> str:
    return fn.replace("_", " ").strip().capitalize() + "."


def default_security_measures() -> str:
    return (
        "Access to personal data is restricted on a need-to-know basis. Data in "
        "transit is protected with TLS. Payment card data is handled by a PCI-DSS "
        "compliant processor and is not stored in clear text. Application activity "
        "is recorded in an audit log. These are baseline measures inferred from the "
        "codebase and must be reviewed and completed by the controller."
    )


def build_record(schema: list[dict], code: dict, graph: dict,
                 security_measures: str | None = None,
                 controller: dict | None = None) -> dict:
    pii_cols = [c for c in schema if c["is_pii"]]

    # (c) categories of personal data
    cat_keys = sorted({c["category"] for c in pii_cols})
    data_categories = []
    for k in cat_keys:
        meta = CATEGORIES.get(k, {"label": k, "description": "", "special": False})
        examples = sorted({f"{c['table']}.{c['column']}" for c in pii_cols if c["category"] == k})
        data_categories.append({
            "category": k,
            "label": meta["label"],
            "special": meta["special"],
            "description": meta["description"],
            "examples": examples,
        })
    special_present = any(dc["special"] for dc in data_categories)

    # (c) categories of data subjects
    tables_with_pii = sorted({c["table"] for c in pii_cols})
    subjects = sorted({_SUBJECTS_BY_TABLE[t] for t in tables_with_pii if t in _SUBJECTS_BY_TABLE})

    # (b) purposes, one per processing activity
    purposes = []
    for act in graph["activities"]:
        fn = act["function"]
        purposes.append({
            "activity": fn,
            "purpose": _PURPOSE_MAP.get(fn, _humanize(fn)),
            "data_categories": act["categories"],
            "special": act["special"],
        })

    # (d) recipients and (e) transfers
    recipients, transfers = [], []
    for dest in graph["destinations"]:
        if dest["kind"] != "external_service":
            continue
        recipients.append({
            "recipient": dest["label"],
            "role": dest.get("role"),
            "country": dest.get("country"),
            "data_categories": dest["categories"],
            "special": dest["special"],
        })
        if dest.get("third_country"):
            transfers.append({
                "recipient": dest["label"],
                "country": dest.get("country"),
                "safeguard": dest.get("safeguard") or _PLACEHOLDER,
                "data_categories": dest["categories"],
                "special": dest["special"],
            })
    recipients.sort(key=lambda r: r["recipient"])
    transfers.sort(key=lambda t: t["recipient"])

    ctrl = {
        "name": _PLACEHOLDER,
        "contact": _PLACEHOLDER,
        "dpo_contact": _PLACEHOLDER,
    }
    if controller:
        ctrl.update({k: v for k, v in controller.items() if v})

    record = {
        "title": "Record of processing activities (GDPR Article 30(1))",
        "status": "DRAFT - auto-generated from a code and schema scan; requires human review",
        "controller": ctrl,
        "purposes": purposes,
        "data_subjects": subjects,
        "data_categories": data_categories,
        "special_category_present": special_present,
        "recipients": recipients,
        "third_country_transfers": transfers,
        "retention": {
            "policy": _PLACEHOLDER,
            "note": "Retention periods cannot be inferred from code and must be "
                    "set per data category and legal basis.",
        },
        "security_measures": security_measures or default_security_measures(),
        "ai_assisted_fields": [],
    }
    return record


def to_markdown(record: dict) -> str:
    """Render the record as a human-readable markdown document."""
    lines = [f"# {record['title']}", "", f"Status: {record['status']}", ""]

    ctrl = record["controller"]
    lines += ["## (a) Controller", "",
              f"- Name: {ctrl['name']}",
              f"- Contact: {ctrl['contact']}",
              f"- Data protection officer: {ctrl['dpo_contact']}", ""]

    lines += ["## (b) Purposes of processing", ""]
    for p in record["purposes"]:
        cats = ", ".join(p["data_categories"]) or "none detected"
        special = " (includes special-category data)" if p["special"] else ""
        lines.append(f"- {p['activity']}: {p['purpose']} Data: {cats}.{special}")
    lines.append("")

    lines += ["## (c) Categories of data subjects", ""]
    for s in record["data_subjects"]:
        lines.append(f"- {s}")
    lines.append("")

    lines += ["## (c) Categories of personal data", ""]
    for dc in record["data_categories"]:
        tag = " [SPECIAL CATEGORY, Article 9]" if dc["special"] else ""
        lines.append(f"- {dc['label']}{tag}: {', '.join(dc['examples'])}")
    lines.append("")

    lines += ["## (d) Categories of recipients", ""]
    if record["recipients"]:
        for r in record["recipients"]:
            lines.append(
                f"- {r['recipient']} ({r['role']}, {r['country']}): "
                f"{', '.join(r['data_categories'])}"
            )
    else:
        lines.append("- No external recipients detected.")
    lines.append("")

    lines += ["## (e) Transfers to third countries", ""]
    if record["third_country_transfers"]:
        for t in record["third_country_transfers"]:
            lines.append(
                f"- {t['recipient']} ({t['country']}): safeguard = {t['safeguard']}; "
                f"data = {', '.join(t['data_categories'])}"
            )
    else:
        lines.append("- No transfers outside the EEA detected.")
    lines.append("")

    lines += ["## (f) Retention", "",
              f"- {record['retention']['policy']}",
              f"- {record['retention']['note']}", ""]

    lines += ["## (g) Technical and organisational security measures", "",
              record["security_measures"], ""]

    return "\n".join(lines)
