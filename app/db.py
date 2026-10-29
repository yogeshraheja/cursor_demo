import sqlite3

from flask import current_app, g


def get_db():
    if "db" not in g:
        connection = sqlite3.connect(current_app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db():
    connection = get_db()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS server (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            display_name TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            hostname TEXT NOT NULL
        )
        """
    )
    connection.commit()


def get_server():
    row = get_db().execute(
        "SELECT display_name, notes, hostname FROM server WHERE id = 1"
    ).fetchone()
    if row is None:
        return None
    return {
        "display_name": row["display_name"],
        "notes": row["notes"],
        "hostname": row["hostname"],
    }


def add_server(display_name, notes, hostname):
    connection = get_db()
    try:
        connection.execute(
            "INSERT INTO server (id, display_name, notes, hostname) VALUES (1, ?, ?, ?)",
            (display_name, notes, hostname),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        connection.rollback()
        return False
    return True


def delete_server():
    connection = get_db()
    connection.execute("DELETE FROM server WHERE id = 1")
    connection.commit()
