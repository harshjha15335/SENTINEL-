from types import SimpleNamespace

import pytest

from app.workers import supervisor


@pytest.mark.parametrize(
    "value",
    [
        "",
        "*",
        "0.0.0.0/0",
        "::/0",
        "127.0.0.1,*",
        "0.0.0.0/1,128.0.0.0/1",
        "::/1,8000::/1",
        "proxy.example",
        "127.0.0.1,",
    ],
)
def test_hosted_unbounded_or_implicit_proxy_trust_fails_before_children(monkeypatch, value):
    monkeypatch.setattr(supervisor, "get_settings", lambda: SimpleNamespace(hosted_deployment=True))
    monkeypatch.setenv("SENTINEL_FORWARDED_ALLOW_IPS", value)

    def forbidden(*args, **kwargs):
        raise AssertionError("Unsafe proxy configuration must fail before launching processes")

    monkeypatch.setattr(supervisor.subprocess, "Popen", forbidden)
    with pytest.raises(SystemExit, match="bounded proxy IPs or CIDRs"):
        supervisor.main()


def test_explicit_proxy_networks_and_loopback_development():
    assert supervisor.forwarded_allow_ips("10.2.0.0/24, ::1", hosted=True) == "10.2.0.0/24,::1"
    assert supervisor.forwarded_allow_ips("", hosted=False) == "127.0.0.1"
