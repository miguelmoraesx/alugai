import argparse
import json
import os
from pathlib import Path

from filelock import FileLock, Timeout

from .collector import execute
from .network import Fetcher, FetchError
from .firecrawl import FirecrawlFetcher, read_api_key
from .probe import probe
from .parser import SEED, LayoutError, parse_page
from .store import Store


def positive(value):
    result = int(value)
    if result < 1:
        raise argparse.ArgumentTypeError("Use um inteiro positivo")
    return result


def main():
    parser = argparse.ArgumentParser(description="Coletor Alugaí: OLX, sem contornar bloqueios")
    parser.add_argument("--database-url", default=os.getenv("ALUGAI_DATABASE_URL", "sqlite:///data/collector.db"))
    sub = parser.add_subparsers(dest="command", required=True)
    review = sub.add_parser("review-snapshots", help="Comparar HTMLs salvos de três fontes sem acessar a rede")
    review.add_argument("--snapshots", type=Path, default=Path("data/snapshots"))
    review.add_argument("--output", type=Path, default=Path("data/review"))
    review.add_argument("--limit", type=positive, default=20)
    for name in ("discover", "refresh"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--limit", type=positive, default=50)
        cmd.add_argument("--max-pages", type=positive, default=1)
        cmd.add_argument("--stale-hours", type=positive, default=24)
        cmd.add_argument("--seed", default=SEED)
        cmd.add_argument("--provider", choices=["http", "firecrawl"], default="http")
        cmd.add_argument("--max-api-calls", type=positive, default=13)
    experiment = sub.add_parser("probe-firecrawl", help="Uma busca e até dez anúncios, com relatório")
    experiment.add_argument("--seed", default=SEED)
    experiment.add_argument("--limit", type=positive, choices=range(1, 11), default=10)
    experiment.add_argument("--max-api-calls", type=positive, default=13)
    experiment.add_argument("--output", type=Path, default=Path("data/firecrawl-probe.json"))
    experiment.add_argument("--repeat-report", type=Path)
    ingest = sub.add_parser("import-html", help="Validar HTML salvo sem acesso à rede")
    ingest.add_argument("path", type=Path)
    ingest.add_argument("--url", default=SEED)
    ingest.add_argument("--fixture", action="store_true", help="Separa dados sintéticos em olx-fixture")
    export = sub.add_parser("export")
    export.add_argument("--output", type=Path, default=Path("data/listings.json"))
    export.add_argument("--source", choices=["olx", "olx-fixture", "olx-probe"], default="olx")
    sub.add_parser("runs", help="Últimas dez execuções")
    args = parser.parse_args()
    Path("data").mkdir(exist_ok=True)
    try:
        # Prevent overlapping scheduled/manual invocations in this checkout.
        with FileLock("data/collector.lock", timeout=0):
            store = Store(args.database_url)
            try:
                result = dispatch(args, store)
            finally:
                store.close()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not isinstance(result, dict) or result.get("status", "success") == "success" else 2
    except Timeout:
        print(json.dumps({"status": "failed", "error": "Já existe um coletor em execução neste checkout"}))
        return 2
    except Exception as exc:
        # Avoid dumping DB credentials or page content through arbitrary exceptions.
        result = {"status": "failed", "error_type": type(exc).__name__}
        if isinstance(exc, (LayoutError, FetchError)):
            result["error"] = str(exc)
        print(json.dumps(result, ensure_ascii=False))
        return 2


def dispatch(args, store):
    if args.command == "review-snapshots":
        from .review import build_review
        return build_review(args.snapshots, args.output, args.database_url, args.limit)
    if args.command == "probe-firecrawl":
        if args.output.exists():
            raise FetchError("O relatório de saída já existe; use outro nome para preservar a comparação")
        previous = None
        if args.repeat_report:
            previous = json.loads(args.repeat_report.read_text(encoding="utf-8"))
            if not isinstance(previous, dict):
                raise FetchError("Relatório anterior inválido")
        fetcher = FirecrawlFetcher(read_api_key(), max_calls=args.max_api_calls)
        try:
            result = probe(store, fetcher, args.seed, args.limit, previous)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            return result
        finally:
            fetcher.close()
    if args.command in ("discover", "refresh"):
        fetcher = (FirecrawlFetcher(read_api_key(), max_calls=args.max_api_calls)
                   if args.provider == "firecrawl" else
                   Fetcher(user_agent=os.getenv("ALUGAI_USER_AGENT", "AlugaiCollector/0.1")))
        try:
            return execute(store, fetcher, args.command, seed=args.seed, limit=args.limit,
                           max_pages=args.max_pages, stale_hours=args.stale_hours)
        finally:
            fetcher.close()
    if args.command == "import-html":
        run_id = store.start_run("import-html-fixture" if args.fixture else "import-html")
        try:
            rows, _, errors = parse_page(args.path.read_text(encoding="utf-8"), args.url)
            for row in rows:
                store.upsert(row, source="olx-fixture" if args.fixture else "olx")
            status = "partial" if errors else "success"
            result = dict(status=status, processed=len(rows), rejected=len(errors), errors=errors)
            store.finish_run(run_id, status, result)
            return result
        except Exception as exc:
            store.finish_run(run_id, "failed", {}, str(exc) if isinstance(exc, LayoutError) else type(exc).__name__)
            raise
    if args.command == "export":
        rows = store.export(args.source)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return dict(status="success", exported=len(rows), output=str(args.output))
    return store.recent_runs()
