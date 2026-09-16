import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_candidate import evaluate  # noqa: E402


GATES = {
    "static_metrics": {
        "detector_precision_min": 0.95,
        "detector_recall_min": 0.95,
        "detector_map50_min": 0.98,
        "detector_map50_95_min": 0.82,
        "speed_top1_min": 0.98,
    }
}


class QualityGateTest(unittest.TestCase):
    def test_passes_matching_metrics(self):
        metrics = {
            "detector_precision": 0.96,
            "detector_recall": 0.96,
            "detector_map50": 0.99,
            "detector_map50_95": 0.83,
            "speed_top1": 0.99,
        }
        self.assertEqual((True, []), evaluate(metrics, GATES))

    def test_missing_metric_rejects(self):
        passed, failures = evaluate({}, GATES)
        self.assertFalse(passed)
        self.assertGreater(len(failures), 0)


if __name__ == "__main__":
    unittest.main()

