import os

from alembic import command
import pytest
from sqlalchemy import create_engine

from tests.dbsetup import alembic_config, ensure_database, reset_schema


@pytest.fixture(scope="session")
def test_database_url():
    url = os.environ.get("ALUGAI_TEST_DATABASE_URL")
    if not url:
        pytest.fail("ALUGAI_TEST_DATABASE_URL ausente: rode `set -a; . ./.env.example; set +a`")
    return url


@pytest.fixture(scope="session")
def migrated_url(test_database_url):
    ensure_database(test_database_url)
    reset_schema(test_database_url)
    command.upgrade(alembic_config(test_database_url), "head")
    return test_database_url


@pytest.fixture(scope="session")
def engine(migrated_url):
    instance = create_engine(migrated_url)
    yield instance
    instance.dispose()


@pytest.fixture
def db(engine):
    """A connection whose work is rolled back at the end of the test."""
    with engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()
