"""PIICompass: automated PII data-flow mapper and GDPR Article 30 record drafter.

All analysis in this package is deterministic and rule-based. The optional AI
layer (see ai_draft.py) only rewrites prose in the processing record and always
degrades gracefully to a deterministic template when no API key is present.
"""

__version__ = "1.0.0"
