from alembic import context

from alugai.db.engine import database_url, make_engine
from alugai.db.tables import metadata

VIEWS = {"listing_review_state", "published_listings", "published_listing_photos", "listing_public_status"}


def include_object(obj, name, type_, reflected, compare_to):
    return not (type_ == "table" and name in VIEWS)


url = context.config.get_main_option("sqlalchemy.url") or database_url()
engine = make_engine(url)
try:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata, include_object=include_object)
        with context.begin_transaction():
            context.run_migrations()
finally:
    engine.dispose()
