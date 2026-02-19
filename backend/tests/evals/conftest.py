import json
from pathlib import Path

import pytest


EVAL_USER_ID = "eval-test-user"
GROUND_TRUTH_PATH = Path(__file__).resolve().parent / "fixtures" / "ground_truth_rag.json"


def load_ground_truth_dataset():
    with open(GROUND_TRUTH_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def ground_truth_samples():
    return load_ground_truth_dataset()
