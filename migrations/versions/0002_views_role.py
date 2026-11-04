"""Publication views and the read-only site role (PLANO.md, sections 3.2 and 3.3)."""
import os

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

VIEWS = r"""
-- Interna. Regra única de revisão e valores efetivos.
CREATE VIEW listing_review_state AS
SELECT l.id AS listing_id, r.id AS review_id, cur.approved_current,
  CASE WHEN r.id IS NULL OR r.decision = 'reopened' OR r.content_hash <> l.content_hash
       THEN 'pending' ELSE r.decision END AS review_status,
  CASE WHEN cur.approved_current AND r.resolved_condo_status IS NOT NULL
       THEN r.resolved_condo_status ELSE l.condo_status END AS condo_status,
  CASE WHEN cur.approved_current AND r.resolved_condo_status IS NOT NULL
       THEN r.resolved_condo_amount ELSE l.condo_amount END AS condo_amount,
  CASE WHEN cur.approved_current AND r.resolved_iptu_status IS NOT NULL
       THEN r.resolved_iptu_status ELSE l.iptu_status END AS iptu_status,
  CASE WHEN cur.approved_current AND r.resolved_iptu_status IS NOT NULL
       THEN r.resolved_iptu_amount ELSE l.iptu_amount END AS iptu_amount,
  CASE WHEN cur.approved_current AND r.resolved_iptu_status IS NOT NULL
       THEN COALESCE(r.resolved_iptu_period, 'unknown') ELSE l.iptu_period END AS iptu_period
FROM listings l
LEFT JOIN LATERAL (
  SELECT * FROM reviews x WHERE x.listing_id = l.id ORDER BY x.decided_at DESC, x.id DESC LIMIT 1
) r ON true
CROSS JOIN LATERAL (
  SELECT COALESCE(r.decision = 'approved' AND r.content_hash = l.content_hash, false) AS approved_current
) cur;

-- Contrato do site. Lista fechada: warnings, evidence e caminhos nunca entram.
CREATE VIEW published_listings AS
SELECT
  l.public_id, l.source_title, s.display_name AS source_name, l.source_url,
  l.advertiser_name, l.creci, l.property_type,
  l.bedrooms, l.bathrooms, l.parking_spaces, l.area_m2,
  l.rent_amount, l.rent_period,
  st.condo_amount, st.condo_status, st.iptu_amount, st.iptu_status, st.iptu_period,
  f.iptu_monthly,
  l.rent_amount + f.condo_monthly + f.iptu_monthly AS monthly_total, -- NULL propaga
  l.pet_policy, l.city, n.name AS neighborhood, l.street,
  l.latitude, l.longitude, l.last_seen_at,
  array_remove(ARRAY[n.zone,
    CASE WHEN n.near_ufam THEN 'ufam' END,
    CASE WHEN n.near_uea  THEN 'uea'  END,
    CASE WHEN n.near_pim  THEN 'pim'  END], NULL) AS zones,
  COALESCE((SELECT array_agg(p.position ORDER BY p.position) FROM listing_photos p
            WHERE p.listing_id = l.id AND p.status = 'stored' AND p.position IS NOT NULL
              AND p.sha256 = ANY(l.photo_hashes)),
           '{}') AS photo_positions
FROM listings l
JOIN sources s ON s.id = l.source_id
JOIN neighborhoods n ON n.id = l.neighborhood_id          -- bairro não reconhecido fica fora
JOIN listing_review_state st ON st.listing_id = l.id
CROSS JOIN LATERAL (SELECT
  CASE st.condo_status WHEN 'reported' THEN st.condo_amount
                       WHEN 'exempt' THEN 0 WHEN 'included' THEN 0 END AS condo_monthly,
  CASE WHEN st.iptu_status IN ('exempt','included') THEN 0
       WHEN st.iptu_status = 'reported' AND st.iptu_period = 'monthly' THEN st.iptu_amount
       WHEN st.iptu_status = 'reported' AND st.iptu_period = 'annual' THEN round(st.iptu_amount / 12, 2)
  END AS iptu_monthly) f
WHERE s.status = 'approved'                                   -- 1. fonte liberada
  AND st.review_status = 'approved'                           -- 2. versão atual aprovada
  AND l.availability_status IN ('active','verifying')         -- 3. disponível
  AND l.expires_at > now()                                    -- 4. não expirado
  AND l.withdrawn_at IS NULL                                  -- 5. não retirado
  AND l.invalid_since IS NULL                                 -- D13
  AND l.rent_period IN ('monthly','assumed_monthly')          -- defesas: falham fechado
  AND l.property_type IN ('apartment','house','condo_house','kitnet','studio','room')
  AND l.city = 'Manaus'
  AND st.condo_status <> 'needs_review'
  AND st.iptu_status <> 'needs_review';

CREATE VIEW published_listing_photos AS
SELECT pl.public_id, p.position, p.storage_path, p.content_type
FROM published_listings pl
JOIN listings l ON l.public_id = pl.public_id
JOIN listing_photos p ON p.listing_id = l.id
WHERE p.status = 'stored' AND p.position IS NOT NULL
  AND p.sha256 = ANY(l.photo_hashes);

-- Exceção do 01 §4. Só existe o que um dia foi aprovado.
CREATE VIEW listing_public_status AS
SELECT l.public_id,
  CASE WHEN pl.public_id IS NOT NULL THEN 'published' ELSE 'unavailable' END AS state
FROM listings l
LEFT JOIN published_listings pl ON pl.public_id = l.public_id
WHERE EXISTS (SELECT 1 FROM reviews r WHERE r.listing_id = l.id AND r.decision = 'approved');
"""

PUBLIC_VIEWS = ("published_listings", "published_listing_photos", "listing_public_status")
DROP_ORDER = ("listing_public_status", "published_listing_photos", "published_listings", "listing_review_state")


def _run(script):
    # Simple-query protocol: these scripts have several statements, `%` and `:`, which text() would reinterpret.
    op.get_bind().exec_driver_sql(script, execution_options={"no_parameters": True})


def _literal(value):
    return "'" + value.replace("'", "''") + "'"


def upgrade():
    _run(VIEWS)
    # The default password is local-only; the role is global to the cluster, so it may already exist.
    # Plain CREATE ROLE, outside the DO block: a `$$` in the password would end the block.
    if not op.get_bind().exec_driver_sql("SELECT 1 FROM pg_roles WHERE rolname = 'alugai_site'").first():
        password = _literal(os.environ.get("ALUGAI_SITE_DB_PASSWORD", "alugai_site_local"))
        _run(f"CREATE ROLE alugai_site LOGIN PASSWORD {password}")
    _run("""
DO $$
BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO alugai_site', current_database());
END $$;
GRANT USAGE ON SCHEMA public TO alugai_site;
""")
    for view in PUBLIC_VIEWS:
        op.execute(f"GRANT SELECT ON {view} TO alugai_site")


def downgrade():
    for view in PUBLIC_VIEWS:
        op.execute(f"REVOKE SELECT ON {view} FROM alugai_site")
    _run("""
DO $$
BEGIN
  EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM alugai_site', current_database());
END $$;
REVOKE USAGE ON SCHEMA public FROM alugai_site;
""")
    for view in DROP_ORDER:
        op.execute(f"DROP VIEW {view}")
