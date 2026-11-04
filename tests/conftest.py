import os

import pytest


@pytest.fixture(scope="session")
def test_database_url():
    url = os.environ.get("ALUGAI_TEST_DATABASE_URL")
    if not url:
        pytest.fail("ALUGAI_TEST_DATABASE_URL ausente: rode `set -a; . ./.env.example; set +a`")
    return url
