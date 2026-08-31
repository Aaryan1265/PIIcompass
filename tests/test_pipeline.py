import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from piicompass.article30 import to_markdown
from piicompass.evaluate import evaluate
from piicompass.pipeline import run_pipeline, write_artifacts


class TestDeterminism(unittest.TestCase):
    def test_artifacts_are_byte_identical_across_runs(self):
        with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
            m1 = write_artifacts(run_pipeline(use_ai=False), out_dir=Path(d1))
            m2 = write_artifacts(run_pipeline(use_ai=False), out_dir=Path(d2))
            self.assertEqual(m1, m2)
            for name in m1:
                b1 = (Path(d1) / name).read_bytes()
                b2 = (Path(d2) / name).read_bytes()
                self.assertEqual(b1, b2, name)


class TestEvaluation(unittest.TestCase):
    def setUp(self):
        self.result = run_pipeline(use_ai=False)
        self.ev = evaluate(self.result["schema"])

    def test_precision_recall_in_expected_range(self):
        self.assertAlmostEqual(self.ev["precision"], 0.909, places=2)
        self.assertAlmostEqual(self.ev["recall"], 0.952, places=2)
        self.assertAlmostEqual(self.ev["f1"], 0.93, places=2)

    def test_special_category_recall_perfect(self):
        self.assertEqual(self.ev["special_category_recall"], 1.0)
        self.assertEqual(self.ev["special_category_n"], 2)

    def test_known_false_negative_is_free_text(self):
        fns = {(d["table"], d["column"]) for d in self.ev["false_negative_detail"]}
        self.assertIn(("patients", "notes"), fns)

    def test_known_false_positives_are_reference_data(self):
        fps = {(d["table"], d["column"]) for d in self.ev["false_positive_detail"]}
        self.assertIn(("cities", "city_name"), fps)
        self.assertIn(("analytics_events", "geo_region"), fps)

    def test_sample_size_reported(self):
        self.assertEqual(self.ev["n_columns_evaluated"], 48)
        self.assertEqual(self.ev["ground_truth_pii"], 21)
        self.assertEqual(self.ev["scanner_flagged"], 22)


class TestArticle30(unittest.TestCase):
    def setUp(self):
        self.record = run_pipeline(use_ai=False)["record"]

    def test_all_sections_present(self):
        for key in ["controller", "purposes", "data_subjects", "data_categories",
                    "recipients", "third_country_transfers", "retention",
                    "security_measures"]:
            self.assertIn(key, self.record)

    def test_special_category_flagged(self):
        self.assertTrue(self.record["special_category_present"])

    def test_transfers_have_safeguards(self):
        self.assertTrue(self.record["third_country_transfers"])
        for t in self.record["third_country_transfers"]:
            self.assertTrue(t["safeguard"])

    def test_controller_left_for_human(self):
        self.assertIn("TO BE COMPLETED", self.record["controller"]["name"])

    def test_markdown_renders_all_headings(self):
        md = to_markdown(self.record)
        for heading in ["(a) Controller", "(b) Purposes", "(c) Categories of personal data",
                        "(d) Categories of recipients", "(e) Transfers to third countries",
                        "(f) Retention", "(g) Technical and organisational"]:
            self.assertIn(heading, md)


if __name__ == "__main__":
    unittest.main()
