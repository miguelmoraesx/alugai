from decimal import Decimal

import pytest
from sqlalchemy import text

from tests import factories as f

PUBLISHED_COLUMNS = {
    "public_id", "source_title", "source_name", "source_url", "advertiser_name", "creci", "property_type",
    "bedrooms", "bathrooms", "parking_spaces", "area_m2", "rent_amount", "rent_period",
    "condo_amount", "condo_status", "iptu_amount", "iptu_status", "iptu_period", "iptu_monthly",
    "monthly_total", "pet_policy", "city", "neighborhood", "street", "latitude", "longitude",
    "last_seen_at", "zones", "photo_positions",
}


def published_row(db, listing_id):
    return db.execute(text(
        "SELECT p.* FROM published_listings p JOIN listings l ON l.public_id = p.public_id WHERE l.id = :id"),
        {"id": listing_id}).mappings().first()


def is_published(db, listing_id):
    return published_row(db, listing_id) is not None


def review_state(db, listing_id):
    return db.execute(text("SELECT * FROM listing_review_state WHERE listing_id = :id"),
                      {"id": listing_id}).mappings().one()


def source_of(db, listing_id):
    return db.execute(text("SELECT source_id FROM listings WHERE id = :id"), {"id": listing_id}).scalar_one()


def test_t1_7_baseline_listing_is_published(db):
    assert is_published(db, f.published(db))


@pytest.mark.parametrize("property_type", ["apartment", "house", "condo_house", "kitnet", "studio", "room"])
def test_t1_7_every_residential_type_is_published(db, property_type):
    assert is_published(db, f.published(db, property_type=property_type))


def test_t1_7_listings_do_not_borrow_a_neighbors_review(db):
    approved = f.published(db)
    pending = f.listing(db, f.source(db), f.neighborhood(db))
    rejected = f.listing(db, f.source(db), f.neighborhood(db))
    f.review(db, rejected, decision="rejected")
    assert is_published(db, approved)
    assert not is_published(db, pending)
    assert not is_published(db, rejected)
    assert db.execute(text("SELECT count(*) FROM published_listings")).scalar_one() == 1


def test_t1_7_listings_do_not_borrow_a_neighbors_source(db):
    f.published(db)
    candidate = f.source(db, status="candidate")
    listing = f.listing(db, candidate, f.neighborhood(db))
    f.review(db, listing)
    assert not is_published(db, listing)
    assert db.execute(text("SELECT count(*) FROM published_listings")).scalar_one() == 1


def test_t1_7_each_row_has_its_own_data(db):
    first = f.published(db, rent_amount="1000")
    second = f.published(db, rent_amount="2000")
    assert published_row(db, first)["rent_amount"] == Decimal("1000.00")
    assert published_row(db, second)["rent_amount"] == Decimal("2000.00")
    assert db.execute(text("SELECT count(*) FROM published_listings")).scalar_one() == 2


@pytest.mark.parametrize("status", ["candidate", "suspended", "removed"])
def test_t1_7_source_status_hides(db, status):
    listing = f.published(db)
    f.update(db, "sources", source_of(db, listing), status=status)
    assert not is_published(db, listing)


def test_t1_7_blocked_source_stays_published(db):
    listing = f.published(db)
    f.update(db, "sources", source_of(db, listing), collection_state="blocked",
             collection_state_at="2026-11-01T00:00:00Z", collection_state_reason="429")
    assert is_published(db, listing)


def test_t1_7_verifying_stays_published(db):
    listing = f.published(db)
    f.update(db, "listings", listing, availability_status="verifying")
    assert is_published(db, listing)


def test_t1_7_without_review_is_hidden(db):
    assert not is_published(db, f.listing(db, f.source(db), f.neighborhood(db)))


def test_t1_7_changed_hash_is_hidden(db):
    listing = f.published(db)
    f.update(db, "listings", listing, content_hash=f.HASH_B)
    assert not is_published(db, listing)


@pytest.mark.parametrize("decision", ["rejected", "reopened"])
def test_t1_7_later_decision_hides(db, decision):
    listing = f.published(db)
    f.review(db, listing, decision=decision)
    assert not is_published(db, listing)


