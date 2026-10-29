# Demo Server Monitoring — Requirements

Local demo for internal infrastructure and application teams. The app runs on the Linux machine where Cursor is running and shows a live, read-only view of that machine. It does not connect to remote hosts.

## Problem

L1, L2, and L3 teams currently sign in to servers to check memory, CPU, network, and listening ports. This demo replaces that check for the local machine with one web page.

## Users

Intended audience: internal L1, L2, and L3 teams in infrastructure and application development.

Demo access: one shared admin account. Separate team logins are out of scope.

## Goal

A signed-in user can open a browser on this machine, see current CPU, memory, network, and listening-port data, and add or remove the local server from the monitored list.

## Demo constraints

- Runs locally on the Cursor machine. Bind to `127.0.0.1` only.
- Monitors that same Linux machine. No SSH, agents, or remote credentials.
- One monitored server record: the local host.
- Live numbers only. No history, charts, or saved samples.
- Metric pages are read-only. The only writes are add server, remove server, and sign-in.
- Small Flask app. Server-rendered pages, one CSS file, and a short script that refreshes numbers. No frontend build step.

## Features

### 1. Read-only monitoring UI

The monitoring screens show data and nothing else. There is no control to kill a process, close a port, change a service, or edit a metric.

The layout is a simple operations view: a server list, then one server page with clear sections for CPU, memory, network, and listening ports. Numbers refresh in place every 5 seconds.

### 2. Admin sign-in

- Username is fixed: `admin`.
- The password is not stored in plain text. The app stores a Werkzeug password hash in a local `.env` file (`ADMIN_PASSWORD_HASH`).
- The demo ships with a known password, `demo-admin`, as a hash in `.env.example`.
- To change it, generate a new hash, replace `ADMIN_PASSWORD_HASH` in `.env`, and restart the app. There is no password-change screen.
- Failed sign-in shows a generic error. Successful sign-in uses a Flask session cookie.
- Every page except sign-in requires a session.

### 3. Add and remove the local server

A signed-in admin can add the local Linux machine to the monitored list and remove it.

Add form fields:

| Field | Required | Notes |
| --- | --- | --- |
| Display name | Yes | Shown on the dashboard. |
| Notes | No | Free text for the team. |

The hostname is taken from the machine. The form does not ask for an address, SSH user, key, or password.

Rules:

- At most one server. If it already exists, add is unavailable and the page says the local server is already monitored.
- Remove deletes that record. Metrics are not collected while the list is empty.
- Server records are stored in a local SQLite file, `monitoring.db`, next to the app.

## Metrics

Collected with `psutil` from the local host only, while a server record exists. The server page polls `GET /api/metrics` every 5 seconds and updates the page.

| Area | What is shown |
| --- | --- |
| CPU | Overall busy percent and load average (1, 5, 15 minutes). |
| Memory | Total, used, available, and used percent. Swap total and used. |
| Network | For each non-loopback interface: name, received bytes, sent bytes, and the rate since the previous sample. |
| Ports | Listening TCP and UDP sockets only: port, protocol, bind address, process name, PID. |

The first network sample shows totals and leaves the rate blank. Later samples show the rate. Nothing is written to disk as history.

## Screens

| Screen | What the user sees |
| --- | --- |
| Sign in | Username, password, submit. |
| Dashboard | The local server card, or an empty state with **Add server**. **Remove** sits on the card. |
| Add server | Display name, notes, save. |
| Server detail | Read-only CPU, memory, network, and listening ports. Shows the time of the last successful read. |

## Out of scope

- Remote Linux or Windows hosts, SSH, and agents.
- More than one server, server edit, or extra user accounts.
- Alerts, thresholds, history, charts, and exports.
- Changing processes, firewall rules, or the password in the UI.
- Deploying beyond this machine.

## Local run

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
flask --app app run
```

Open `http://127.0.0.1:5000` and sign in as `admin` / `demo-admin`.

Change the password:

```bash
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('new-password'))"
```

Paste the printed hash into `ADMIN_PASSWORD_HASH` in `.env` and restart Flask.

## Acceptance

- Unsigned users can only open the sign-in page.
- `admin` with the password that matches `ADMIN_PASSWORD_HASH` reaches the dashboard. A wrong password does not.
- With no server saved, the dashboard offers add and shows no metrics.
- Add saves one local server. A second add is blocked.
- The server page shows CPU, memory, network, and listening ports, and those values refresh about every 5 seconds.
- The server page has no action that changes the host.
- Remove clears the server. The dashboard returns to the empty state.
- Restarting the app keeps the server record and still accepts the same admin login.
