"""
database.py - the only file that talks to PostgreSQL.

Every query in app.py goes through these small helper functions:
  query_all()  -> SELECT, returns many rows
  query_one()  -> SELECT, returns one row (or None)
  execute()    -> INSERT / UPDATE / DELETE, saves (commits) the change
  run_in_transaction() -> several changes that must succeed or fail together
  next_id()    -> next free primary key (the tables do not auto-number)

Values are always passed separately from the SQL text using %s
placeholders. psycopg2 escapes them, which prevents SQL injection.
"""

import psycopg2
from psycopg2.extras import RealDictCursor

import config


def get_connection():
    """Open a new connection to PostgreSQL using config.py."""
    return psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        connect_timeout=config.DB_CONNECT_TIMEOUT
    )


def query_all(sql, params=None):
    """Run a SELECT and return a list of dictionaries, one per row."""
    conn = get_connection()

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    finally:
        conn.close()


def query_one(sql, params=None):
    """Run a SELECT and return only the first row, or None if empty."""
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=None):
    """Run one INSERT / UPDATE / DELETE and commit it."""
    run_in_transaction([(sql, params)])


def run_in_transaction(statements):
    """
    Run a list of (sql, params) pairs as ONE transaction.

    If any statement fails, rollback() undoes all of them.
    """
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            for sql, params in statements:
                cur.execute(sql, params)

        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def next_id(table, column):
    """
    Tables use plain INT primary keys, so we calculate MAX(id) + 1.

    table/column come from our own code, not from user input.
    """
    row = query_one(
        f"SELECT COALESCE(MAX({column}), 0) + 1 AS new_id FROM {table}"
    )

    return row["new_id"]