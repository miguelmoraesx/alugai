"""Domain vocabulary: one StrEnum per database CHECK, plus tunable constants."""
from datetime import timedelta
from enum import StrEnum
import secrets

PUBLIC_ID_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"
PUBLIC_ID_LENGTH = 10

# Fixed by earlier decisions (PLANO.md, section 15).
EXPIRY_DAYS = 30
MAX_PHOTOS = 5
SKIP_IF_CONFIRMED_WITHIN = timedelta(days=7)
MISSING_CHECKS_TO_UNAVAILABLE = 2
RAW_HTML_TTL = timedelta(days=7)
RAW_SAMPLE_TTL = timedelta(days=30)
DELAY_SECONDS = 5.0
MIN_DELAY_SECONDS = 2.0
MAX_RESPONSE_BYTES = 8_000_000

# Initial values without real data; adjust after sampling and record in docs/decisoes.md.
MISSING_MIN_INTERVAL = timedelta(hours=20)
DEGRADED_STOP_MIN = 5
DEGRADED_STOP_RATIO = 0.30
NETWORK_STOP_CONSECUTIVE = 5
SITEMAP_SHRINK_ABORT_RATIO = 0.50
SITEMAP_SHRINK_ABORT_MIN_KNOWN = 10
REJECTED_URL_MEMO_DAYS = 30
SITEMAP_GUNZIP_MAX_BYTES = 50_000_000
RENT_PLAUSIBLE_MIN = 200
RENT_PLAUSIBLE_MAX = 50_000
COUNT_PLAUSIBLE_MAX = 100


class SourceStatus(StrEnum):
    CANDIDATE = "candidate"
    APPROVED = "approved"
    SUSPENDED = "suspended"
    REMOVED = "removed"


class CollectionState(StrEnum):
    OK = "ok"
    BLOCKED = "blocked"


class TermsResult(StrEnum):
    ALLOWED = "allowed"
    SILENT = "silent"
    PROHIBITED = "prohibited"
    NOT_FOUND = "not_found"


class Zone(StrEnum):
    NORTE = "region-norte"
    SUL = "region-sul"
    LESTE = "region-leste"
    OESTE = "region-oeste"
    CENTRO_SUL = "region-centro-sul"
    CENTRO_OESTE = "region-centro-oeste"


class RunMode(StrEnum):
    SAMPLE = "sample"
    COLLECT = "collect"
    REVIEW = "review"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    LAYOUT_STOP = "layout_stop"
    FAILED = "failed"
    DISCARDED = "discarded"


class PropertyType(StrEnum):
    APARTMENT = "apartment"
    HOUSE = "house"
    CONDO_HOUSE = "condo_house"
    KITNET = "kitnet"
    STUDIO = "studio"
    ROOM = "room"
    OTHER = "other"


class RentPeriod(StrEnum):
    MONTHLY = "monthly"
    ASSUMED_MONTHLY = "assumed_monthly"
    SHORT_TERM = "short_term"
    UNKNOWN = "unknown"


class FeeStatus(StrEnum):
    REPORTED = "reported"
    EXEMPT = "exempt"
    INCLUDED = "included"
    UNKNOWN = "unknown"
    ON_REQUEST = "on_request"
    NEEDS_REVIEW = "needs_review"


class ResolvedFeeStatus(StrEnum):
    REPORTED = "reported"
    EXEMPT = "exempt"
    INCLUDED = "included"
    UNKNOWN = "unknown"
    ON_REQUEST = "on_request"


class IptuPeriod(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
    UNKNOWN = "unknown"


class PetPolicy(StrEnum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"
    ON_REQUEST = "on_request"


class LocationPrecision(StrEnum):
    EXACT = "exact"
    APPROXIMATE = "approximate"
    NONE = "none"


class Availability(StrEnum):
    ACTIVE = "active"
    VERIFYING = "verifying"
    UNAVAILABLE = "unavailable"


class CaptureKind(StrEnum):
    SITEMAP = "sitemap"
    PAGE = "page"
    ROBOTS = "robots"


class CaptureResult(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NOT_FOUND = "not_found"
    BLOCKED = "blocked"
    FETCH_ERROR = "fetch_error"
    LAYOUT_ERROR = "layout_error"
    INTERNAL_ERROR = "internal_error"
    NOT_APPLICABLE = "not_applicable"


class ReviewDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REOPENED = "reopened"


class PhotoStatus(StrEnum):
    PENDING = "pending"
    STORED = "stored"
    FAILED = "failed"
    DELETED = "deleted"


class PhotoContentType(StrEnum):
    JPEG = "image/jpeg"
    PNG = "image/png"
    WEBP = "image/webp"


def new_public_id() -> str:
    return "".join(secrets.choice(PUBLIC_ID_ALPHABET) for _ in range(PUBLIC_ID_LENGTH))
