from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.web import mount_web


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<div id=root></div>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / "secret.txt").write_text("outside the build")
    app = FastAPI()

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    mount_web(app, str(dist))
    return TestClient(app)


def test_client_routes_fall_back_to_index(client: TestClient) -> None:
    resp = client.get("/cases/123")
    assert resp.status_code == 200
    assert "root" in resp.text
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
    assert resp.headers["cache-control"] == "no-cache"


def test_assets_are_served_with_long_cache(client: TestClient) -> None:
    resp = client.get("/assets/app.js")
    assert resp.text == "console.log(1)"
    assert "immutable" in resp.headers["cache-control"]


def test_api_paths_never_return_the_html_shell(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.get("/api/v1/unknown").status_code == 404
    assert client.get("/api").status_code == 404


def test_paths_cannot_escape_the_build(client: TestClient) -> None:
    resp = client.get("/assets/../../secret.txt")
    assert "outside the build" not in resp.text
    resp = client.get("/%2e%2e/secret.txt")
    assert "outside the build" not in resp.text


def test_missing_build_is_a_startup_error(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match=r"index\.html"):
        mount_web(FastAPI(), str(tmp_path))


@pytest.mark.parametrize(
    "url",
    [
        "postgres://u:p@h:5432/db",
        "postgresql://u:p@h:5432/db",
        "postgresql+psycopg://u:p@h:5432/db",
    ],
)
def test_hosted_database_urls_use_psycopg(url: str) -> None:
    assert Settings(database_url=url).database_url == "postgresql+psycopg://u:p@h:5432/db"
