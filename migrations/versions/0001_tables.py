"""Tables of the unified data model (PLANO.md, section 3.1)."""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

TABLES = r"""
CREATE TABLE sources (
  id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  slug                 TEXT NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9_]+$'),
  display_name         TEXT NOT NULL,
  domain               TEXT NOT NULL UNIQUE,
  adapter              TEXT,                   -- nulo até o adaptador existir; collect exige
  sitemap_urls         TEXT[] NOT NULL,
  photo_hosts          TEXT[] NOT NULL DEFAULT '{}',
  photo_robots_waivers JSONB NOT NULL DEFAULT '[]', -- [{host, by, at, reason}]; só para robots ausente
  status               TEXT NOT NULL DEFAULT 'candidate'
    CONSTRAINT ck_sources_status CHECK (status IN ('candidate','approved','suspended','removed')),
  collection_state     TEXT NOT NULL DEFAULT 'ok'
    CONSTRAINT ck_sources_collection_state CHECK (collection_state IN ('ok','blocked')),
  collection_state_at  TIMESTAMPTZ,
  collection_state_reason TEXT,
  terms_result         TEXT
    CONSTRAINT ck_sources_terms_result CHECK (terms_result IN ('allowed','silent','prohibited','not_found')),
  terms_checked_at     TIMESTAMPTZ,
  terms_checked_by     TEXT,
  terms_url            TEXT,
  notice_sent_at       TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_sources_terms_complete CHECK (
    (terms_result IS NULL) = (terms_checked_at IS NULL)
    AND (terms_result IS NULL) = (terms_checked_by IS NULL)),
  CONSTRAINT ck_sources_blocked_has_reason CHECK (
    collection_state = 'ok' OR (collection_state_at IS NOT NULL AND collection_state_reason IS NOT NULL)),
  CONSTRAINT ck_sources_approved_needs_terms CHECK (
    status <> 'approved' OR (terms_checked_at IS NOT NULL AND terms_result <> 'prohibited'))
);

CREATE TABLE neighborhoods (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  slug          TEXT NOT NULL UNIQUE,
  name          TEXT NOT NULL UNIQUE,
  aliases       TEXT[] NOT NULL DEFAULT '{}',
  zone          TEXT NOT NULL
    CONSTRAINT ck_neighborhoods_zone CHECK (zone IN ('region-norte','region-sul','region-leste',
      'region-oeste','region-centro-sul','region-centro-oeste')),
  near_ufam     BOOLEAN NOT NULL DEFAULT false,
  near_uea      BOOLEAN NOT NULL DEFAULT false,
  near_pim      BOOLEAN NOT NULL DEFAULT false,
  source_note   TEXT NOT NULL
);

CREATE TABLE collection_runs (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  mode         TEXT NOT NULL CONSTRAINT ck_runs_mode CHECK (mode IN ('sample','collect','review')),
  source_id    BIGINT REFERENCES sources(id),  -- nulo em review
  started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ,
  status       TEXT NOT NULL DEFAULT 'running'
    CONSTRAINT ck_runs_status CHECK (status IN
      ('running','success','partial','blocked','layout_stop','failed','discarded')),
  counters     JSONB NOT NULL DEFAULT '{}',    -- só lidos no relatório; inclui aceite de mudança em massa
  reason       TEXT
);

CREATE TABLE listings (
  id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_id           TEXT NOT NULL UNIQUE
    CONSTRAINT ck_listings_public_id CHECK (public_id ~ '^[a-hjkmnp-z2-9]{10}$'),
  source_id           BIGINT NOT NULL REFERENCES sources(id),
  external_id         TEXT NOT NULL,
  source_url          TEXT NOT NULL CONSTRAINT ck_listings_url_https CHECK (source_url LIKE 'https://%'),
  advertiser_name     TEXT,
  creci               TEXT,
  source_title        TEXT NOT NULL,
  property_type       TEXT NOT NULL
    CONSTRAINT ck_listings_property_type CHECK (property_type IN
      ('apartment','house','condo_house','kitnet','studio','room','other')),
  bedrooms            SMALLINT CONSTRAINT ck_listings_bedrooms CHECK (bedrooms >= 0),
  bathrooms           SMALLINT CONSTRAINT ck_listings_bathrooms CHECK (bathrooms >= 0),
  parking_spaces      SMALLINT CONSTRAINT ck_listings_parking CHECK (parking_spaces >= 0),
  area_m2             NUMERIC(10,2) CONSTRAINT ck_listings_area CHECK (area_m2 > 0 AND area_m2 <> 'NaN'),
  rent_amount         NUMERIC(12,2) NOT NULL CONSTRAINT ck_listings_rent CHECK (rent_amount > 0 AND rent_amount <> 'NaN'),
  rent_period         TEXT NOT NULL
    CONSTRAINT ck_listings_rent_period CHECK (rent_period IN ('monthly','assumed_monthly','short_term','unknown')),
  condo_amount        NUMERIC(12,2) CONSTRAINT ck_listings_condo_amount CHECK (condo_amount >= 0 AND condo_amount <> 'NaN'),
  condo_status        TEXT NOT NULL
    CONSTRAINT ck_listings_condo_status CHECK (condo_status IN
      ('reported','exempt','included','unknown','on_request','needs_review')),
  iptu_amount         NUMERIC(12,2) CONSTRAINT ck_listings_iptu_amount CHECK (iptu_amount >= 0 AND iptu_amount <> 'NaN'),
  iptu_status         TEXT NOT NULL
    CONSTRAINT ck_listings_iptu_status CHECK (iptu_status IN
      ('reported','exempt','included','unknown','on_request','needs_review')),
  iptu_period         TEXT NOT NULL DEFAULT 'unknown'
    CONSTRAINT ck_listings_iptu_period CHECK (iptu_period IN ('monthly','annual','unknown')),
  pet_policy          TEXT NOT NULL DEFAULT 'unknown'
    CONSTRAINT ck_listings_pet CHECK (pet_policy IN ('yes','no','unknown','on_request')),
  city                TEXT NOT NULL,
  neighborhood_raw    TEXT NOT NULL,
  neighborhood_id     BIGINT REFERENCES neighborhoods(id),
  street              TEXT,
  latitude            NUMERIC(9,6) CONSTRAINT ck_listings_lat CHECK (latitude BETWEEN -90 AND 90),
  longitude           NUMERIC(9,6) CONSTRAINT ck_listings_lng CHECK (longitude BETWEEN -180 AND 180),
  location_precision  TEXT NOT NULL DEFAULT 'none'  -- com coordenada: approximate, salvo a fonte declarar exata
    CONSTRAINT ck_listings_precision CHECK (location_precision IN ('exact','approximate','none')),
  photo_hashes        TEXT[] NOT NULL DEFAULT '{}', -- conjunto ordenado que entrou no content_hash
  first_seen_at       TIMESTAMPTZ NOT NULL,
  last_seen_at        TIMESTAMPTZ NOT NULL,   -- só página baixada e validada renova
  last_checked_at     TIMESTAMPTZ NOT NULL,
  source_updated_at   TIMESTAMPTZ,            -- lastmod do sitemap
  expires_at          TIMESTAMPTZ NOT NULL,   -- last_seen_at + 30 dias, gravado no código (coluna gerada exige IMMUTABLE)
  availability_status TEXT NOT NULL DEFAULT 'active'
    CONSTRAINT ck_listings_availability CHECK (availability_status IN ('active','verifying','unavailable')),
  missing_count       SMALLINT NOT NULL DEFAULT 0,
  last_missing_at     TIMESTAMPTZ,
  last_error          TEXT,
  invalid_since       TIMESTAMPTZ,
  invalid_reason      TEXT,
  withdrawn_at        TIMESTAMPTZ,
  withdrawn_by        TEXT,
  withdrawn_reason    TEXT,
  content_hash        TEXT NOT NULL CONSTRAINT ck_listings_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  warnings            TEXT[] NOT NULL DEFAULT '{}',
  evidence            JSONB NOT NULL DEFAULT '{}',
  CONSTRAINT uq_listings_identity UNIQUE (source_id, external_id),
  CONSTRAINT ck_listings_expiry_after_seen CHECK (expires_at > last_seen_at),
  CONSTRAINT ck_listings_coords_pair CHECK ((latitude IS NULL) = (longitude IS NULL)),
  CONSTRAINT ck_listings_precision_coords CHECK ((location_precision = 'none') = (latitude IS NULL)),
  CONSTRAINT ck_listings_condo_consistent CHECK (
    (condo_status = 'reported' AND condo_amount IS NOT NULL)
    OR (condo_status IN ('exempt','included','unknown','on_request') AND condo_amount IS NULL)
    OR condo_status = 'needs_review'),
  CONSTRAINT ck_listings_iptu_consistent CHECK (
    (iptu_status = 'reported' AND iptu_amount IS NOT NULL)
    OR (iptu_status IN ('exempt','included','unknown','on_request') AND iptu_amount IS NULL)
    OR iptu_status = 'needs_review'),
  CONSTRAINT ck_listings_invalid_pair CHECK ((invalid_since IS NULL) = (invalid_reason IS NULL)),
  CONSTRAINT ck_listings_withdrawn_complete CHECK (
    (withdrawn_at IS NULL) = (withdrawn_by IS NULL) AND (withdrawn_at IS NULL) = (withdrawn_reason IS NULL))
);
CREATE INDEX ix_listings_neighborhood ON listings(neighborhood_id);

-- Só campos do hash, mesmos tipos de listings.
CREATE TABLE listing_versions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  listing_id BIGINT NOT NULL REFERENCES listings(id),
  capture_id BIGINT,                 -- FK adicionada após captures
  observed_at TIMESTAMPTZ NOT NULL,
  content_hash TEXT NOT NULL CONSTRAINT ck_versions_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  adapter_version TEXT NOT NULL,
  source_title TEXT NOT NULL,
  property_type TEXT NOT NULL CONSTRAINT ck_versions_property_type CHECK (property_type IN
    ('apartment','house','condo_house','kitnet','studio','room','other')),
  bedrooms SMALLINT, bathrooms SMALLINT, parking_spaces SMALLINT, area_m2 NUMERIC(10,2),
  rent_amount NUMERIC(12,2) NOT NULL,
  rent_period TEXT NOT NULL CONSTRAINT ck_versions_rent_period CHECK (rent_period IN
    ('monthly','assumed_monthly','short_term','unknown')),
  condo_amount NUMERIC(12,2),
  condo_status TEXT NOT NULL CONSTRAINT ck_versions_condo_status CHECK (condo_status IN
    ('reported','exempt','included','unknown','on_request','needs_review')),
  iptu_amount NUMERIC(12,2),
  iptu_status TEXT NOT NULL CONSTRAINT ck_versions_iptu_status CHECK (iptu_status IN
    ('reported','exempt','included','unknown','on_request','needs_review')),
  iptu_period TEXT NOT NULL CONSTRAINT ck_versions_iptu_period CHECK (iptu_period IN ('monthly','annual','unknown')),
  pet_policy TEXT NOT NULL CONSTRAINT ck_versions_pet CHECK (pet_policy IN ('yes','no','unknown','on_request')),
  neighborhood_raw TEXT NOT NULL, street TEXT, city TEXT NOT NULL,
  latitude NUMERIC(9,6), longitude NUMERIC(9,6),
  advertiser_name TEXT, creci TEXT,
  photo_hashes TEXT[] NOT NULL DEFAULT '{}'
);
CREATE INDEX ix_versions_listing ON listing_versions(listing_id, observed_at DESC);
CREATE INDEX ix_versions_hash ON listing_versions(listing_id, content_hash);

CREATE TABLE captures (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id BIGINT NOT NULL REFERENCES collection_runs(id),
  source_id BIGINT NOT NULL REFERENCES sources(id),
  listing_id BIGINT REFERENCES listings(id),
  kind TEXT NOT NULL CONSTRAINT ck_captures_kind CHECK (kind IN ('sitemap','page','robots')),
  url TEXT NOT NULL,
  final_url TEXT,
  fetched_at TIMESTAMPTZ NOT NULL,
  http_status SMALLINT,
  body_sha256 TEXT,
  source_lastmod TIMESTAMPTZ,
  adapter_version TEXT,
  result TEXT NOT NULL CONSTRAINT ck_captures_result CHECK (result IN
    ('accepted','rejected','not_found','blocked','fetch_error','layout_error','internal_error','not_applicable')),
  reason TEXT,
  raw_path TEXT CONSTRAINT ck_captures_raw_path CHECK (raw_path !~ '(^/|\.\.)'),
  raw_expires_at TIMESTAMPTZ,
  CONSTRAINT ck_captures_raw_pair CHECK ((raw_path IS NULL) = (raw_expires_at IS NULL))
);
CREATE INDEX ix_captures_url ON captures(source_id, url, fetched_at DESC);
CREATE INDEX ix_captures_listing ON captures(listing_id);
CREATE INDEX ix_captures_run ON captures(run_id);
ALTER TABLE listing_versions ADD CONSTRAINT fk_versions_capture
  FOREIGN KEY (capture_id) REFERENCES captures(id);

CREATE TABLE reviews (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  listing_id BIGINT NOT NULL REFERENCES listings(id),
  run_id BIGINT REFERENCES collection_runs(id),
  decision TEXT NOT NULL CONSTRAINT ck_reviews_decision CHECK (decision IN ('approved','rejected','reopened')),
  reason TEXT,
  reviewer TEXT NOT NULL CONSTRAINT ck_reviews_reviewer CHECK (length(trim(reviewer)) > 0),
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  content_hash TEXT NOT NULL CONSTRAINT ck_reviews_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  resolved_condo_status TEXT CONSTRAINT ck_reviews_condo CHECK (resolved_condo_status IN
    ('reported','exempt','included','unknown','on_request')),
  resolved_condo_amount NUMERIC(12,2),
  resolved_iptu_status TEXT CONSTRAINT ck_reviews_iptu CHECK (resolved_iptu_status IN
    ('reported','exempt','included','unknown','on_request')),
  resolved_iptu_amount NUMERIC(12,2),
  resolved_iptu_period TEXT CONSTRAINT ck_reviews_iptu_period CHECK (resolved_iptu_period IN ('monthly','annual','unknown')),
  CONSTRAINT ck_reviews_resolved_amounts CHECK (
    (resolved_condo_amount IS NULL OR (resolved_condo_amount >= 0 AND resolved_condo_amount <> 'NaN'))
    AND (resolved_iptu_amount IS NULL OR (resolved_iptu_amount >= 0 AND resolved_iptu_amount <> 'NaN'))),
  CONSTRAINT ck_reviews_reason_required CHECK (decision = 'approved' OR reason IS NOT NULL),
  CONSTRAINT ck_reviews_resolved_only_approved CHECK (decision = 'approved' OR
    (resolved_condo_status IS NULL AND resolved_iptu_status IS NULL)),
  CONSTRAINT ck_reviews_condo_pair CHECK (
    (resolved_condo_status IS NULL AND resolved_condo_amount IS NULL)
    OR (resolved_condo_status = 'reported' AND resolved_condo_amount IS NOT NULL)
    OR (resolved_condo_status IN ('exempt','included','unknown','on_request') AND resolved_condo_amount IS NULL)),
  CONSTRAINT ck_reviews_iptu_pair CHECK (
    (resolved_iptu_status IS NULL AND resolved_iptu_amount IS NULL)
    OR (resolved_iptu_status = 'reported' AND resolved_iptu_amount IS NOT NULL)
    OR (resolved_iptu_status IN ('exempt','included','unknown','on_request') AND resolved_iptu_amount IS NULL))
);
CREATE INDEX ix_reviews_latest ON reviews(listing_id, decided_at DESC, id DESC);

CREATE TABLE listing_photos (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  listing_id BIGINT NOT NULL REFERENCES listings(id),
  source_url TEXT NOT NULL,
  position SMALLINT CONSTRAINT ck_photos_position CHECK (position BETWEEN 1 AND 5), -- nulo: fora da seleção
  sha256 TEXT CONSTRAINT ck_photos_sha CHECK (sha256 ~ '^[0-9a-f]{64}$'),           -- mantido após apagar
  storage_path TEXT CONSTRAINT ck_photos_path CHECK (storage_path !~ '(^/|\.\.)'),
  content_type TEXT CONSTRAINT ck_photos_type CHECK (content_type IN ('image/jpeg','image/png','image/webp')),
  byte_size INTEGER,
  status TEXT NOT NULL DEFAULT 'pending'
    CONSTRAINT ck_photos_status CHECK (status IN ('pending','stored','failed','deleted')),
  fetched_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ,
  last_error TEXT,
  CONSTRAINT uq_photos_url UNIQUE (listing_id, source_url),
  CONSTRAINT ck_photos_stored_complete CHECK (status <> 'stored' OR
    (sha256 IS NOT NULL AND storage_path IS NOT NULL AND content_type IS NOT NULL)),
  CONSTRAINT ck_photos_deleted_no_path CHECK (status <> 'deleted' OR storage_path IS NULL)
);
CREATE UNIQUE INDEX uq_photos_position ON listing_photos(listing_id, position) WHERE position IS NOT NULL;
"""

# Reverse dependency order: listing_versions references captures, captures references listings.
DROP_ORDER = ("listing_photos", "reviews", "listing_versions", "captures", "listings",
              "collection_runs", "neighborhoods", "sources")


def _run(script):
    # Simple-query protocol: these scripts have several statements, `%` and `:`, which text() would reinterpret.
    op.get_bind().exec_driver_sql(script, execution_options={"no_parameters": True})


def upgrade():
    _run(TABLES)


def downgrade():
    for table in DROP_ORDER:
        op.execute(f"DROP TABLE {table}")
