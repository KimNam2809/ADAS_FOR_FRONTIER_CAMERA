import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from common import redact  # noqa: E402


class SecretRedactionTest(unittest.TestCase):
    def test_redacts_named_secret(self):
        self.assertNotIn("abc123", redact("KAGGLE_API_TOKEN=abc123"))

    def test_redacts_runtime_token(self):
        old = os.environ.get("KAGGLE_API_TOKEN")
        os.environ["KAGGLE_API_TOKEN"] = "token-value-that-must-not-leak"
        try:
            self.assertNotIn("token-value-that-must-not-leak", redact("failed token-value-that-must-not-leak"))
        finally:
            if old is None:
                os.environ.pop("KAGGLE_API_TOKEN", None)
            else:
                os.environ["KAGGLE_API_TOKEN"] = old


if __name__ == "__main__":
    unittest.main()
