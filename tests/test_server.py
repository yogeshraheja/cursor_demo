import socket
import sqlite3

from werkzeug.security import generate_password_hash

from app import create_app
from tests.conftest import csrf_token


def test_add_duplicate_and_remove(auth_client):
    saved = auth_client.post(
        "/servers/add",
        data={
            "display_name": "Lab host",
            "notes": "near the window",
            "csrf_token": csrf_token(auth_client),
        },
        follow_redirects=True,
    )
    body = saved.get_data(as_text=True)
    assert saved.status_code == 200
    assert "Lab host" in body
    assert "near the window" in body
    assert socket.gethostname() in body

    duplicate = auth_client.post(
        "/servers/add",
        data={
            "display_name": "Second",
            "notes": "should not save",
            "csrf_token": csrf_token(auth_client),
        },
    )
    duplicate_body = duplicate.get_data(as_text=True)
    assert "The local server is already monitored." in duplicate_body
    assert "should not save" not in duplicate_body

    removed = auth_client.post(
        "/servers/remove",
        data={"csrf_token": csrf_token(auth_client)},
        follow_redirects=True,
    )
    assert "No server monitored yet." in removed.get_data(as_text=True)
    assert "Lab host" not in removed.get_data(as_text=True)


def test_row_still_exists_after_reopening_the_database(tmp_path):
    password = "temporary-test-password"
    config = {
        "TESTING": True,
        "SECRET_KEY": "temporary-test-secret",
        "ADMIN_PASSWORD_HASH": generate_password_hash(password),
        "DATABASE": str(tmp_path / "monitoring.db"),
    }
    first = create_app(config)
    client = first.test_client()
    assert client.post("/login", data={"username": "admin", "password": password}).status_code == 302
    added = client.post(
        "/servers/add",
        data={
            "display_name": "Lab host",
            "notes": "rack A",
            "csrf_token": csrf_token(client),
        },
    )
    assert added.status_code == 302

    second = create_app(dict(config))
    reopened = second.test_client()
    assert reopened.post("/login", data={"username": "admin", "password": password}).status_code == 302
    page = reopened.get("/")
    body = page.get_data(as_text=True)
    assert "Lab host" in body
    assert "rack A" in body

    with sqlite3.connect(config["DATABASE"]) as connection:
        count = connection.execute("SELECT COUNT(*) FROM server").fetchone()[0]
    assert count == 1


def test_add_form_has_no_credential_fields(auth_client):
    body = auth_client.get("/servers/add").get_data(as_text=True)
    assert 'name="display_name"' in body
    assert 'name="notes"' in body
    assert 'name="address"' not in body
    assert 'name="username"' not in body
    assert 'name="password"' not in body
    assert 'name="key"' not in body


def test_add_rejects_address_username_key_and_password(auth_client):
    response = auth_client.post(
        "/servers/add",
        data={
            "display_name": "Lab host",
            "notes": "",
            "address": "10.1.1.1",
            "username": "root",
            "password": "secret-value",
            "key": "ssh-rsa",
            "csrf_token": csrf_token(auth_client),
        },
    )
    assert response.status_code == 400
    assert "secret-value" not in response.get_data(as_text=True)
    page = auth_client.get("/")
    assert "No server monitored yet." in page.get_data(as_text=True)


def test_add_and_remove_require_csrf(auth_client):
    missing = auth_client.post(
        "/servers/add",
        data={"display_name": "Lab host", "notes": ""},
    )
    assert missing.status_code == 400
    assert "No server monitored yet." in auth_client.get("/").get_data(as_text=True)

    saved = auth_client.post(
        "/servers/add",
        data={
            "display_name": "Lab host",
            "notes": "",
            "csrf_token": csrf_token(auth_client),
        },
    )
    assert saved.status_code == 302
    rejected = auth_client.post("/servers/remove", data={})
    assert rejected.status_code == 400
    assert "Lab host" in auth_client.get("/").get_data(as_text=True)


def test_display_name_is_required_and_length_limited(auth_client):
    empty = auth_client.post(
        "/servers/add",
        data={
            "display_name": "   ",
            "notes": "",
            "csrf_token": csrf_token(auth_client),
        },
    )
    assert empty.status_code == 400
    assert "Display name is required." in empty.get_data(as_text=True)

    too_long = auth_client.post(
        "/servers/add",
        data={
            "display_name": "n" * 81,
            "notes": "p" * 501,
            "csrf_token": csrf_token(auth_client),
        },
    )
    assert too_long.status_code == 400
    assert "80" in too_long.get_data(as_text=True)
    assert "No server monitored yet." in auth_client.get("/").get_data(as_text=True)
