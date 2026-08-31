"""Vendor lexicon.

Maps a token that may appear in a call site (a client variable name or a
function name) to the third-party recipient it represents, plus the transfer
metadata GDPR Article 30(1)(d) and (e) require: who receives the data, in which
country, and whether that is a transfer outside the EEA that needs a safeguard.

Country judgements are from the point of view of an EU or EEA controller: the
United States is a third country, so a transfer there needs a safeguard such as
Standard Contractual Clauses. This lexicon is editable data, not a model; extend
it for your own stack.
"""
from __future__ import annotations

# token -> recipient metadata
VENDOR_LEXICON: dict[str, dict] = {
    "stripe": {
        "recipient": "Stripe Payments (payment processor)",
        "country": "United States", "iso": "US",
        "role": "processor", "third_country": True,
        "safeguard": "Standard Contractual Clauses",
    },
    "sendgrid": {
        "recipient": "Twilio SendGrid (transactional email)",
        "country": "United States", "iso": "US",
        "role": "processor", "third_country": True,
        "safeguard": "Standard Contractual Clauses",
    },
    "mixpanel": {
        "recipient": "Mixpanel (product analytics)",
        "country": "United States", "iso": "US",
        "role": "processor", "third_country": True,
        "safeguard": "Standard Contractual Clauses",
    },
    "amplitude": {
        "recipient": "Amplitude (product analytics)",
        "country": "United States", "iso": "US",
        "role": "processor", "third_country": True,
        "safeguard": "Standard Contractual Clauses",
    },
    "segment": {
        "recipient": "Segment (customer data platform)",
        "country": "United States", "iso": "US",
        "role": "processor", "third_country": True,
        "safeguard": "Standard Contractual Clauses",
    },
    "mailjet": {
        "recipient": "Mailjet (transactional email)",
        "country": "France", "iso": "FR",
        "role": "processor", "third_country": False,
        "safeguard": None,
    },
    "postmark": {
        "recipient": "Postmark (transactional email)",
        "country": "United States", "iso": "US",
        "role": "processor", "third_country": True,
        "safeguard": "Standard Contractual Clauses",
    },
}


def match_vendor(*name_parts: str) -> dict | None:
    """Return vendor metadata if any lexicon token appears in the given names."""
    haystack = "_".join(p for p in name_parts if p).lower()
    if not haystack:
        return None
    # Deterministic: iterate the lexicon in sorted key order.
    for token in sorted(VENDOR_LEXICON):
        if token in haystack:
            record = dict(VENDOR_LEXICON[token])
            record["token"] = token
            return record
    return None