@pytest.mark.parametrize("values", [
    {"availability_status": "unavailable"},
    {"last_seen_at": "2020-01-01T00:00:00Z", "expires_at": "2020-01-31T00:00:00Z"},
    {"withdrawn_at": "2026-11-01T00:00:00Z", "withdrawn_by": "operador", "withdrawn_reason": "pedido"},
    {"invalid_since": "2026-11-01T00:00:00Z", "invalid_reason": "rent_on_request"},
    {"rent_period": "short_term"},
    {"rent_period": "unknown"},
    {"property_type": "other"},
    {"condo_status": "needs_review"},
    {"iptu_status": "needs_review"},
    {"neighborhood_id": None},
    {"city": "Iranduba"},
], ids=lambda values: next(iter(values)) + "=" + str(next(iter(values.values())))[:12])
def test_t1_7_listing_state_hides(db, values):
    listing = f.published(db)
    f.update(db, "listings", listing, **values)
    assert not is_published(db, listing)


@pytest.mark.parametrize("rent_period", ["monthly", "assumed_monthly"])
@pytest.mark.parametrize("condo,iptu,total,iptu_monthly", [
    ({"condo_status": "reported", "condo_amount": "200"}, {"iptu_status": "reported", "iptu_amount": "50", "iptu_period": "monthly"}, "1250.00", "50.00"),
    ({"condo_status": "exempt", "condo_amount": None}, {"iptu_status": "exempt", "iptu_amount": None, "iptu_period": "unknown"}, "1000.00", "0"),
    ({"condo_status": "included", "condo_amount": None}, {"iptu_status": "included", "iptu_amount": None, "iptu_period": "unknown"}, "1000.00", "0"),
    ({"condo_status": "exempt", "condo_amount": None}, {"iptu_status": "reported", "iptu_amount": "120", "iptu_period": "annual"}, "1010.00", "10.00"),
    ({"condo_status": "unknown", "condo_amount": None}, {"iptu_status": "reported", "iptu_amount": "50", "iptu_period": "monthly"}, None, "50.00"),
    ({"condo_status": "on_request", "condo_amount": None}, {"iptu_status": "reported", "iptu_amount": "50", "iptu_period": "monthly"}, None, "50.00"),
    ({"condo_status": "exempt", "condo_amount": None}, {"iptu_status": "unknown", "iptu_amount": None, "iptu_period": "unknown"}, None, None),
    ({"condo_status": "exempt", "condo_amount": None}, {"iptu_status": "on_request", "iptu_amount": None, "iptu_period": "unknown"}, None, None),
    ({"condo_status": "exempt", "condo_amount": None}, {"iptu_status": "reported", "iptu_amount": "50", "iptu_period": "unknown"}, None, None),
])
def test_t1_8_monthly_total(db, rent_period, condo, iptu, total, iptu_monthly):
    row = published_row(db, f.published(db, rent_period=rent_period, **condo, **iptu))
    assert row["monthly_total"] == (Decimal(total) if total else None)
    assert row["iptu_monthly"] == (Decimal(iptu_monthly) if iptu_monthly else None)


@pytest.mark.parametrize("annual,monthly,total", [("1000", "83.33", "1283.33"), ("1100", "91.67", "1291.67")])
def test_t1_13_annual_iptu_rounds_to_cents(db, annual, monthly, total):
    row = published_row(db, f.published(db, iptu_amount=annual, iptu_period="annual"))
    assert row["iptu_monthly"] == Decimal(monthly)
    assert row["monthly_total"] == Decimal(total)


def test_t1_9_published_columns_are_a_closed_list(db):
    row = published_row(db, f.published(db))
    assert set(row.keys()) == PUBLISHED_COLUMNS
    for name in ("warnings", "evidence", "storage_path", "last_error", "source_id", "content_hash"):
        assert name not in row


