from __future__ import annotations

import argparse
import json
from pathlib import Path

from .config import Policy
from .contracts import Layer2_KinematicsOutput
from .engine import DecisionEngine


def run_replay(
    input_path: str,
    policy_path: str,
) -> None:
    input_file = Path(input_path)

    with input_file.open(
        "r",
        encoding="utf-8",
    ) as file:
        raw_data = json.load(file)

    layer2_input = Layer2_KinematicsOutput.model_validate(
        raw_data
    )

    policy = Policy.from_json(policy_path)
    engine = DecisionEngine(policy)

    output = engine.evaluate(layer2_input)

    print(output.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RoadWatch Layer 3 replay"
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Path to Layer 2 JSON scenario",
    )

    parser.add_argument(
        "--policy",
        default="config/policy.json",
        help="Path to policy JSON",
    )

    args = parser.parse_args()

    run_replay(
        input_path=args.input,
        policy_path=args.policy,
    )


if __name__ == "__main__":
    main()