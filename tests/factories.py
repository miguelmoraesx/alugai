"""Raw-SQL builders, so these tests never depend on the code they verify."""
from itertools import count

from sqlalchemy import text

HASH_A = "a" * 64
HASH_B = "b" * 64
ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
_sequence = count(1)


def _public_id(number):
    digits = ""
    for _ in range(10):
        number, digit = divmod(number, len(ALPHABET))
        digits = ALPHABET[digit] + digits
    return digits


def insert(db, table, values):
    columns = ", ".join(values)
    binds = ", ".join(f":{name}" for name in values)
    return db.execute(text(f"INSERT INTO {table} ({columns}) VALUES ({binds}) RETURNING id"), values).scalar_one()


def source(db, **overrides):
    number = next(_sequence)
    values = {
        "slug": f"fonte_{number}", "display_name": f"Fonte {number}", "domain": f"fonte{number}.example",
        "sitemap_urls": [f"https://fonte{number}.example/sitemap.xml"], "status": "approved",
        "terms_result": "silent", "terms_checked_at": "2026-11-01T00:00:00Z", "terms_checked_by": "operador",
    }
    return insert(db, "sources", {**values, **overrides})


def neighborhood(db, **overrides):
    number = next(_sequence)
    values = {"slug": f"bairro-{number}", "name": f"Bairro {number}", "zone": "region-sul",
              "source_note": "teste"}
    return insert(db, "neighborhoods", {**values, **overrides})


def listing(db, source_id, neighborhood_id, **overrides):
    number = next(_sequence)
    values = {
        "public_id": _public_id(number), "source_id": source_id, "external_id": str(number),
        "source_url": f"https://fonte.example/imovel/{number}", "source_title": "Apartamento de teste",
        "property_type": "apartment", "rent_amount": "1000.00", "rent_period": "monthly",
        "condo_amount": "200.00", "condo_status": "reported", "iptu_amount": "50.00",
        "iptu_status": "reported", "iptu_period": "monthly", "city": "Manaus",
        "neighborhood_raw": "Bairro", "neighborhood_id": neighborhood_id,
        "first_seen_at": "2026-11-01T00:00:00Z", "last_seen_at": "2026-11-01T00:00:00Z",
        "last_checked_at": "2026-11-01T00:00:00Z", "expires_at": "2099-01-01T00:00:00Z",
        "content_hash": HASH_A,
    }
    return insert(db, "listings", {**values, **overrides})


def review(db, listing_id, decision="approved", content_hash=HASH_A, **overrides):
    values = {"listing_id": listing_id, "decision": decision, "content_hash": content_hash,
              "reviewer": "operador", "reason": None if decision == "approved" else "motivo"}
    return insert(db, "reviews", {**values, **overrides})


def photo(db, listing_id, **overrides):
    number = next(_sequence)
    values = {"listing_id": listing_id, "source_url": f"https://fonte.example/foto/{number}.jpg",
              "position": 1, "sha256": HASH_A, "storage_path": f"{number}.jpg",
              "content_type": "image/jpeg", "status": "stored"}
    return insert(db, "listing_photos", {**values, **overrides})


def published(db, source_overrides=None, neighborhood_overrides=None, **listing_overrides):
    """A listing that passes every publication rule; tests break one rule at a time."""
    listing_id = listing(db, source(db, **(source_overrides or {})),
                         neighborhood(db, **(neighborhood_overrides or {})), **listing_overrides)
    review(db, listing_id, content_hash=listing_overrides.get("content_hash", HASH_A))
    return listing_id


def update(db, table, row_id, **values):
    assignments = ", ".join(f"{name} = :{name}" for name in values)
    db.execute(text(f"UPDATE {table} SET {assignments} WHERE id = :row_id"), {**values, "row_id": row_id})
