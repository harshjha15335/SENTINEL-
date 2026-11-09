import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "fixture_verification",
    Path(__file__).parents[2] / "scripts/verify-webhook-pipeline.py",
)
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "postgresql://sentinel:sentinel@localhost/sentinel",
        "postgresql://sentinel:sentinel@remote.example/sentinel_test",
    ],
)
def test_fixture_never_targets_a_user_or_remote_database(monkeypatch, value):
    monkeypatch.setenv("SENTINEL_FIXTURE_DATABASE_URL", value)
    with pytest.raises(SystemExit):
        fixture.fixture_database_url()


def test_fixture_requires_quiet_inbox_before_mutation():
    class Reply:
        def raise_for_status(self):
            pass

        def json(self):
            return [{"id": "historical", "status": "PENDING"}]

    class RPC:
        def get(self, *args, **kwargs):
            return Reply()

    with pytest.raises(RuntimeError, match="without active receipts"):
        fixture.inbox_snapshot(RPC(), "https://project.supabase.co")
