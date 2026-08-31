"""Central configuration: single seed, canonical paths, and the data-category taxonomy.

Determinism note: SEED governs every ordering and any tie-break in the pipeline.
The pipeline never reads system time, hostname, or random state that is not seeded.
"""
from __future__ import annotations

import os
from pathlib import Path

# Single seed governs all ordering / tie-breaks. Byte-identical output is a
# credibility requirement, so nothing in the pipeline may depend on wall-clock
# time or unsorted set iteration.
SEED = 1729

# Repository root is two levels up from this file (src/piicompass/config.py).
PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_DIR.parent.parent

SAMPLE_APP_DIR = PROJECT_ROOT / "sample_app"
SCHEMA_FILE = SAMPLE_APP_DIR / "schema.sql"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"

# The sealed ground-truth directory. The scanning pipeline is FORBIDDEN to read
# anything under this path. Only evaluate.py may open it, and only after the
# pipeline has already produced its artifacts. firewall.py enforces this at both
# static-scan time and run time.
GROUND_TRUTH_DIR = PROJECT_ROOT / "ground_truth"
GROUND_TRUTH_FILE = GROUND_TRUTH_DIR / "expected_pii.json"

# GDPR data categories. "special" marks Article 9 special-category data, which
# carries a higher legal bar (explicit consent or another Article 9 condition).
CATEGORIES = {
    "identity": {
        "label": "Identity",
        "description": "Names, dates of birth and other direct identifiers.",
        "special": False,
    },
    "contact": {
        "label": "Contact",
        "description": "Email, phone, postal address and location of a person.",
        "special": False,
    },
    "financial": {
        "label": "Financial",
        "description": "Payment card, bank and billing details.",
        "special": False,
    },
    "government_id": {
        "label": "Government identifier",
        "description": "National insurance, passport, tax and similar state IDs.",
        "special": False,
    },
    "online_identifier": {
        "label": "Online identifier",
        "description": "IP address, device and session identifiers, user agent.",
        "special": False,
    },
    "credentials": {
        "label": "Authentication",
        "description": "Passwords, secrets, tokens and security answers.",
        "special": False,
    },
    "health": {
        "label": "Health (special category)",
        "description": "Diagnoses, clinical and other health data (Article 9).",
        "special": True,
    },
    "free_text": {
        "label": "Free text (possible PII)",
        "description": "Unstructured notes that may embed personal data.",
        "special": False,
    },
}


def anthropic_api_key() -> str | None:
    """Return the Anthropic API key if configured, else None.

    Absence is a supported state, not an error: the AI drafting layer falls back
    to deterministic templates.
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    return key or None


_DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def anthropic_model() -> str:
    return os.environ.get("ANTHROPIC_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
