import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from piicompass import firewall
from piicompass.config import GROUND_TRUTH_FILE


class TestFirewall(unittest.TestCase):
    def test_static_scan_is_clean(self):
        self.assertEqual(firewall.check_static(), [])

    def test_assert_static_clean_does_not_raise(self):
        firewall.assert_static_clean()  # should not raise

    def test_booby_trap_blocks_sealed_read(self):
        with self.assertRaises(PermissionError):
            with firewall.sealed():
                with open(GROUND_TRUTH_FILE, encoding="utf-8") as handle:
                    handle.read()

    def test_reading_is_allowed_outside_seal(self):
        # Outside the sealed context, the evaluator may read the key.
        data = GROUND_TRUTH_FILE.read_text(encoding="utf-8")
        self.assertIn("columns", data)

    def test_seal_reactivates_after_context(self):
        # A normal file open inside seal (not the ground truth) is fine.
        with firewall.sealed():
            self.assertTrue((ROOT / "requirements.txt").read_text())
        # And the ground truth is blocked again if re-sealed.
        with self.assertRaises(PermissionError):
            with firewall.sealed():
                open(GROUND_TRUTH_FILE).read()


if __name__ == "__main__":
    unittest.main()
