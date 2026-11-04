import os

from sqlalchemy import create_engine


def database_url():
    url = os.environ.get("ALUGAI_DATABASE_URL")
    if not url:
        raise RuntimeError("ALUGAI_DATABASE_URL ausente: rode `set -a; . ./.env.example; set +a`")
    return url


def make_engine(url=None):
    return create_engine(url or database_url())
