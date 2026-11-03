"""Transactional persistence, compatible with PostgreSQL and local SQLite."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import uuid

from sqlalchemy import (create_engine, MetaData, Table, Column, String, Integer, Text,
                        JSON, select, insert, update, and_, or_)

metadata = MetaData()
listings = Table("collector_listings", metadata,
    Column("source", String(32), primary_key=True),
    Column("external_id", String(64), primary_key=True),
    Column("url", Text, nullable=False),
    Column("data", JSON, nullable=False),
    Column("content_hash", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("first_seen_at", String(40), nullable=False),
    Column("last_seen_at", String(40), nullable=False),
    Column("last_checked_at", String(40), nullable=False),
    Column("last_detail_checked_at", String(40)),
    Column("missing_count", Integer, nullable=False, default=0),
    Column("last_error", Text))
history = Table("collector_price_history", metadata,
    Column("id", String(36), primary_key=True),
    Column("source", String(32), nullable=False),
    Column("external_id", String(64), nullable=False),
    Column("observed_at", String(40), nullable=False),
    Column("rent_price", String(32), nullable=False),
    Column("condo_fee", String(32)))
runs = Table("collector_runs", metadata,
    Column("id", String(36), primary_key=True),
    Column("mode", String(32), nullable=False),
    Column("started_at", String(40), nullable=False),
    Column("finished_at", String(40)),
    Column("status", String(32), nullable=False),
    Column("stats", JSON),
    Column("error", Text))



review_items = Table("collector_review_items", metadata,
    Column("source", String(32), primary_key=True),
    Column("external_id", String(64), primary_key=True),
    Column("data", JSON, nullable=False),
    Column("first_imported_at", String(40), nullable=False),
    Column("last_imported_at", String(40), nullable=False))


def now():
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, database_url):
        if database_url.startswith("sqlite:///data/"):
            Path("data").mkdir(exist_ok=True)
        self.engine = create_engine(database_url)
        metadata.create_all(self.engine)

    def close(self):
        self.engine.dispose()

    def start_run(self, mode):
        run_id = str(uuid.uuid4())
        with self.engine.begin() as db:
            db.execute(insert(runs).values(id=run_id, mode=mode, started_at=now(), status="running"))
        return run_id

    def finish_run(self, run_id, status, stats, error=None):
        with self.engine.begin() as db:
            db.execute(update(runs).where(runs.c.id == run_id).values(
                finished_at=now(), status=status, stats=stats, error=error))

    def upsert(self, listing, source="olx", detail=False):
        stamp = now()
        key = and_(listings.c.source == source, listings.c.external_id == listing.external_id)
        with self.engine.begin() as db:
            old = db.execute(select(listings).where(key)).mappings().first()
            data = listing.data()
            if old and not detail:
                # Search cards omit detail fields. Do not erase known values.
                data = {k: old["data"].get(k) if v is None else v for k, v in data.items()}
            fingerprint = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
            values = dict(url=listing.url, data=data, content_hash=fingerprint, status="active",
                          last_seen_at=stamp, last_checked_at=stamp, missing_count=0, last_error=None)
            if detail:
                values["last_detail_checked_at"] = stamp
            if old:
                db.execute(update(listings).where(key).values(**values))
            else:
                db.execute(insert(listings).values(source=source, external_id=listing.external_id,
                                                   first_seen_at=stamp, **values))
            if not old or any(old["data"].get(k) != data.get(k) for k in ("rent_price", "condo_fee")):
                db.execute(insert(history).values(id=str(uuid.uuid4()), source=source,
                    external_id=listing.external_id, observed_at=stamp,
                    rent_price=data["rent_price"], condo_fee=data["condo_fee"]))
            return "new" if not old else "updated" if old["content_hash"] != fingerprint else "unchanged"

    def mark_error(self, source, external_id, error, missing=False):
        key = and_(listings.c.source == source, listings.c.external_id == external_id)
        with self.engine.begin() as db:
            old = db.execute(select(listings).where(key)).mappings().one()
            count = old["missing_count"] + 1 if missing else 0
            # Even 404/410 must occur on two separate refresh runs.
            stamp = now()
            db.execute(update(listings).where(key).values(last_checked_at=stamp, last_detail_checked_at=stamp,
                last_error=error, missing_count=count,
                status="unavailable" if count >= 2 else "pending_verification"))


    def upsert_review_item(self, source, external_id, data):
        stamp = now()
        key = and_(review_items.c.source == source, review_items.c.external_id == external_id)
        with self.engine.begin() as db:
            old = db.execute(select(review_items).where(key)).mappings().first()
            if old:
                db.execute(update(review_items).where(key).values(data=data, last_imported_at=stamp))
            else:
                db.execute(insert(review_items).values(source=source, external_id=external_id,
                    data=data, first_imported_at=stamp, last_imported_at=stamp))
        return "updated" if old else "new"

    def count_review_items(self, source=None):
        with self.engine.connect() as db:
            query = select(review_items)
            if source:
                query = query.where(review_items.c.source == source)
            return sum(1 for _ in db.execute(query))

    def review_data(self):
        with self.engine.connect() as db:
            return [row["data"] for row in db.execute(select(review_items)).mappings()]

    def due(self, source="olx", hours=24, limit=50):
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        with self.engine.connect() as db:
            return list(db.execute(select(listings).where(
                listings.c.source == source, or_(listings.c.last_detail_checked_at.is_(None),
                                                 listings.c.last_detail_checked_at <= cutoff))
                .order_by(listings.c.last_detail_checked_at.asc().nulls_first(), listings.c.external_id)
                .limit(limit)).mappings())

    def export(self, source="olx"):
        with self.engine.connect() as db:
            return [{**row["data"], "source": source, "status": row["status"],
                     "first_seen_at": row["first_seen_at"], "last_seen_at": row["last_seen_at"],
                     "last_checked_at": row["last_checked_at"]}
                    for row in db.execute(select(listings).where(listings.c.source == source)
                                          .order_by(listings.c.external_id)).mappings()]

    def recent_runs(self):
        with self.engine.connect() as db:
            return [dict(row) for row in db.execute(select(runs).order_by(
                runs.c.started_at.desc()).limit(10)).mappings()]
