"""Deterministic PII classifier.

Given a column or field identifier, decide whether it is likely to hold personal
data and, if so, which GDPR data category it belongs to. Every decision is
reproducible and carries the exact rule that fired, so a reviewer can audit or
override it. There is no learned model and no randomness here.

Design trade-off (documented on purpose):
  - Columns whose name ends in ``_id`` are treated as internal surrogate or
    foreign keys and are NOT flagged, EXCEPT for a small allow-list of online
    identifiers (device_id, session_id, ...). This suppresses primary/foreign
    key false positives at the cost of missing any custom ``*_id`` that happens
    to be personal. That trade-off is surfaced in the limitations panel.
  - Name-based scanning cannot see inside free-text columns, so a ``notes``
    column that embeds personal data will be missed. This is a real limitation
    of this class of tool and is reported, not hidden.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Classification:
    identifier: str
    category: str
    special: bool
    confidence: float
    rule: str
    rationale: str


# Online identifiers that legitimately end in ``_id`` and must survive the
# surrogate-key suppressor below. Checked before the ``_id`` rule.
_ONLINE_ID_ALLOWLIST = {
    "device_id",
    "session_id",
    "cookie_id",
    "visitor_id",
    "advertising_id",
    "advertiser_id",
    "gaid",
    "idfa",
    "client_id_hash",
}

# Rules are evaluated in this order; the first match wins. Higher-sensitivity
# categories are placed first so, for example, a health field is never demoted
# to a generic identity field.
#
# Each rule: (category, rule_name, regex, confidence, rationale)
_RULES: list[tuple[str, str, str, float, str]] = [
    # --- Authentication / secrets -------------------------------------------
    ("credentials", "secret_material",
     r"(?:^|_)(password|passwd|pwd|secret|api_key|apikey|access_token|"
     r"refresh_token|token|mfa_secret|otp|security_answer|security_question)(?:_|$)",
     0.96, "Field name denotes authentication material or a shared secret."),

    # --- Government identifiers ---------------------------------------------
    ("government_id", "state_identifier",
     r"(?:^|_)(ssn|sin|social_insurance|national_insurance|nino|passport|"
     r"passport_no|national_id|tax_id|tin|drivers_license|license_no|license_number)(?:_|$)",
     0.95, "Field name denotes a government-issued identifier."),

    # --- Financial ----------------------------------------------------------
    ("financial", "payment_instrument",
     r"(?:^|_)(card|card_number|card_no|cardnumber|credit_card|card_expiry|"
     r"cvv|cvc|iban|account_number|acct_no|sort_code|routing_number|"
     r"bank_account|payment_method)(?:_|$)",
     0.93, "Field name denotes a payment card or bank detail."),
    ("financial", "compensation",
     r"(?:^|_)(salary|income|wage|net_pay|gross_pay)(?:_|$)",
     0.8, "Field name denotes compensation, which is personal financial data."),

    # --- Health / special category (Article 9) ------------------------------
    ("health", "clinical_data",
     r"(?:^|_)(diagnosis|blood|blood_type|medical|clinical|health|disability|"
     r"allergy|medication|icd|symptom|treatment|prescription)(?:_|$)",
     0.9, "Field name denotes health data, a special category under Article 9."),

    # --- Online identifiers -------------------------------------------------
    ("online_identifier", "network_or_device",
     r"(?:^|_)(ip|ip_address|user_agent|useragent|device_id|session_id|"
     r"cookie|cookie_id|mac_address|imei|advertising_id|visitor_id|fingerprint)(?:_|$)",
     0.85, "Field name denotes an online, network or device identifier."),

    # --- Identity -----------------------------------------------------------
    ("identity", "person_name",
     r"(?:^|_)(name|first_name|last_name|full_name|surname|forename|given_name|"
     r"maiden_name|middle_name)(?:_|$)",
     0.86, "Field name denotes a person's name."),
    ("identity", "birth_or_demographic",
     r"(?:^|_)(dob|date_of_birth|birth|birthdate|gender|nationality|"
     r"marital_status)(?:_|$)",
     0.84, "Field name denotes a birth or demographic attribute of a person."),

    # --- Contact / location -------------------------------------------------
    ("contact", "electronic_contact",
     r"(?:^|_)(email|e_mail|mail|phone|mobile|tel|telephone|fax)(?:_|$)",
     0.9, "Field name denotes an electronic contact point."),
    ("contact", "postal_or_location",
     r"(?:^|_)(address|addr|street|city|town|postal|postal_code|postcode|zip|"
     r"zipcode|country|county|region|geo|latitude|longitude)(?:_|$)",
     0.6, "Field name denotes a postal or geographic attribute (review: may be "
          "reference data rather than a person's location)."),
]

_COMPILED = [(cat, name, re.compile(rx), conf, why) for cat, name, rx, conf, why in _RULES]


def _normalize(identifier: str) -> str:
    """Lower-case and collapse any run of non-alphanumerics to a single ``_``."""
    return re.sub(r"[^a-z0-9]+", "_", identifier.strip().lower()).strip("_")


def classify(identifier: str) -> Classification | None:
    """Classify a single identifier. Returns None when it is not flagged as PII."""
    norm = _normalize(identifier)
    if not norm:
        return None

    # Online identifiers that end in _id must be caught before the _id suppressor.
    if norm in _ONLINE_ID_ALLOWLIST:
        return Classification(
            identifier=identifier,
            category="online_identifier",
            special=False,
            confidence=0.88,
            rule="online_id_allowlist",
            rationale="Field is an allow-listed online identifier ending in _id.",
        )

    # Surrogate / foreign keys: not personal data on their own.
    if norm == "id" or norm.endswith("_id"):
        return None

    for category, rule_name, pattern, confidence, rationale in _COMPILED:
        if pattern.search(norm):
            special = category == "health"
            return Classification(
                identifier=identifier,
                category=category,
                special=special,
                confidence=confidence,
                rule=rule_name,
                rationale=rationale,
            )
    return None
