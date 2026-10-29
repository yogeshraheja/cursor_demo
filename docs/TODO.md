# Implementation TODO

Small steps for the local demo in [requirements.md](requirements.md). Do one checkbox group at a time. The app runs only on this machine (`127.0.0.1`). GitHub Actions runs tests. There is no remote deploy job.

## 1. Project initialization and basic UI

- [x] Add `requirements.txt` with Flask, a `app` package, `templates/`, and `static/style.css`.
- [x] Add a base layout and a dashboard page with an empty state: “No server monitored yet.”
- [x] Add a server detail page with static placeholder blocks for CPU, memory, network, and listening ports.
- [x] Serve the app with `flask --app app run --host 127.0.0.1 --port 5000`.
- [x] Add `.gitignore` for `.venv/`, `.env`, `monitoring.db`, and `__pycache__/`.

**Security**

- [x] Bind to `127.0.0.1` only. Do not listen on `0.0.0.0`.
- [x] Do not add secrets, SSH keys, or remote-host fields.
- [x] Label placeholder numbers as sample data so they cannot be mistaken for live host data.

**Documentation**

- [x] Add a short `README.md` with the venv, install, and local run commands.
- [x] State that the demo monitors this Linux machine only.

## 2. Sign-in and unit tests

- [x] Add `.env.example` with `FLASK_SECRET_KEY` and `ADMIN_PASSWORD_HASH` (Werkzeug hash of `demo-admin`).
- [x] Load `.env` at startup. Username is fixed as `admin`. Check the password with `check_password_hash`.
- [x] Add a sign-in page, a generic failure message, a session cookie, and sign-out.
- [x] Require a session on every page except sign-in.
- [x] Add pytest coverage for: valid login, wrong password, wrong username, missing session redirect, and sign-out.

**Security**

- [x] Store only the password hash. Do not log the password or the hash.
- [x] Use a generic error for every failed sign-in.
- [x] Set the session cookie `HttpOnly` and `SameSite=Lax`. Read `FLASK_SECRET_KEY` from the environment.
- [x] Keep `.env` out of git. Tests must use a temporary hash, not a production secret.

**Documentation**

- [x] Document `admin` / `demo-admin`, copying `.env.example` to `.env`, and how to replace `ADMIN_PASSWORD_HASH`.
- [x] Note that there is no in-app password change.

## 3. GitHub Actions CI

- [x] Add `.github/workflows/ci.yml` to run on push and pull request.
- [x] The job installs dependencies and runs pytest.
- [x] Pass a test-only `FLASK_SECRET_KEY` and `ADMIN_PASSWORD_HASH` as job env values generated in the workflow, not committed live secrets.

**Security**

- [x] Do not store credentials in the workflow file. Do not print env values.
- [x] Do not add a deploy, SSH, or publish step. Release stays `flask run` on this machine.

**Documentation**

- [x] Add a `README.md` note: CI runs tests on GitHub; the app is started locally.

## 4. Local server record

- [x] Add SQLite `monitoring.db` with one server row: display name, notes, hostname.
- [x] Set hostname from the local machine. The form asks only for display name (required) and notes (optional).
- [x] Save the first server. If one exists, block another add and say the local server is already monitored.
- [x] Remove deletes the row and returns the dashboard to the empty state.
- [x] Test add, duplicate add, remove, and “row still exists after reopening the database.”

**Security**

- [x] Use parameterized queries. Limit display name and notes length.
- [x] Require a session and a CSRF token on add and remove.
- [x] Do not accept an address, username, key, or password field.

**Documentation**

- [x] Document the one-server rule and that `monitoring.db` is local and gitignored.

## 5. Read-only metrics

- [x] Collect CPU, memory, swap, network totals, and listening TCP/UDP ports with `psutil` only when a server row exists.
- [x] Add session-protected `GET /api/metrics`.
- [x] Fill the server page from that response. Show the time of the last successful read.
- [x] Leave the network rate blank on the first sample. On the next sample, show the rate since the previous read. Do not store samples.
- [x] Test the API with `psutil` mocked, including “no server row returns no metrics.”

**Security**

- [x] Do not run shell commands built from request data.
- [x] Return only the fields in the PRD. The page has no process, port, or service controls.
- [x] Reject unauthenticated calls to `/api/metrics`.

**Documentation**

- [x] In `README.md`, list each metric in one line and state that values are live and not saved.

## 6. Five-second refresh

- [x] Poll `/api/metrics` every 5 seconds from the server page and update the existing sections in place.
- [x] If the request fails, keep the last numbers and show that the latest read failed.

**Security**

- [x] Use a same-origin request only. Do not add third-party scripts.
- [x] Stop polling after sign-out.

**Documentation**

- [x] Note the 5-second refresh and that a failed read does not clear the last good snapshot.

## 7. Acceptance pass

- [x] Walk through the acceptance list in `docs/requirements.md` on `http://127.0.0.1:5000`.
- [ ] Confirm CI is green on the same commit.

**Security**

- [x] Confirm `.env` and `monitoring.db` are untracked, the app is bound to `127.0.0.1`, and metric pages stay read-only.

**Documentation**

- [x] Update `README.md` so the run, sign-in, add, remove, and hash-rotation steps match the app.
