"""T1.3: each StrEnum holds exactly the values of its database CHECK."""
import re

import pytest
from sqlalchemy import text

from alugai import domain

CONTRACT = {
    "ck_sources_status": domain.SourceStatus,
    "ck_sources_collection_state": domain.CollectionState,
    "ck_sources_terms_result": domain.TermsResult,
    "ck_neighborhoods_zone": domain.Zone,
    "ck_runs_mode": domain.RunMode,
    "ck_runs_status": domain.RunStatus,
    "ck_listings_property_type": domain.PropertyType,
    "ck_listings_rent_period": domain.RentPeriod,
    "ck_listings_condo_status": domain.FeeStatus,
    "ck_listings_iptu_status": domain.FeeStatus,
    "ck_listings_iptu_period": domain.IptuPeriod,
    "ck_listings_pet": domain.PetPolicy,
    "ck_listings_precision": domain.LocationPrecision,
    "ck_listings_availability": domain.Availability,
    "ck_versions_property_type": domain.PropertyType,
    "ck_versions_rent_period": domain.RentPeriod,
    "ck_versions_condo_status": domain.FeeStatus,
    "ck_versions_iptu_status": domain.FeeStatus,
    "ck_versions_iptu_period": domain.IptuPeriod,
    "ck_versions_pet": domain.PetPolicy,
    "ck_captures_kind": domain.CaptureKind,
    "ck_captures_result": domain.CaptureResult,
    "ck_reviews_decision": domain.ReviewDecision,
    "ck_reviews_condo": domain.ResolvedFeeStatus,
    "ck_reviews_iptu": domain.ResolvedFeeStatus,
    "ck_reviews_iptu_period": domain.IptuPeriod,
    "ck_photos_status": domain.PhotoStatus,
    "ck_photos_type": domain.PhotoContentType,
}


@pytest.mark.parametrize("constraint,enum", CONTRACT.items())
def test_t1_3_enum_matches_check(db, constraint, enum):
    definition = db.execute(text(
        "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = :name"),
        {"name": constraint}).scalar_one()
    allowed = set(re.findall(r"'([^']+)'::text", definition))
    assert allowed
    assert {member.value for member in enum} == allowed


def test_t1_3_resolved_status_excludes_needs_review():
    assert "needs_review" not in {member.value for member in domain.ResolvedFeeStatus}
    assert {member.value for member in domain.ResolvedFeeStatus} | {"needs_review"} == {
        member.value for member in domain.FeeStatus}


def test_t1_17_new_public_id_format_and_uniqueness():
    identifiers = {domain.new_public_id() for _ in range(1000)}
    assert len(identifiers) == 1000
    assert all(re.fullmatch(r"[a-hjkmnp-z2-9]{10}", value) for value in identifiers)
