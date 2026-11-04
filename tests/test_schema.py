import os

from alembic import command
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from tests import factories as f
from tests.dbsetup import alembic_config, ensure_database, reset_schema

TABLES = {"sources", "neighborhoods", "collection_runs", "listings", "listing_versions", "captures",
          "reviews", "listing_photos"}
PUBLIC_VIEWS = {"published_listings", "published_listing_photos", "listing_public_status"}
VIEWS = PUBLIC_VIEWS | {"listing_review_state"}


def violates(db, constraint, action):
    with pytest.raises(IntegrityError) as caught, db.begin_nested():
        action()
    assert caught.value.orig.diag.constraint_name == constraint


def test_t1_1_up_down_up(test_database_url):
    url = make_url(test_database_url).set(database="alugai_mig_test").render_as_string(hide_password=False)
    ensure_database(url)
    reset_schema(url)
    config = alembic_config(url)
    engine = create_engine(url)

    def objects():
        inspector = inspect(engine)
        return set(inspector.get_table_names()) - {"alembic_version"}, set(inspector.get_view_names())

    def site_can_use_schema():
        with engine.connect() as connection:
            return connection.execute(text("SELECT has_schema_privilege('alugai_site', 'public', 'USAGE')")).scalar_one()

    try:
        command.upgrade(config, "head")
        assert objects() == (TABLES, VIEWS)
        assert site_can_use_schema()
        command.downgrade(config, "0001")
        assert objects()[1] == set()
        assert not site_can_use_schema()
        command.downgrade(config, "base")
        assert objects() == (set(), set())
        command.upgrade(config, "head")
        assert objects() == (TABLES, VIEWS)
        assert site_can_use_schema()
    finally:
        engine.dispose()


def test_t1_4_money_is_numeric_and_dates_are_timestamptz(db):
    rows = db.execute(text(
        "SELECT table_name, column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = 'public' AND table_name = ANY(:tables)"), {"tables": list(TABLES)}).all()
    assert rows
    wrong = [row for row in rows if
             (row.column_name.endswith("_amount") and row.data_type != "numeric")
             or (row.column_name.endswith("_at") and row.data_type != "timestamp with time zone")]
    assert wrong == []
    money = {row.column_name for row in rows if row.data_type == "numeric"}
    assert {"rent_amount", "condo_amount", "iptu_amount", "resolved_condo_amount", "resolved_iptu_amount"} <= money


def test_t1_5_identity_and_public_id(db):
    source_a, source_b = f.source(db), f.source(db)
    neighborhood = f.neighborhood(db)
    f.listing(db, source_a, neighborhood, external_id="1", public_id="aaaaaaaaaa")
    f.listing(db, source_b, neighborhood, external_id="1")
    violates(db, "uq_listings_identity", lambda: f.listing(db, source_a, neighborhood, external_id="1"))
    violates(db, "listings_public_id_key", lambda: f.listing(db, source_a, neighborhood, public_id="aaaaaaaaaa"))
    violates(db, "ck_listings_public_id", lambda: f.listing(db, source_a, neighborhood, public_id="iiiiiiiiii"))
    violates(db, "ck_listings_public_id", lambda: f.listing(db, source_a, neighborhood, public_id="curto"))


def test_t1_6_zero_parking_is_valid(db):
    assert f.listing(db, f.source(db), f.neighborhood(db), parking_spaces=0)


