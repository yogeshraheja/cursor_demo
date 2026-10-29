import os
import secrets
import socket
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, abort, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from app.db import add_server, close_db, delete_server, get_server, init_db
from app.metrics import clear_rate_snapshot, read_metrics

ROOT = Path(__file__).resolve().parent.parent
USERNAME = "admin"
SIGN_IN_ERROR = "Sign-in failed."
ALREADY_MONITORED = "The local server is already monitored."
DISPLAY_NAME_MAX = 80
NOTES_MAX = 500
ADD_FIELDS = {"display_name", "notes", "csrf_token"}
REMOVE_FIELDS = {"csrf_token"}


def create_app(config=None):
    load_dotenv(ROOT / ".env")
    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ.get("FLASK_SECRET_KEY"),
        ADMIN_PASSWORD_HASH=os.environ.get("ADMIN_PASSWORD_HASH"),
        DATABASE=os.environ.get("MONITORING_DB", str(ROOT / "monitoring.db")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        DISPLAY_NAME_MAX=DISPLAY_NAME_MAX,
        NOTES_MAX=NOTES_MAX,
    )
    if config:
        app.config.update(config)
    if not app.config.get("SECRET_KEY") or not app.config.get("ADMIN_PASSWORD_HASH"):
        raise RuntimeError("FLASK_SECRET_KEY and ADMIN_PASSWORD_HASH must be set")

    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()

    @app.context_processor
    def inject_layout():
        logged_in = session.get("user") == USERNAME
        return {
            "logged_in": logged_in,
            "csrf_token": session.get("csrf_token", ""),
            "monitored_server": get_server() if logged_in else None,
        }

    @app.before_request
    def require_session():
        if request.endpoint in {"login", "static"}:
            return None
        if session.get("user") == USERNAME:
            return None
        if request.path.startswith("/api/"):
            return jsonify({"error": "Sign-in required."}), 401
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if session.get("user") == USERNAME:
            return redirect(url_for("dashboard"))
        if request.method == "GET":
            return render_template("login.html", error=None)
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        password_ok = check_password_hash(app.config["ADMIN_PASSWORD_HASH"], password)
        if username != USERNAME or not password_ok:
            return render_template("login.html", error=SIGN_IN_ERROR), 401
        session.clear()
        session["user"] = USERNAME
        session["csrf_token"] = secrets.token_urlsafe(32)
        return redirect(url_for("dashboard"))

    @app.post("/logout")
    def logout():
        _require_csrf()
        clear_rate_snapshot()
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    def dashboard():
        return render_template("dashboard.html", server=get_server())

    @app.get("/servers/add")
    @app.post("/servers/add")
    def add_server_page():
        if get_server() is not None:
            return render_template(
                "add_server.html",
                error=ALREADY_MONITORED,
                blocked=True,
                display_name="",
                notes="",
            )
        if request.method == "GET":
            return render_template(
                "add_server.html",
                error=None,
                blocked=False,
                display_name="",
                notes="",
            )
        if set(request.form) - ADD_FIELDS:
            abort(400, description="The form only accepts a display name and notes.")
        _require_csrf()
        display_name = request.form.get("display_name", "").strip()
        notes = request.form.get("notes", "").strip()
        error = _validate_server_fields(display_name, notes)
        if error:
            return (
                render_template(
                    "add_server.html",
                    error=error,
                    blocked=False,
                    display_name=display_name,
                    notes=notes,
                ),
                400,
            )
        saved = add_server(display_name, notes, socket.gethostname())
        if not saved:
            return render_template(
                "add_server.html",
                error=ALREADY_MONITORED,
                blocked=True,
                display_name="",
                notes="",
            )
        return redirect(url_for("dashboard"))

    @app.post("/servers/remove")
    def remove_server():
        if set(request.form) - REMOVE_FIELDS:
            abort(400, description="The remove form does not accept extra fields.")
        _require_csrf()
        delete_server()
        clear_rate_snapshot()
        return redirect(url_for("dashboard"))

    @app.get("/server")
    def server_detail():
        server = get_server()
        if server is None:
            return redirect(url_for("dashboard"))
        return render_template("server.html", server=server)

    @app.get("/api/metrics")
    def api_metrics():
        if get_server() is None:
            response = jsonify({"metrics": None})
        else:
            response = jsonify({"metrics": read_metrics()})
        response.headers["Cache-Control"] = "no-store"
        return response

    return app


def _require_csrf():
    token = session.get("csrf_token") or ""
    supplied = request.form.get("csrf_token") or ""
    if not token or not isinstance(supplied, str) or len(token) != len(supplied):
        abort(400, description="The form expired. Reload the page and try again.")
    if not secrets.compare_digest(token, supplied):
        abort(400, description="The form expired. Reload the page and try again.")


def _validate_server_fields(display_name, notes):
    if not display_name:
        return "Display name is required."
    if len(display_name) > DISPLAY_NAME_MAX:
        return f"Display name must be {DISPLAY_NAME_MAX} characters or fewer."
    if len(notes) > NOTES_MAX:
        return f"Notes must be {NOTES_MAX} characters or fewer."
    return None