def test_t1_9_columns_carry_the_right_data(db):
    listing = f.published(
        db, source_overrides={"display_name": "Imobiliária Exemplo"},
        neighborhood_overrides={"name": "Flores Oficial", "zone": "region-norte", "near_ufam": True,
                                "near_uea": True, "near_pim": True},
        source_url="https://fonte.example/imovel/9", advertiser_name="Anunciante", creci="CRECI 1",
        source_title="Título", property_type="kitnet", bedrooms=1, bathrooms=2, parking_spaces=3, area_m2="40.5",
        rent_amount="1500", rent_period="assumed_monthly", pet_policy="yes", neighborhood_raw="Flores (bruto)",
        street="Rua Um", latitude="-3.100000", longitude="-60.200000", location_precision="approximate",
        last_seen_at="2026-11-02T00:00:00Z", last_checked_at="2026-11-03T00:00:00Z")
    row = published_row(db, listing)
    expected = {
        "source_name": "Imobiliária Exemplo", "source_url": "https://fonte.example/imovel/9",
        "advertiser_name": "Anunciante", "creci": "CRECI 1", "source_title": "Título", "property_type": "kitnet",
        "bedrooms": 1, "bathrooms": 2, "parking_spaces": 3, "area_m2": Decimal("40.50"),
        "rent_amount": Decimal("1500.00"), "rent_period": "assumed_monthly", "pet_policy": "yes",
        "city": "Manaus", "neighborhood": "Flores Oficial", "street": "Rua Um",
        "latitude": Decimal("-3.100000"), "longitude": Decimal("-60.200000"),
        "zones": ["region-norte", "ufam", "uea", "pim"],
    }
    assert {name: row[name] for name in expected} == expected
    assert row["last_seen_at"].isoformat().startswith("2026-11-02")


def test_t1_9_other_public_views_are_closed_lists(db):
    columns = lambda view: set(db.execute(text(f"SELECT * FROM {view} LIMIT 0")).keys())
    assert columns("published_listing_photos") == {"public_id", "position", "storage_path", "content_type"}
    assert columns("listing_public_status") == {"public_id", "state"}


def public_state(db, listing_id):
    return db.execute(text(
        "SELECT s.state FROM listing_public_status s JOIN listings l ON l.public_id = s.public_id "
        "WHERE l.id = :id"), {"id": listing_id}).scalar_one_or_none()


def test_t1_11_public_status(db):
    listing = f.published(db)
    assert public_state(db, listing) == "published"
    f.update(db, "listings", listing, withdrawn_at="2026-11-01T00:00:00Z", withdrawn_by="o", withdrawn_reason="p")
    assert public_state(db, listing) == "unavailable"


def test_t1_11_approved_then_rejected_is_unavailable(db):
    listing = f.published(db)
    f.review(db, listing, decision="rejected")
    assert public_state(db, listing) == "unavailable"


def test_t1_11_each_listing_has_its_own_status(db):
    published = f.published(db)
    withdrawn = f.published(db)
    never = f.listing(db, f.source(db), f.neighborhood(db))
    f.update(db, "listings", withdrawn, withdrawn_at="2026-11-01T00:00:00Z", withdrawn_by="o", withdrawn_reason="p")
    assert public_state(db, published) == "published"
    assert public_state(db, withdrawn) == "unavailable"
    assert public_state(db, never) is None
    assert db.execute(text("SELECT count(*) FROM listing_public_status")).scalar_one() == 2


def test_t1_11_never_approved_and_unknown_have_no_row(db):
    never = f.listing(db, f.source(db), f.neighborhood(db))
    assert public_state(db, never) is None
    f.review(db, never, decision="rejected")
    assert public_state(db, never) is None
    assert db.execute(text("SELECT count(*) FROM listing_public_status WHERE public_id = 'naoexiste2'")).scalar_one() == 0


def photos_of(db, listing_id):
    return db.execute(text(
        "SELECT p.position FROM published_listing_photos p JOIN listings l ON l.public_id = p.public_id "
        "WHERE l.id = :id ORDER BY p.position"), {"id": listing_id}).scalars().all()


