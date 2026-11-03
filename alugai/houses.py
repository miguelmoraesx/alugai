"""High-confidence house collection: discover via search cards, verify via detail pages.

Search cards are used only for discovery. Every candidate is fetched as an
individual detail page before any acceptance decision, and only records that
pass every acceptance rule are staged in review items.
"""
from __future__ import annotations

from .cards import SOURCES, parse_cards, url_for
from .detail import accept, serialize
from .network import Blocked, FetchError, Missing
from .parser import LayoutError
from .review import duplicate_candidates
from .store import now

# Category-filtered search: only residential houses for rent in Manaus.
CASA_SEED = "https://www.olx.com.br/imoveis/aluguel/casas/estado-am/regiao-de-manaus/manaus"
HOUSE_SEEDS = {source: values[1] for source, values in SOURCES.items()}
HOUSE_SEEDS["olx"] = CASA_SEED


def collect_houses(store, fetcher, search_url, *, source="olx", max_details=30,
                   max_accepted=20):
    run_id = store.start_run("collect-houses-" + source)
    report = {
        "run_id": run_id, "status": "running", "search_url": search_url,
        "started_at": now(), "discovered": 0, "inspected": 0, "accepted": 0,
        "source": source, "rejected": {}, "errors": [], "accepted_ids": [],
        "possible_duplicates": [],
    }
    try:
        url_for(search_url, source)
        html, url = fetcher.get(search_url)
        cards, stats = parse_cards(html, source, limit=100)
        report["discovered"] = len(cards)
        report["search_stats"] = stats

        for card in cards:
            if report["accepted"] >= max_accepted or report["inspected"] >= max_details:
                break
            listing = card.listing
            external_id = listing.external_id
            detail_url = listing.url
            report["inspected"] += 1
            try:
                detail_html, final_url = fetcher.get(detail_url)
                scrape_id = fetcher.calls[-1].get("scrape_id") if fetcher.calls else None
                accepted, record, reasons = accept(
                    detail_html, final_url, source=source, requested_url=detail_url,
                    search_url=search_url,
                    scrape_id=scrape_id, collected_at=now())
                if record["external_id"] != external_id:
                    accepted = False
                    reasons = [*reasons, "external_id_mismatch"]
                if accepted:
                    store.upsert_review_item(source, record["external_id"], serialize(record))
                    report["accepted"] += 1
                    report["accepted_ids"].append(external_id)
                else:
                    for reason in reasons:
                        report["rejected"][reason] = report["rejected"].get(reason, 0) + 1
            except Missing:
                report["rejected"]["detail_missing_404"] = report["rejected"].get("detail_missing_404", 0) + 1
            except Blocked:
                raise
            except (FetchError, LayoutError, ValueError) as exc:
                report["errors"].append(f"{external_id}: {type(exc).__name__}")
        report["status"] = "success" if not report["errors"] else "partial"
    except (Blocked, FetchError, LayoutError, ValueError) as exc:
        report["status"] = "blocked" if isinstance(exc, Blocked) else "failed"
        report["errors"].append(str(exc))
    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append(type(exc).__name__)
    finally:
        report["finished_at"] = now()
        report["transport"] = fetcher.metrics()
        report["rejected"] = dict(sorted(report["rejected"].items(), key=lambda item: -item[1]))
        try:
            report["possible_duplicates"] = duplicate_candidates(store.review_data())
            report["cross_source_duplicates"] = [pair for pair in report["possible_duplicates"]
                if pair["a"].split(":", 1)[0] != pair["b"].split(":", 1)[0]]
        except (KeyError, TypeError, ValueError):
            report["possible_duplicates"] = []
            report["cross_source_duplicates"] = []
        store.finish_run(run_id, report["status"], report,
                         "; ".join(report["errors"][:10]) or None)
    return report
