import glob
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from piicompass.code_scanner import scan_code
from piicompass.config import SAMPLE_APP_DIR, SCHEMA_FILE
from piicompass.schema_scanner import scan_schema


class TestSchemaScanner(unittest.TestCase):
    def setUp(self):
        self.schema = scan_schema(SCHEMA_FILE)

    def test_column_count(self):
        self.assertEqual(len(self.schema), 48)

    def test_pii_count(self):
        self.assertEqual(sum(1 for c in self.schema if c["is_pii"]), 22)

    def test_special_count(self):
        self.assertEqual(sum(1 for c in self.schema if c["special"]), 2)

    def test_deterministic_order(self):
        again = scan_schema(SCHEMA_FILE)
        self.assertEqual(self.schema, again)


class TestCodeScanner(unittest.TestCase):
    def setUp(self):
        self.code = scan_code(sorted(glob.glob(str(SAMPLE_APP_DIR / "*.py"))))
        self.flows = self.code["flows"]

    def _flow(self, function, sink_kind, target_contains):
        for f in self.flows:
            if (f["function"] == function and f["sink_kind"] == sink_kind
                    and target_contains in f["target"]):
                return f
        return None

    def test_collection_points_found(self):
        self.assertGreaterEqual(len(self.code["collection_points"]), 20)

    def test_card_data_crosses_border_to_stripe(self):
        f = self._flow("charge_patient", "external_service", "Stripe")
        self.assertIsNotNone(f)
        self.assertTrue(f["third_country"])
        self.assertEqual(f["iso"], "US")
        self.assertIn("financial", f["categories"])

    def test_health_flow_is_special(self):
        f = self._flow("record_health", "datastore", "health_records")
        self.assertIsNotNone(f)
        self.assertTrue(f["special"])
        self.assertIn("health", f["categories"])

    def test_eu_email_vendor_is_not_a_transfer(self):
        f = self._flow("book_appointment", "external_service", "Mailjet")
        self.assertIsNotNone(f)
        self.assertFalse(f["third_country"])

    def test_csv_export_carries_government_id(self):
        f = self._flow("export_patient_csv", "export", "CSV")
        self.assertIsNotNone(f)
        self.assertIn("government_id", f["categories"])

    def test_names_leak_into_logs(self):
        f = self._flow("register_patient", "log", "logs")
        self.assertIsNotNone(f)
        self.assertIn("identity", f["categories"])


if __name__ == "__main__":
    unittest.main()
