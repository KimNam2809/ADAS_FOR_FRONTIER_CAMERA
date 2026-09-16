import json
import unittest
from pathlib import Path


class RunRequestSchemaTest(unittest.TestCase):
    def test_schema_is_fail_closed(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / "schemas/run_request.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("account", schema["required"])
        self.assertEqual(["account_1", "account_2"], schema["properties"]["account"]["enum"])


if __name__ == "__main__":
    unittest.main()
