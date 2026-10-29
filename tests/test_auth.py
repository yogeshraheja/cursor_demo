from pathlib import Path

import pytest
from werkzeug.security import check_password_hash

from app import create_app


def test_valid_login(client, password):
    response = client.post(
        "/login",
        data={"username": "admin", "password": password},
        follow_redirects=True,
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "No server monitored yet." in body
    assert "Sign-in failed." not in body


def test_wrong_password(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "not-the-password"},
    )
    body = response.get_data(as_text=True)
    assert response.status_code == 401
    assert "Sign-in failed." in body
    assert "not-the-password" not in body
    assert "No server monitored yet." not in body


def test_wrong_username_matches_wrong_password(client):
    wrong_user = client.post(
        "/login",
        data={"username": "root", "password": "nope"},
    )
    wrong_password = client.post(
        "/login",
        data={"username": "admin", "password": "nope"},
    )
    assert wrong_user.status_code == 401
    assert wrong_password.status_code == 401
    assert "Sign-in failed." in wrong_user.get_data(as_text=True)
    assert wrong_user.get_data() == wrong_password.get_data()


@pytest.mark.parametrize("path", ["/", "/server", "/servers/add"])
def test_missing_session_redirects(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_sign_out(auth_client):
    with auth_client.session_transaction() as sess:
        token = sess["csrf_token"]
    response = auth_client.post("/logout", data={"csrf_token": token})
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    follow = auth_client.get("/")
    assert follow.status_code == 302
    assert follow.headers["Location"].endswith("/login")


def test_session_cookie_is_httponly_and_lax(client, password):
    response = client.post(
        "/login",
        data={"username": "admin", "password": password},
    )
    cookie = response.headers["Set-Cookie"]
    assert "HttpOnly" in cookie
    assert "SameSite=Lax" in cookie


def test_example_env_uses_demo_password_hash():
    values = {}
    for line in Path(".env.example").read_text().splitlines():
        key, value = line.split("=", 1)
        values[key] = value
    assert values["FLASK_SECRET_KEY"]
    assert check_password_hash(values["ADMIN_PASSWORD_HASH"], "demo-admin")


def test_app_requires_secret_and_hash(monkeypatch):
    monkeypatch.setattr("app.load_dotenv", lambda *_args, **_kwargs: None)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD_HASH", raising=False)
    with pytest.raises(RuntimeError):
        create_app()


def test_local_secrets_are_gitignored():
    ignored = Path(".gitignore").read_text().splitlines()
    assert ".env" in ignored
    assert "monitoring.db" in ignored