def test_t1_12_only_published_stored_positioned_photos(db):
    sha = {n: str(n) * 64 for n in range(1, 6)}
    listing = f.published(db, photo_hashes=list(sha.values()))
    f.photo(db, listing, position=3, sha256=sha[3])
    f.photo(db, listing, position=1, sha256=sha[1])
    f.photo(db, listing, position=None, sha256=sha[2])
    f.photo(db, listing, position=2, sha256=sha[4], status="pending", storage_path=None)
    f.photo(db, listing, position=4, sha256=sha[5], status="failed", storage_path=None)
    assert photos_of(db, listing) == [1, 3]
    assert published_row(db, listing)["photo_positions"] == [1, 3]
    f.update(db, "listings", listing, withdrawn_at="2026-11-01T00:00:00Z", withdrawn_by="o", withdrawn_reason="p")
    assert photos_of(db, listing) == []


def test_t1_12_listings_do_not_borrow_a_neighbors_photos(db):
    # Same sha256 in both: only the listing column can tell the photos apart.
    sha = "1" * 64
    first = f.published(db, photo_hashes=[sha])
    second = f.published(db, photo_hashes=[sha])
    without = f.published(db, photo_hashes=[sha])
    f.photo(db, first, position=1, sha256=sha)
    f.photo(db, second, position=2, sha256=sha)
    assert photos_of(db, first) == [1]
    assert photos_of(db, second) == [2]
    assert photos_of(db, without) == []
    assert published_row(db, first)["photo_positions"] == [1]
    assert published_row(db, second)["photo_positions"] == [2]
    assert published_row(db, without)["photo_positions"] == []
    assert db.execute(text("SELECT count(*) FROM published_listing_photos")).scalar_one() == 2


def test_t1_12_no_photos_is_an_empty_list(db):
    assert published_row(db, f.published(db))["photo_positions"] == []


def test_t1_18_stored_photo_outside_approved_set_is_not_served(db):
    approved = "1" * 64
    listing = f.published(db, photo_hashes=[approved])
    f.photo(db, listing, position=1, sha256=approved)
    f.photo(db, listing, position=2, sha256="2" * 64)
    assert photos_of(db, listing) == [1]
    assert published_row(db, listing)["photo_positions"] == [1]


def test_t1_14_without_review_is_pending(db):
    state = review_state(db, f.listing(db, f.source(db), f.neighborhood(db)))
    assert state["review_status"] == "pending"
    assert state["approved_current"] is False


def test_t1_14_reopened_is_pending(db):
    listing = f.published(db)
    assert review_state(db, listing)["approved_current"] is True
    f.review(db, listing, decision="reopened")
    state = review_state(db, listing)
    assert state["review_status"] == "pending"
    assert state["approved_current"] is False


@pytest.mark.parametrize("older,newer,expected", [
    ("approved", "rejected", "rejected"), ("rejected", "approved", "approved"),
])
def test_t1_14_latest_date_wins_regardless_of_insertion_order(db, older, newer, expected):
    listing = f.listing(db, f.source(db), f.neighborhood(db))
    f.review(db, listing, decision=newer, decided_at="2026-11-02T00:00:00Z")
    f.review(db, listing, decision=older, decided_at="2026-11-01T00:00:00Z")
    assert review_state(db, listing)["review_status"] == expected


def test_t1_14_rejected_then_new_hash_is_pending(db):
    listing = f.listing(db, f.source(db), f.neighborhood(db))
    f.review(db, listing, decision="rejected")
    assert review_state(db, listing)["review_status"] == "rejected"
    f.update(db, "listings", listing, content_hash=f.HASH_B)
    assert review_state(db, listing)["review_status"] == "pending"


def test_t1_14_approved_a_b_a_is_approved_again(db):
    listing = f.published(db)
    f.update(db, "listings", listing, content_hash=f.HASH_B)
    assert review_state(db, listing)["review_status"] == "pending"
    f.update(db, "listings", listing, content_hash=f.HASH_A)
    assert review_state(db, listing)["review_status"] == "approved"
    assert is_published(db, listing)


