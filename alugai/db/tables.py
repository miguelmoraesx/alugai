"""SQLAlchemy Core mirror of the migrations. `alembic check` keeps both in sync.

CHECK constraints live only in the migrations: autogenerate cannot compare them.
"""
from sqlalchemy import (
    BigInteger, Boolean, Column, ForeignKey, Identity, Index, Integer, MetaData, Numeric, SmallInteger,
    Table, Text, TIMESTAMP, UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

metadata = MetaData()
TimestampTz = TIMESTAMP(timezone=True)
Money = Numeric(12, 2)
TextArray = ARRAY(Text)


def _id():
    return Column("id", BigInteger, Identity(always=True), primary_key=True)


sources = Table(
    "sources", metadata, _id(),
    Column("slug", Text, nullable=False, unique=True),
    Column("display_name", Text, nullable=False),
    Column("domain", Text, nullable=False, unique=True),
    Column("adapter", Text),
    Column("sitemap_urls", TextArray, nullable=False),
    Column("photo_hosts", TextArray, nullable=False, server_default=text("'{}'")),
    Column("photo_robots_waivers", JSONB, nullable=False, server_default=text("'[]'")),
    Column("status", Text, nullable=False, server_default=text("'candidate'")),
    Column("collection_state", Text, nullable=False, server_default=text("'ok'")),
    Column("collection_state_at", TimestampTz),
    Column("collection_state_reason", Text),
    Column("terms_result", Text),
    Column("terms_checked_at", TimestampTz),
    Column("terms_checked_by", Text),
    Column("terms_url", Text),
    Column("notice_sent_at", TimestampTz),
    Column("created_at", TimestampTz, nullable=False, server_default=text("now()")),
)

neighborhoods = Table(
    "neighborhoods", metadata, _id(),
    Column("slug", Text, nullable=False, unique=True),
    Column("name", Text, nullable=False, unique=True),
    Column("aliases", TextArray, nullable=False, server_default=text("'{}'")),
    Column("zone", Text, nullable=False),
    Column("near_ufam", Boolean, nullable=False, server_default=text("false")),
    Column("near_uea", Boolean, nullable=False, server_default=text("false")),
    Column("near_pim", Boolean, nullable=False, server_default=text("false")),
    Column("source_note", Text, nullable=False),
)

collection_runs = Table(
    "collection_runs", metadata, _id(),
    Column("mode", Text, nullable=False),
    Column("source_id", BigInteger, ForeignKey("sources.id")),
    Column("started_at", TimestampTz, nullable=False, server_default=text("now()")),
    Column("finished_at", TimestampTz),
    Column("status", Text, nullable=False, server_default=text("'running'")),
    Column("counters", JSONB, nullable=False, server_default=text("'{}'")),
    Column("reason", Text),
)

listings = Table(
    "listings", metadata, _id(),
    Column("public_id", Text, nullable=False, unique=True),
    Column("source_id", BigInteger, ForeignKey("sources.id"), nullable=False),
    Column("external_id", Text, nullable=False),
    Column("source_url", Text, nullable=False),
    Column("advertiser_name", Text),
    Column("creci", Text),
    Column("source_title", Text, nullable=False),
    Column("property_type", Text, nullable=False),
    Column("bedrooms", SmallInteger),
    Column("bathrooms", SmallInteger),
    Column("parking_spaces", SmallInteger),
    Column("area_m2", Numeric(10, 2)),
    Column("rent_amount", Money, nullable=False),
    Column("rent_period", Text, nullable=False),
    Column("condo_amount", Money),
    Column("condo_status", Text, nullable=False),
    Column("iptu_amount", Money),
    Column("iptu_status", Text, nullable=False),
    Column("iptu_period", Text, nullable=False, server_default=text("'unknown'")),
    Column("pet_policy", Text, nullable=False, server_default=text("'unknown'")),
    Column("city", Text, nullable=False),
    Column("neighborhood_raw", Text, nullable=False),
    Column("neighborhood_id", BigInteger, ForeignKey("neighborhoods.id")),
    Column("street", Text),
    Column("latitude", Numeric(9, 6)),
    Column("longitude", Numeric(9, 6)),
    Column("location_precision", Text, nullable=False, server_default=text("'none'")),
    Column("photo_hashes", TextArray, nullable=False, server_default=text("'{}'")),
    Column("first_seen_at", TimestampTz, nullable=False),
    Column("last_seen_at", TimestampTz, nullable=False),
    Column("last_checked_at", TimestampTz, nullable=False),
    Column("source_updated_at", TimestampTz),
    Column("expires_at", TimestampTz, nullable=False),
    Column("availability_status", Text, nullable=False, server_default=text("'active'")),
    Column("missing_count", SmallInteger, nullable=False, server_default=text("0")),
    Column("last_missing_at", TimestampTz),
    Column("last_error", Text),
    Column("invalid_since", TimestampTz),
    Column("invalid_reason", Text),
    Column("withdrawn_at", TimestampTz),
    Column("withdrawn_by", Text),
    Column("withdrawn_reason", Text),
    Column("content_hash", Text, nullable=False),
    Column("warnings", TextArray, nullable=False, server_default=text("'{}'")),
    Column("evidence", JSONB, nullable=False, server_default=text("'{}'")),
    UniqueConstraint("source_id", "external_id", name="uq_listings_identity"),
    Index("ix_listings_neighborhood", "neighborhood_id"),
)

listing_versions = Table(
    "listing_versions", metadata, _id(),
    Column("listing_id", BigInteger, ForeignKey("listings.id"), nullable=False),
    Column("capture_id", BigInteger, ForeignKey("captures.id", name="fk_versions_capture")),
    Column("observed_at", TimestampTz, nullable=False),
    Column("content_hash", Text, nullable=False),
    Column("adapter_version", Text, nullable=False),
    Column("source_title", Text, nullable=False),
    Column("property_type", Text, nullable=False),
    Column("bedrooms", SmallInteger),
    Column("bathrooms", SmallInteger),
    Column("parking_spaces", SmallInteger),
    Column("area_m2", Numeric(10, 2)),
    Column("rent_amount", Money, nullable=False),
    Column("rent_period", Text, nullable=False),
    Column("condo_amount", Money),
    Column("condo_status", Text, nullable=False),
    Column("iptu_amount", Money),
    Column("iptu_status", Text, nullable=False),
    Column("iptu_period", Text, nullable=False),
    Column("pet_policy", Text, nullable=False),
    Column("neighborhood_raw", Text, nullable=False),
    Column("street", Text),
    Column("city", Text, nullable=False),
    Column("latitude", Numeric(9, 6)),
    Column("longitude", Numeric(9, 6)),
    Column("advertiser_name", Text),
    Column("creci", Text),
    Column("photo_hashes", TextArray, nullable=False, server_default=text("'{}'")),
    Index("ix_versions_listing", "listing_id", text("observed_at DESC")),
    Index("ix_versions_hash", "listing_id", "content_hash"),
)

captures = Table(
    "captures", metadata, _id(),
    Column("run_id", BigInteger, ForeignKey("collection_runs.id"), nullable=False),
    Column("source_id", BigInteger, ForeignKey("sources.id"), nullable=False),
    Column("listing_id", BigInteger, ForeignKey("listings.id")),
    Column("kind", Text, nullable=False),
    Column("url", Text, nullable=False),
    Column("final_url", Text),
    Column("fetched_at", TimestampTz, nullable=False),
    Column("http_status", SmallInteger),
    Column("body_sha256", Text),
    Column("source_lastmod", TimestampTz),
    Column("adapter_version", Text),
    Column("result", Text, nullable=False),
    Column("reason", Text),
    Column("raw_path", Text),
    Column("raw_expires_at", TimestampTz),
    Index("ix_captures_url", "source_id", "url", text("fetched_at DESC")),
    Index("ix_captures_listing", "listing_id"),
    Index("ix_captures_run", "run_id"),
)

reviews = Table(
    "reviews", metadata, _id(),
    Column("listing_id", BigInteger, ForeignKey("listings.id"), nullable=False),
    Column("run_id", BigInteger, ForeignKey("collection_runs.id")),
    Column("decision", Text, nullable=False),
    Column("reason", Text),
    Column("reviewer", Text, nullable=False),
    Column("decided_at", TimestampTz, nullable=False, server_default=text("now()")),
    Column("content_hash", Text, nullable=False),
    Column("resolved_condo_status", Text),
    Column("resolved_condo_amount", Money),
    Column("resolved_iptu_status", Text),
    Column("resolved_iptu_amount", Money),
    Column("resolved_iptu_period", Text),
    Index("ix_reviews_latest", "listing_id", text("decided_at DESC"), text("id DESC")),
)

listing_photos = Table(
    "listing_photos", metadata, _id(),
    Column("listing_id", BigInteger, ForeignKey("listings.id"), nullable=False),
    Column("source_url", Text, nullable=False),
    Column("position", SmallInteger),
    Column("sha256", Text),
    Column("storage_path", Text),
    Column("content_type", Text),
    Column("byte_size", Integer),
    Column("status", Text, nullable=False, server_default=text("'pending'")),
    Column("fetched_at", TimestampTz),
    Column("deleted_at", TimestampTz),
    Column("last_error", Text),
    UniqueConstraint("listing_id", "source_url", name="uq_photos_url"),
    Index("uq_photos_position", "listing_id", "position", unique=True,
          postgresql_where=text("position IS NOT NULL")),
)
