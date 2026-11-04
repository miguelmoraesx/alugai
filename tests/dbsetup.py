"""Create the test databases; refuses any database without the `_test` suffix."""
from pathlib import Path
import re

import psycopg
from psycopg import sql
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parent.parent
# Postgres truncates identifiers at 63 bytes, which would drop the suffix.
TEST_DATABASE = re.compile(r"[a-z0-9_]{1,58}_test")


def _test_url(url):
    parsed = make_url(url)
    # A query such as ?dbname=alugai would override the database the check just saw.
    if not TEST_DATABASE.fullmatch(parsed.database or "") or parsed.query:
        raise ValueError(f"Banco sem sufixo _test, ou URL com parâmetros: {parsed.database!r}")
    return parsed


def ensure_database(url):
    parsed = _test_url(url)
    name = parsed.database
    admin = parsed.set(drivername="postgresql", database="postgres")
    with psycopg.connect(admin.render_as_string(hide_password=False), autocommit=True) as connection:
        if not connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", (name,)).fetchone():
            connection.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))


def reset_schema(url):
    """Drop everything in a test database, so each run starts from the migrations."""
    target = _test_url(url).set(drivername="postgresql")
    with psycopg.connect(target.render_as_string(hide_password=False), autocommit=True) as connection:
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("CREATE SCHEMA public")


def alembic_config(url):
    from alembic.config import Config

    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return config