@pytest.mark.parametrize("constraint,overrides", [
    ("ck_listings_parking", {"parking_spaces": -1}),
    ("ck_listings_coords_pair", {"latitude": "-3.1", "location_precision": "approximate"}),
    ("ck_listings_precision_coords", {"latitude": "-3.1", "longitude": "-60.0"}),
    ("ck_listings_condo_consistent", {"condo_status": "reported", "condo_amount": None}),
    ("ck_listings_condo_consistent", {"condo_status": "unknown", "condo_amount": "10"}),
    ("ck_listings_iptu_consistent", {"iptu_status": "reported", "iptu_amount": None}),
    ("ck_listings_iptu_consistent", {"iptu_status": "unknown", "iptu_amount": "10"}),
    ("ck_listings_bedrooms", {"bedrooms": -1}),
    ("ck_listings_bathrooms", {"bathrooms": -1}),
    ("ck_listings_area", {"area_m2": "0"}),
    ("ck_listings_area", {"area_m2": "NaN"}),
    ("ck_listings_rent", {"rent_amount": "NaN"}),
    ("ck_listings_condo_amount", {"condo_amount": "-1"}),
    ("ck_listings_condo_amount", {"condo_amount": "NaN"}),
    ("ck_listings_iptu_amount", {"iptu_amount": "-1"}),
    ("ck_listings_iptu_amount", {"iptu_amount": "NaN"}),
    ("ck_listings_lat", {"latitude": "91", "longitude": "-60", "location_precision": "approximate"}),
    ("ck_listings_lng", {"latitude": "-3", "longitude": "181", "location_precision": "approximate"}),
    ("ck_listings_hash", {"content_hash": "curto"}),
    ("ck_listings_rent", {"rent_amount": "0"}),
    ("ck_listings_url_https", {"source_url": "http://fonte.example/1"}),
    ("ck_listings_invalid_pair", {"invalid_since": "2026-11-01T00:00:00Z"}),
    ("ck_listings_withdrawn_complete", {"withdrawn_at": "2026-11-01T00:00:00Z"}),
    ("ck_listings_expiry_after_seen", {"expires_at": "2026-10-01T00:00:00Z"}),
])
def test_t1_6_listing_constraints(db, constraint, overrides):
    source, neighborhood = f.source(db), f.neighborhood(db)
    violates(db, constraint, lambda: f.listing(db, source, neighborhood, **overrides))


@pytest.mark.parametrize("constraint,overrides", [
    ("ck_sources_approved_needs_terms", {"terms_result": None, "terms_checked_at": None, "terms_checked_by": None}),
    ("ck_sources_approved_needs_terms", {"terms_result": "prohibited"}),
    ("ck_sources_terms_complete", {"status": "candidate", "terms_checked_by": None}),
    ("ck_sources_blocked_has_reason", {"collection_state": "blocked"}),
    ("sources_slug_check", {"slug": "Com Espaco"}),
])
def test_t1_6_source_constraints(db, constraint, overrides):
    violates(db, constraint, lambda: f.source(db, **overrides))


@pytest.mark.parametrize("constraint,overrides", [
    ("ck_photos_position", {"position": 6}),
    ("ck_photos_path", {"storage_path": "../fora.jpg"}),
    ("ck_photos_path", {"storage_path": "/etc/passwd"}),
    ("ck_photos_stored_complete", {"sha256": None}),
    ("ck_photos_deleted_no_path", {"status": "deleted"}),
    ("ck_photos_type", {"content_type": "image/gif"}),
    ("ck_photos_sha", {"sha256": "curto"}),
])
def test_t1_6_photo_constraints(db, constraint, overrides):
    listing = f.listing(db, f.source(db), f.neighborhood(db))
    violates(db, constraint, lambda: f.photo(db, listing, **overrides))


def test_t1_6_photo_url_cannot_repeat_in_a_listing(db):
    listing = f.listing(db, f.source(db), f.neighborhood(db))
    url = "https://fonte.example/foto.jpg"
    f.photo(db, listing, source_url=url, position=1)
    violates(db, "uq_photos_url", lambda: f.photo(db, listing, source_url=url, position=2))


def test_t1_6_photo_position_cannot_repeat(db):
    listing = f.listing(db, f.source(db), f.neighborhood(db))
    f.photo(db, listing, position=1)
    violates(db, "uq_photos_position", lambda: f.photo(db, listing, position=1))
    assert f.photo(db, listing, position=None)
    assert f.photo(db, listing, position=None)


@pytest.mark.parametrize("constraint,overrides", [
    ("ck_reviews_reason_required", {"decision": "rejected", "reason": None}),
    ("ck_reviews_hash", {"content_hash": "curto"}),
    ("ck_reviews_reviewer", {"reviewer": "  "}),
    ("ck_reviews_decision", {"decision": "talvez", "reason": "x"}),
    ("ck_reviews_condo", {"resolved_condo_status": "needs_review"}),
    ("ck_reviews_resolved_only_approved", {"decision": "rejected", "reason": "x", "resolved_condo_status": "unknown"}),
    ("ck_reviews_condo_pair", {"resolved_condo_status": "reported"}),
    ("ck_reviews_iptu_pair", {"resolved_iptu_status": "unknown", "resolved_iptu_amount": "1"}),
    ("ck_reviews_resolved_amounts", {"resolved_condo_status": "reported", "resolved_condo_amount": "-900"}),
    ("ck_reviews_resolved_amounts", {"resolved_condo_status": "reported", "resolved_condo_amount": "NaN"}),
    ("ck_reviews_resolved_amounts", {"resolved_iptu_status": "reported", "resolved_iptu_amount": "-2400"}),
    ("ck_reviews_resolved_amounts", {"resolved_iptu_status": "reported", "resolved_iptu_amount": "NaN"}),
])
def test_t1_6_review_constraints(db, constraint, overrides):
    listing = f.listing(db, f.source(db), f.neighborhood(db))
    violates(db, constraint, lambda: f.review(db, listing, **overrides))


