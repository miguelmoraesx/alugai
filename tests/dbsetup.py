"""Create the test databases; refuses any database without the `_test` suffix."""
import re

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

# Postgres truncates identifiers at 63 bytes, which would drop the suffix.
TEST_DATABASE = re.compile(r"[a-z0-9_]{1,58}_test")


def ensure_database(url):
    parsed = make_url(url)
    name = parsed.database or ""
    if not TEST_DATABASE.fullmatch(name):
        raise ValueError(f"Banco sem sufixo _test: {name!r}")
    admin = parsed.set(drivername="postgresql", database="postgres")
    with psycopg.connect(admin.render_as_string(hide_password=False), autocommit=True) as connection:
        if not connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
