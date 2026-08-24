import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_arm64_manifest_does_not_claim_jetson_validation() -> None:
    payload = json.loads((ROOT / "configs/arm64_cloud_manifest.json").read_text(encoding="utf-8"))
    assert payload["cpu_architecture"] == "aarch64"
    assert "Jetson FPS" in payload["forbidden_claims"]
    assert "not Jetson Orin evidence" in payload["warning"]
