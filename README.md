# Demo Server Monitoring

This demo monitors this Linux machine only. It does not connect to remote hosts.

## Run locally

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app app run --host 127.0.0.1 --port 5000
```

Open http://127.0.0.1:5000.

The dashboard starts empty. The server detail page shows labeled sample numbers until live metrics are added. The app listens on `127.0.0.1` only.
