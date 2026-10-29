# Demo Server Monitoring

This demo monitors this Linux machine only. It does not connect to remote hosts.

## Run locally

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app app run --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000 and sign in as `admin` / `demo-admin`.

The app listens on `127.0.0.1` only. Copying `.env.example` to `.env` provides `FLASK_SECRET_KEY` and `ADMIN_PASSWORD_HASH`. `.env` stays on this machine and is not committed.

There is no in-app password change. To replace the password, generate a Werkzeug hash and restart:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('new-password'))"
```

Paste the printed hash into `ADMIN_PASSWORD_HASH` in `.env`, then start Flask again. You can replace `FLASK_SECRET_KEY` with a new random string at the same time. The old session cookie stops working after the secret changes.

GitHub Actions runs the tests on push and pull request. The workflow generates a test-only secret and password hash in the job. It does not print those values, and it does not deploy. Start the app on this machine with `flask run`.

## One local server

A signed-in admin can add this machine once. The form asks for a display name (required, 80 characters or fewer) and notes (optional, 500 characters or fewer). The hostname is read from the machine. The form does not accept an address, username, key, or password.

If a server is already saved, another add is blocked and the page says the local server is already monitored. Remove deletes that row and the dashboard returns to “No server monitored yet.”

The record is stored in `monitoring.db` next to the app. That file is local and gitignored. Restarting the app keeps the row.

## Metrics

Values are live and are not saved. The server page requests `GET /api/metrics` every 5 seconds and updates the current sections in place. The first network sample leaves the rate blank. Later samples show the rate since the previous read. A failed read does not clear the last good snapshot; the page says the latest read failed. Signing out stops the refresh.

- CPU: overall busy percent and load average for 1, 5, and 15 minutes.
- Memory: total, used, available, and used percent.
- Swap: total and used.
- Network: each non-loopback interface name, received bytes, sent bytes, and the rate since the previous read.
- Listening ports: TCP and UDP port, protocol, bind address, process name, and PID.

Metrics are collected only while a server row exists. The server page is read-only. It has no process, port, or service controls.
