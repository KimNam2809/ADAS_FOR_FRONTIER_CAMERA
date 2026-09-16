import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from preflight import validate_config  # noqa: E402


class PreflightTest(unittest.TestCase):
    def test_valid_config(self):
        config = {
            "run_mode": "pilot",
            "kernel_slug": "x",
            "source_package": "kaggle/train_sign_phase2",
            "detector_epochs": 1,
            "classifier_epochs": 1,
            "gpu_required": True,
        }
        self.assertEqual([], validate_config(config))

    def test_rejects_cpu_and_zero_epoch(self):
        config = {
            "run_mode": "pilot",
            "kernel_slug": "x",
            "source_package": "x",
            "detector_epochs": 0,
            "classifier_epochs": 1,
            "gpu_required": False,
        }
        errors = validate_config(config)
        self.assertIn("epochs_must_be_positive", errors)
        self.assertIn("gpu_must_be_required", errors)


if __name__ == "__main__":
    unittest.main()

