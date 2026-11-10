"""Pure snapshot regressions: never imports the API test DB/truncation fixtures."""

import copy
import importlib.util
import os
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "static_validator", Path(__file__).parents[1] / "validate_static_demo.py"
)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


@pytest.fixture
def snapshot():
    directory = os.environ.get("SENTINEL_TEST_SNAPSHOT")
    if not directory:
        pytest.skip("SENTINEL_TEST_SNAPSHOT must point to a generated fixture export")
    return validator.read_snapshot(Path(directory))


def test_export_closure_and_original_regression(snapshot):
    assert validator.validate(snapshot)["unresolved_references"] == 0
    case = next(c for c in snapshot["cases"] if c["id"] == "73823607-ce2b-4090-9fd4-d1e3119f28d6")
    assert case["transaction_id"] == "1e054580-49f1-48be-a7a4-a4d4cf23647d"
    assert any(t["id"] == case["transaction_id"] for t in snapshot["transactions"])


@pytest.mark.parametrize(
    "corruption",
    ["orphan", "risk", "details", "extras", "dashboard", "counts", "origin", "sensitive"],
)
def test_reject_corrupt_export(snapshot, corruption):
    data = copy.deepcopy(snapshot)
    tid = data["cases"][0]["transaction_id"]
    if corruption == "orphan":
        data["cases"][0]["transaction_id"] = "00000000-0000-0000-0000-000000000000"
    elif corruption == "risk":
        data["risk"][next(iter(data["risk"]))]["transaction_id"] = tid + "bad"
    elif corruption == "details":
        data["case-details"][data["cases"][0]["id"]]["transaction_id"] = "bad"
    elif corruption == "extras":
        data["transaction-extras"][tid]["id"] = tid
    elif corruption == "dashboard":
        data["dashboard"]["recent"][0]["id"] = "bad"
    elif corruption == "counts":
        data["snapshot"]["counts"]["transactions"] += 1
    elif corruption == "origin":
        data["transactions"][-1]["data_origin"] = "MERCHANT_PROVIDED"
    else:
        data["model"]["password"] = "should-never-ship"  # noqa: S105 - rejected fixture value
    with pytest.raises(ValueError):
        validator.validate(data)