def test_t1_14_approved_a_rejected_b_back_to_a_is_pending(db):
    listing = f.published(db)
    f.update(db, "listings", listing, content_hash=f.HASH_B)
    f.review(db, listing, decision="rejected", content_hash=f.HASH_B)
    f.update(db, "listings", listing, content_hash=f.HASH_A)
    assert review_state(db, listing)["review_status"] == "pending"
    assert not is_published(db, listing)


@pytest.mark.parametrize("first,second,expected", [
    ("approved", "rejected", "rejected"), ("rejected", "approved", "approved"),
])
def test_t1_14_ties_are_broken_by_id(db, first, second, expected):
    listing = f.listing(db, f.source(db), f.neighborhood(db))
    moment = "2026-11-01T12:00:00Z"
    f.review(db, listing, decision=first, decided_at=moment)
    f.review(db, listing, decision=second, decided_at=moment)
    # Without an index the planner has no incidental order to fall back on.
    db.execute(text("SET LOCAL enable_indexscan = off"))
    db.execute(text("SET LOCAL enable_bitmapscan = off"))
    db.execute(text("SET LOCAL enable_indexonlyscan = off"))
    assert review_state(db, listing)["review_status"] == expected


def test_t1_15_correction_applies_with_same_hash_and_falls_with_new_hash(db):
    listing = f.listing(db, f.source(db), f.neighborhood(db), condo_status="needs_review", condo_amount="1",
                        iptu_status="needs_review", iptu_amount="1", iptu_period="unknown")
    f.review(db, listing, resolved_condo_status="exempt", resolved_iptu_status="reported",
             resolved_iptu_amount="1200", resolved_iptu_period="annual")
    state = review_state(db, listing)
    assert (state["condo_status"], state["condo_amount"]) == ("exempt", None)
    assert (state["iptu_status"], state["iptu_amount"], state["iptu_period"]) == ("reported", Decimal("1200.00"), "annual")
    row = published_row(db, listing)
    assert (row["condo_status"], row["condo_amount"]) == ("exempt", None)
    assert (row["iptu_status"], row["iptu_amount"], row["iptu_period"]) == ("reported", Decimal("1200.00"), "annual")
    assert row["iptu_monthly"] == Decimal("100.00")
    assert row["monthly_total"] == Decimal("1100.00")
    f.update(db, "listings", listing, content_hash=f.HASH_B)
    state = review_state(db, listing)
    assert state["review_status"] == "pending"
    assert (state["condo_status"], state["condo_amount"]) == ("needs_review", Decimal("1.00"))
    assert (state["iptu_status"], state["iptu_amount"], state["iptu_period"]) == ("needs_review", Decimal("1.00"), "unknown")
    assert published_row(db, listing) is None


def test_t1_15_corrected_condo_value_reaches_the_view(db):
    listing = f.listing(db, f.source(db), f.neighborhood(db), condo_status="needs_review", condo_amount="1")
    f.review(db, listing, resolved_condo_status="reported", resolved_condo_amount="300")
    row = published_row(db, listing)
    assert (row["condo_status"], row["condo_amount"]) == ("reported", Decimal("300.00"))
    assert row["monthly_total"] == Decimal("1350.00")


def test_t1_15_correction_without_period_is_unknown(db):
    listing = f.listing(db, f.source(db), f.neighborhood(db), iptu_status="needs_review", iptu_amount="1", iptu_period="monthly")
    f.review(db, listing, resolved_iptu_status="reported", resolved_iptu_amount="50")
    assert review_state(db, listing)["iptu_period"] == "unknown"
    assert published_row(db, listing)["monthly_total"] is None


def test_t1_16_neighborhood_id_does_not_change_review(db):
    listing = f.published(db)
    f.update(db, "listings", listing, neighborhood_id=f.neighborhood(db))
    assert review_state(db, listing)["review_status"] == "approved"
    assert is_published(db, listing)


def test_zones_come_from_the_neighborhood(db):
    row = published_row(db, f.published(db, neighborhood_overrides={"zone": "region-leste", "near_ufam": True, "near_pim": True}))
    assert row["zones"] == ["region-leste", "ufam", "pim"]