@pytest.mark.parametrize("constraint,column,value", [
    ("ck_versions_hash", "content_hash", "curto"),
    ("ck_versions_property_type", "property_type", "castelo"),
    ("ck_versions_rent_period", "rent_period", "semanal"),
    ("ck_versions_condo_status", "condo_status", "talvez"),
    ("ck_versions_iptu_status", "iptu_status", "talvez"),
    ("ck_versions_iptu_period", "iptu_period", "semanal"),
    ("ck_versions_pet", "pet_policy", "talvez"),
])
def test_t1_6_version_constraints(db, constraint, column, value):
    listing = f.listing(db, f.source(db), f.neighborhood(db))
    values = {"listing_id": listing, "observed_at": "2026-11-01T00:00:00Z", "content_hash": f.HASH_A,
              "adapter_version": "1", "source_title": "t", "property_type": "house", "rent_amount": "1",
              "rent_period": "monthly", "condo_status": "unknown", "iptu_status": "unknown",
              "iptu_period": "unknown", "pet_policy": "unknown", "neighborhood_raw": "b", "city": "Manaus",
              column: value}
    violates(db, constraint, lambda: f.insert(db, "listing_versions", values))


@pytest.mark.parametrize("constraint,overrides", [
    ("ck_captures_raw_path", {"raw_path": "../fora.html", "raw_expires_at": "2026-11-08T00:00:00Z"}),
    ("ck_captures_raw_pair", {"raw_path": "amostra.html"}),
])
def test_t1_6_capture_raw_constraints(db, constraint, overrides):
    source = f.source(db)
    run = f.insert(db, "collection_runs", {"mode": "collect", "source_id": source})
    values = {"run_id": run, "source_id": source, "kind": "page", "url": "https://fonte.example/1",
              "fetched_at": "2026-11-01T00:00:00Z", "result": "accepted", **overrides}
    violates(db, constraint, lambda: f.insert(db, "captures", values))


@pytest.fixture
def site_engine(migrated_url):
    url = make_url(migrated_url).set(username="alugai_site", password=os.environ["ALUGAI_SITE_DB_PASSWORD"])
    instance = create_engine(url)
    yield instance
    instance.dispose()


@pytest.mark.parametrize("view", sorted(PUBLIC_VIEWS))
def test_t1_10_site_role_reads_public_views(site_engine, view):
    with site_engine.connect() as connection:
        assert connection.execute(text(f"SELECT count(*) FROM {view}")).scalar_one() >= 0


def test_t1_10_site_role_grants_are_exactly_the_public_views(db, migrated_url):
    rows = db.execute(text(
        "SELECT table_name, privilege_type FROM information_schema.role_table_grants "
        "WHERE grantee = 'alugai_site' ORDER BY table_name")).all()
    assert [tuple(row) for row in rows] == [(view, "SELECT") for view in sorted(PUBLIC_VIEWS)]


def refused(site_engine, statement, reason):
    with site_engine.connect() as connection:
        # Positive control: without it, a role with no access at all would pass these refusals.
        connection.execute(text("SELECT count(*) FROM published_listings"))
        with pytest.raises(DBAPIError, match=reason):
            connection.execute(text(statement))


@pytest.mark.parametrize("relation", sorted(TABLES))
def test_t1_10_site_role_cannot_read_tables(site_engine, relation):
    refused(site_engine, f"SELECT 1 FROM {relation} LIMIT 1", "permission denied for table")


def test_t1_10_site_role_cannot_read_internal_view(site_engine):
    refused(site_engine, "SELECT 1 FROM listing_review_state LIMIT 1", "permission denied for view")


@pytest.mark.parametrize("statement,reason", [
    ("INSERT INTO sources (slug, display_name, domain, sitemap_urls) VALUES ('x', 'x', 'x', '{}')",
     "permission denied for table"),
    ("DELETE FROM listings", "permission denied for table"),
    ("UPDATE published_listings SET city = 'x'", "cannot update view|permission denied for view"),
    ("CREATE TABLE invasora (id INT)", "permission denied for schema"),
])
def test_t1_10_site_role_cannot_write(site_engine, statement, reason):
    refused(site_engine, statement, reason)
