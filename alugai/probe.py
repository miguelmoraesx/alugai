"""Bounded sample, repeatable URLs and a report for manual quality review."""
import time

from .network import Blocked, FetchError
from .parser import LayoutError, canonical_url, parse_page
from .store import now


def probe(store, fetcher, seed, limit=10, previous=None):
    if not 1 <= limit <= 10:
        raise ValueError("O experimento aceita de 1 a 10 anúncios")
    run_id = store.start_run("probe-firecrawl")
    started = time.monotonic()
    report = {"run_id": run_id, "started_at": now(), "status": "running", "seed": seed,
              "selected": [], "results": [], "errors": [], "manual_review": "pending"}
    try:
        if previous is None:
            html, url = fetcher.get(seed)
            rows, _, rejected = parse_page(html, url)
            report["errors"].extend(rejected)
            selected = [{"external_id": row.external_id, "url": row.url,
                         "search_data": row.data()} for row in rows[:limit]]
        else:
            selected = previous.get("selected")
            if not isinstance(selected, list) or not selected:
                raise ValueError("Relatório anterior sem amostra de URLs")
            selected = selected[:limit]
            for item in selected:
                if not isinstance(item, dict) or not str(item.get("external_id", "")).isdigit():
                    raise ValueError("Amostra anterior inválida")
                canonical_url(item.get("url", ""))
        report["selected"] = selected
        previous_results = {r["external_id"]: r.get("data") for r in (previous or {}).get("results", [])}
        for item in selected:
            result = {"external_id": item["external_id"], "url": item["url"], "status": "pending"}
            report["results"].append(result)
            try:
                html, url = fetcher.get(item["url"])
                rows, _, rejected = parse_page(html, url)
                report["errors"].extend(rejected)
                listing = next((row for row in rows if row.external_id == item["external_id"]), None)
                if listing is None:
                    raise LayoutError("Detalhes não correspondem ao ID solicitado")
                # Isolate experiment data from operational listings until reviewed.
                result["persistence"] = store.upsert(listing, source="olx-probe", detail=True)
                result["status"] = "success"
                result["data"] = listing.data()
                old = previous_results.get(item["external_id"])
                result["changes_since_previous"] = ({key: {"before": old.get(key), "after": value}
                    for key, value in result["data"].items() if old.get(key) != value} if old else None)
                result["manual_checks"] = {key: None for key in
                                           ("rent_price", "condo_fee", "neighborhood", "rental_period")}
            except (FetchError, LayoutError, ValueError) as exc:
                result["status"] = "failed"
                result["error"] = str(exc)
                if isinstance(exc, (Blocked, LayoutError)):
                    raise
                report["errors"].append(str(exc))
        report["status"] = "partial" if report["errors"] else "success"
    except (FetchError, LayoutError, ValueError) as exc:
        report["status"] = "blocked" if isinstance(exc, Blocked) else "failed"
        report["errors"].append(str(exc))
    except Exception:
        store.finish_run(run_id, "failed", {}, "Erro inesperado no experimento")
        raise
    report["finished_at"] = now()
    report["elapsed_seconds"] = round(time.monotonic() - started, 2)
    report["valid_details"] = sum(item["status"] == "success" for item in report["results"])
    report["transport"] = fetcher.metrics()
    report["estimated_base_credits_per_valid_listing"] = (
        round(report["transport"]["estimated_base_credits"] / report["valid_details"], 2)
        if report["valid_details"] else None)
    store.finish_run(run_id, report["status"], report, "; ".join(report["errors"][:10]) or None)
    return report
