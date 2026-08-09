from pathlib import Path

import pytest

from layer3.config import Policy
from layer3.engine import DecisionEngine


ROOT_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def policy() -> Policy:
    return Policy.from_json(
        ROOT_DIR / "config" / "policy.json"
    )


@pytest.fixture
def engine(policy: Policy) -> DecisionEngine:
    return DecisionEngine(policy)