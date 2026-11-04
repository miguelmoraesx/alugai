"""Domain vocabulary: one StrEnum per database CHECK, plus tunable constants."""
from enum import StrEnum


class SourceStatus(StrEnum): pass
class CollectionState(StrEnum): pass
class TermsResult(StrEnum): pass
class Zone(StrEnum): pass
class RunMode(StrEnum): pass
class RunStatus(StrEnum): pass
class PropertyType(StrEnum): pass
class RentPeriod(StrEnum): pass
class FeeStatus(StrEnum): pass
class ResolvedFeeStatus(StrEnum): pass
class IptuPeriod(StrEnum): pass
class PetPolicy(StrEnum): pass
class LocationPrecision(StrEnum): pass
class Availability(StrEnum): pass
class CaptureKind(StrEnum): pass
class CaptureResult(StrEnum): pass
class ReviewDecision(StrEnum): pass
class PhotoStatus(StrEnum): pass
class PhotoContentType(StrEnum): pass


def new_public_id() -> str:
    raise NotImplementedError
