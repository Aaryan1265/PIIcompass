import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from piicompass.classifier import classify


class TestClassifier(unittest.TestCase):
    def test_identity_fields(self):
        for col in ["first_name", "last_name", "date_of_birth", "clinician_name"]:
            self.assertEqual(classify(col).category, "identity", col)

    def test_contact_fields(self):
        for col in ["email", "phone", "address_line1", "postal_code", "actor_email"]:
            self.assertEqual(classify(col).category, "contact", col)

    def test_financial_fields(self):
        for col in ["card_number", "card_expiry"]:
            self.assertEqual(classify(col).category, "financial", col)

    def test_government_id(self):
        self.assertEqual(classify("national_insurance_no").category, "government_id")

    def test_health_is_special(self):
        for col in ["diagnosis_code", "blood_type"]:
            c = classify(col)
            self.assertEqual(c.category, "health", col)
            self.assertTrue(c.special, col)

    def test_online_identifiers(self):
        for col in ["ip_address", "user_agent", "device_id", "session_id"]:
            self.assertEqual(classify(col).category, "online_identifier", col)

    def test_surrogate_and_foreign_keys_suppressed(self):
        for col in ["patient_id", "city_id", "contact_id", "id"]:
            self.assertIsNone(classify(col), col)

    def test_online_id_allowlist_beats_id_suppressor(self):
        self.assertEqual(classify("device_id").category, "online_identifier")
        self.assertEqual(classify("session_id").category, "online_identifier")

    def test_non_pii_returns_none(self):
        for col in ["created_at", "amount_cents", "currency", "consent_flag",
                    "action", "scheduled_for", "population", "contact_type",
                    "relationship", "page_url", "notes"]:
            self.assertIsNone(classify(col), col)

    def test_every_result_is_reproducible_and_carries_a_rule(self):
        c = classify("email")
        self.assertEqual(c, classify("email"))
        self.assertTrue(c.rule)
        self.assertTrue(c.rationale)


if __name__ == "__main__":
    unittest.main()
