from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_account_tokens_are_named_and_not_duplicated_in_submit_script() -> None:
    submit = (ROOT / "scripts/submit_object_v3_pilot.ps1").read_text(encoding="utf-8")
    preflight = (ROOT / "scripts/finetune_preflight.ps1").read_text(encoding="utf-8")
    selector = (ROOT / "scripts/kaggle_account_preflight.ps1").read_text(encoding="utf-8")
    assert "KAGGLE_API_TOKEN_ACCOUNT_1" in submit
    assert "^KAGGLE_API_TOKEN=" not in submit
    assert "KAGGLE_API_TOKEN_ACCOUNT_1" in preflight
    assert "KAGGLE_API_TOKEN_ACCOUNT_2" in preflight
    assert "KAGGLE_API_TOKEN_ACCOUNT_$Account" in selector


def test_account_preflight_is_read_only() -> None:
    selector = (ROOT / "scripts/kaggle_account_preflight.ps1").read_text(encoding="utf-8")
    assert "kernels push" not in selector
    assert "mutation_performed = $false" in selector
    assert "secret_logged = $false" in selector
    assert "PrivateDataset" in selector
    assert "AUTH_PASS_PRIVATE_ACCESS_PENDING" in selector
    assert "datasets files" in selector
    assert "datasets status $slug" not in selector
