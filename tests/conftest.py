import pytest
from werkzeug.security import generate_password_hash

from app import create_app

TEST_PASSWORD = "temporary-test-password"


@pytest.fixture
def password():
    return TEST_PASSWORD


@pytest.fixture
def app(tmp_path, password):
    return create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "temporary-test-secret",
            "ADMIN_PASSWORD_HASH": generate_password_hash(password),
            "DATABASE": str(tmp_path / "monitoring.db"),
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client, password):
    response = client.post(
        "/login",
        data={"username": "admin", "password": password},
    )
    assert response.status_code == 302
    return client


def csrf_token(client):
    with client.session_transaction() as sess:
        return sess["csrf_token"]
