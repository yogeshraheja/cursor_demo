import sqlite3
import socket
from pathlib import Path
from types import SimpleNamespace

import psutil

from tests.conftest import csrf_token


class _Memory:
    total = 16_000_000_000
    used = 6_000_000_000
    available = 10_000_000_000
    percent = 37.5


class _Swap:
    total = 4_000_000_000
    used = 100_000_000


class _Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _install_mocks(monkeypatch, counters, connections):
    clock = _Clock()
    monkeypatch.setattr("app.metrics.time.monotonic", clock)
    monkeypatch.setattr("app.metrics.psutil.cpu_percent", lambda interval=None: 12.5)
    monkeypatch.setattr("app.metrics.psutil.getloadavg", lambda: (0.4, 0.35, 0.3))
    monkeypatch.setattr("app.metrics.psutil.virtual_memory", lambda: _Memory())
    monkeypatch.setattr("app.metrics.psutil.swap_memory", lambda: _Swap())
    monkeypatch.setattr(
        "app.metrics.psutil.net_if_addrs",
        lambda: {
            "lo": [SimpleNamespace(family=socket.AF_INET, address="127.0.0.1")],
            "eth0": [SimpleNamespace(family=socket.AF_INET, address="10.0.0.8")],
        },
    )
    monkeypatch.setattr(
        "app.metrics.psutil.net_io_counters",
        lambda pernic=True: counters,
    )
    monkeypatch.setattr(
        "app.metrics.psutil.net_connections",
        lambda kind="inet": connections,
    )
    monkeypatch.setattr(
        "app.metrics.psutil.Process",
        lambda pid: SimpleNamespace(name=lambda: "sshd" if pid == 7 else "other"),
    )
    return clock


def _counters(received, sent):
    return {
        "lo": SimpleNamespace(bytes_recv=9, bytes_sent=9),
        "eth0": SimpleNamespace(bytes_recv=received, bytes_sent=sent),
    }


def _connections():
    return [
        SimpleNamespace(
            status=psutil.CONN_ESTABLISHED,
            type=socket.SOCK_STREAM,
            laddr=SimpleNamespace(ip="10.0.0.8", port=40000),
            raddr=SimpleNamespace(ip="10.0.0.1", port=443),
            pid=9,
        ),
        SimpleNamespace(
            status=psutil.CONN_LISTEN,
            type=socket.SOCK_STREAM,
            laddr=SimpleNamespace(ip="0.0.0.0", port=22),
            raddr=(),
            pid=7,
        ),
        SimpleNamespace(
            status=psutil.CONN_NONE,
            type=socket.SOCK_DGRAM,
            laddr=SimpleNamespace(ip="0.0.0.0", port=53),
            raddr=(),
            pid=None,
        ),
    ]


def _add_server(auth_client):
    response = auth_client.post(
        "/servers/add",
        data={
            "display_name": "Lab host",
            "notes": "",
            "csrf_token": csrf_token(auth_client),
        },
    )
    assert response.status_code == 302


def test_no_server_row_returns_no_metrics(auth_client, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("psutil should not run without a server row")

    monkeypatch.setattr("app.metrics.psutil.cpu_percent", forbidden)
    monkeypatch.setattr("app.metrics.psutil.net_connections", forbidden)
    response = auth_client.get("/api/metrics")
    assert response.status_code == 200
    assert response.get_json() == {"metrics": None}
    assert response.headers["Cache-Control"] == "no-store"


def test_unauthenticated_metrics_are_rejected(client):
    response = client.get("/api/metrics")
    assert response.status_code == 401
    assert "busy_percent" not in response.get_data(as_text=True)


def test_metrics_api_with_psutil_mocked(auth_client, monkeypatch):
    counters = _counters(1_000, 500)
    clock = _install_mocks(monkeypatch, counters, _connections())
    _add_server(auth_client)

    first = auth_client.get("/api/metrics")
    body = first.get_json()["metrics"]
    assert first.status_code == 200
    assert set(body) == {"read_at", "cpu", "memory", "network", "ports"}
    assert body["cpu"] == {"busy_percent": 12.5, "load_average": [0.4, 0.35, 0.3]}
    assert body["memory"] == {
        "total": 16_000_000_000,
        "used": 6_000_000_000,
        "available": 10_000_000_000,
        "used_percent": 37.5,
        "swap_total": 4_000_000_000,
        "swap_used": 100_000_000,
    }
    assert body["network"] == [
        {
            "name": "eth0",
            "bytes_recv": 1_000,
            "bytes_sent": 500,
            "recv_rate": None,
            "sent_rate": None,
        }
    ]
    assert body["ports"] == [
        {
            "port": 22,
            "protocol": "TCP",
            "address": "0.0.0.0",
            "process": "sshd",
            "pid": 7,
        },
        {
            "port": 53,
            "protocol": "UDP",
            "address": "0.0.0.0",
            "process": "",
            "pid": None,
        },
    ]

    counters["eth0"] = SimpleNamespace(bytes_recv=3_000, bytes_sent=1_000)
    clock.now = 1005.0
    second = auth_client.get("/api/metrics").get_json()["metrics"]
    assert second["network"][0]["recv_rate"] == 400
    assert second["network"][0]["sent_rate"] == 100

    database = auth_client.application.config["DATABASE"]
    with sqlite3.connect(database) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        count = connection.execute("SELECT COUNT(*) FROM server").fetchone()[0]
    assert tables == {"server"}
    assert count == 1


def test_metrics_rejected_after_sign_out(auth_client, monkeypatch):
    _install_mocks(monkeypatch, _counters(1_000, 500), _connections())
    _add_server(auth_client)
    token = csrf_token(auth_client)
    assert auth_client.post("/logout", data={"csrf_token": token}).status_code == 302
    assert auth_client.get("/api/metrics").status_code == 401


def test_server_page_polls_same_origin_metrics(auth_client, monkeypatch):
    _install_mocks(monkeypatch, _counters(1_000, 500), _connections())
    _add_server(auth_client)
    page = auth_client.get("/server")
    body = page.get_data(as_text=True)
    script = Path("app/static/metrics.js").read_text()
    assert page.status_code == 200
    assert "Sample data" not in body
    assert "metrics.js" in body
    assert 'fetch("/api/metrics"' in script
    assert 'credentials: "same-origin"' in script
    assert "POLL_MS = 5000" in script
    assert "The latest read failed." in script
    assert "pagehide" in script
    assert "http://" not in script
    assert "https://" not in script


def test_workflow_generates_secrets_and_does_not_deploy():
    text = Path(".github/workflows/ci.yml").read_text().lower()
    assert "pytest" in text
    assert "generate_password_hash" in text
    assert "secrets.token_hex" in text
    assert "deploy" not in text
    assert "ssh" not in text
    assert "echo " not in text
    assert "scrypt:" not in text
