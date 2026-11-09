import importlib.util
import io
import json
from pathlib import Path
import urllib.error

import pytest

spec = importlib.util.spec_from_file_location(
    "deploy_sentinel", Path(__file__).parents[2] / "scripts/deploy-supabase-webhook.py"
)
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class Reply(io.BytesIO):
    status = 200

    def __init__(self, payload):
        super().__init__(json.dumps(payload).encode())


def test_missing_account_access_cannot_create_a_project(monkeypatch, tmp_path):
    monkeypatch.delenv("SUPABASE_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("SENTINEL_SUPABASE_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr("sys.argv", ["deploy"])
    with pytest.raises(SystemExit) as result:
        deploy.main()
    assert result.value.code == 2
    assert not (tmp_path / "state").exists()


@pytest.mark.parametrize("use_cli", [False, True])
def test_create_deploy_and_check_url_without_printing_password(
    monkeypatch, tmp_path, capsys, use_cli
):
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "test-access-token")
    monkeypatch.setenv("SUPABASE_CLI", "/test/supabase")
    monkeypatch.setenv("SENTINEL_SUPABASE_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("SUPABASE_ORGANIZATION_ID", raising=False)
    monkeypatch.setattr("sys.argv", ["deploy", "--use-cli"] if use_cli else ["deploy"])
    calls, commands, uploads = [], [], []

    def request(req, timeout):
        url = req if isinstance(req, str) else req.full_url
        method = "GET" if isinstance(req, str) else req.get_method()
        calls.append((url, method))
        if url.endswith("/organizations"):
            return Reply([{"id": "org-test"}])
        if url.endswith("/projects"):
            body = json.loads(req.data)
            assert body["organization_id"] == "org-test"
            assert len(body["db_pass"]) >= 32
            return Reply({"id": "testprojectreference"})
        if url.endswith("/projects/testprojectreference"):
            return Reply({"status": "ACTIVE_HEALTHY"})
        if url.endswith("/database/query"):
            assert "enable row level security" in json.loads(req.data)["query"]
            return Reply([])
        if url.endswith("/functions/deploy?slug=paypal-webhook"):
            assert "multipart/form-data" in req.get_header("Content-type")
            assert b'"verify_jwt": false' in req.data
            assert b'filename="supabase/functions/paypal-webhook/index.ts"' in req.data
            assert (
                b'filename="supabase/functions/paypal-webhook/receiver.ts"' in req.data
            )
            assert b"receiver_test.ts" not in req.data
            uploads.append(req)
            return Reply({"slug": "paypal-webhook", "status": "ACTIVE"})
        if method == "POST":
            raise urllib.error.HTTPError(url, 400, "Unsigned", {}, None)
        return Reply({"status": "ok"})

    monkeypatch.setattr(deploy.urllib.request, "urlopen", request)
    monkeypatch.setattr(
        deploy.subprocess, "run", lambda args, **kwargs: commands.append(args)
    )
    deploy.main()
    state = json.loads((tmp_path / "deployment.json").read_text())
    assert state["webhook_url"].endswith("/functions/v1/paypal-webhook")
    if use_cli:
        assert "--use-api" in commands[0] and "--no-verify-jwt" in commands[0]
    else:
        assert len(uploads) == 1 and not commands
    assert state["db_password"] not in capsys.readouterr().out
    assert (tmp_path / "deployment.json").stat().st_mode & 0o777 == 0o600
    deploy.main()  # Resume from the same project; never create a duplicate.
    assert (
        sum(url.endswith("/projects") and method == "POST" for url, method in calls)
        == 1
    )


def test_unknown_creation_outcome_does_not_automatically_create_again(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("SUPABASE_ACCESS_TOKEN", "test-access-token")
    monkeypatch.setenv("SUPABASE_CLI", "/test/supabase")
    monkeypatch.setenv("SENTINEL_SUPABASE_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("SUPABASE_ORGANIZATION_ID", raising=False)
    monkeypatch.setattr("sys.argv", ["deploy"])
    attempts = []

    def request(req, timeout):
        if req.full_url.endswith("/organizations"):
            return Reply([{"id": "org-test"}])
        if req.get_method() == "GET":
            return Reply([])
        attempts.append(req)
        raise urllib.error.URLError("ambiguous timeout")

    monkeypatch.setattr(deploy.urllib.request, "urlopen", request)
    with pytest.raises(SystemExit):
        deploy.main()
    with pytest.raises(SystemExit):
        deploy.main()
    assert len(attempts) == 1
