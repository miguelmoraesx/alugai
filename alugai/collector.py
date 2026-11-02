from .network import Blocked, FetchError, Missing
from .parser import LayoutError, parse_page


def execute(store, fetcher, mode, *, seed, limit=50, max_pages=1, stale_hours=24):
    run_id = store.start_run(mode)
    stats = dict(pages=0, processed=0, new=0, updated=0, unchanged=0,
                 rejected=0, failed=0, pending=0, pagination_not_followed=0)
    errors = []
    try:
        if mode == "discover":
            queue, visited, seen = [seed], set(), set()
            while queue and stats["pages"] < max_pages and stats["processed"] < limit:
                url = queue.pop(0)
                if url in visited:
                    continue
                visited.add(url)
                html, final_url = fetcher.get(url)
                stats["pages"] += 1
                rows, next_urls, rejected = parse_page(html, final_url)
                stats["rejected"] += len(rejected)
                errors.extend(rejected)
                for listing in rows:
                    if listing.external_id in seen:
                        continue
                    seen.add(listing.external_id)
                    result = store.upsert(listing)
                    stats[result] += 1
                    stats["processed"] += 1
                    if stats["processed"] >= limit:
                        break
                queue.extend(u for u in next_urls if u not in visited and u not in queue)
            stats["pagination_not_followed"] = len(queue)
        elif mode == "refresh":
            for row in store.due(hours=stale_hours, limit=limit):
                try:
                    html, final_url = fetcher.get(row["url"])
                    stats["pages"] += 1
                    parsed, _, rejected = parse_page(html, final_url)
                    stats["rejected"] += len(rejected)
                    errors.extend(rejected)
                    listing = next((item for item in parsed if item.external_id == row["external_id"]), None)
                    if listing is None:
                        raise LayoutError("Resposta não contém o anúncio solicitado")
                    stats[store.upsert(listing, detail=True)] += 1
                    stats["processed"] += 1
                except Blocked as exc:
                    store.mark_error("olx", row["external_id"], str(exc))
                    stats["pending"] += 1
                    raise
                except (FetchError, LayoutError) as exc:
                    store.mark_error("olx", row["external_id"], str(exc), missing=isinstance(exc, Missing))
                    stats["failed"] += 1
                    errors.append(str(exc))
                    if isinstance(exc, LayoutError):
                        raise  # A layout change affects the whole adapter.
        else:
            raise ValueError("Modo desconhecido")
        status = "partial" if stats["rejected"] or stats["failed"] else "success"
    except (Blocked, FetchError, LayoutError, ValueError) as exc:
        status = "blocked" if isinstance(exc, Blocked) else "failed"
        errors.append(str(exc))
    except Exception:
        store.finish_run(run_id, "failed", stats, "Erro inesperado; verificar execução local")
        raise
    if hasattr(fetcher, "metrics"):
        stats["transport"] = fetcher.metrics()
    store.finish_run(run_id, status, stats, "; ".join(errors[:10]) or None)
    return {"run_id": run_id, "status": status, **stats, "errors": errors[:10]}
