import json
import unittest
from pathlib import Path


class NoAutoPromoteTest(unittest.TestCase):
    def test_release_gate_disables_auto_promote(self):
        root = Path(__file__).resolve().parents[1]
        gates = json.loads((root / "configs/sign_release_gates.yaml").read_text(encoding="utf-8"))
        self.assertFalse(gates["auto_promote"])
        self.assertTrue(gates["human_gate_required"])

    def test_workflows_do_not_push_model_changes(self):
        repo = Path(__file__).resolve().parents[2]
        text = "\n".join(path.read_text(encoding="utf-8") for path in (repo / ".github/workflows").glob("kaggle-*.yml"))
        self.assertNotIn("git push", text)
        self.assertNotIn("AUTO_PROMOTE=true", text)


if __name__ == "__main__":
    unittest.main()
