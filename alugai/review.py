"""Local review staging; never publishes records or merges uncertain duplicates."""
from collections import Counter
from datetime import datetime, timezone
from html import escape
import hashlib
import json
from pathlib import Path
import unicodedata

from sqlalchemy import Column, JSON, MetaData, String, Table, create_engine, insert, select, update

from .cards import SOURCES, parse_cards

meta = MetaData()
review_items = Table("collector_review_items", meta,
    Column("source", String(32), primary_key=True),
    Column("external_id", String(64), primary_key=True),
    Column("data", JSON, nullable=False),
    Column("first_imported_at", String(40), nullable=False),
    Column("last_imported_at", String(40), nullable=False))


def normalized(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', value or '').lower() if not unicodedata.combining(c))


def duplicate_candidates(rows):
    pairs = []
    for i, a in enumerate(rows):
        for b in rows[i+1:]:
            required = ("neighborhood", "area_m2", "bedrooms", "rent_price")
            if any(a[k] is None or b[k] is None for k in required):
                continue
            if (normalized(a["neighborhood"]) == normalized(b["neighborhood"])
                    and a["bedrooms"] == b["bedrooms"]
                    and abs(a["area_m2"] - b["area_m2"]) <= 2
                    and abs(float(a["rent_price"]) - float(b["rent_price"])) <= float(a["rent_price"]) * .05):
                pairs.append({"a": a["source"] + ":" + a["external_id"],
                              "b": b["source"] + ":" + b["external_id"],
                              "reason": "Mesmo bairro/quartos, área até 2 m² e preço até 5%; revisar, não mesclar"})
    return pairs


def summary(rows):
    flags = Counter(flag for row in rows for flag in row["warnings"])
    return {"count": len(rows),
            "core_complete": sum(all(row[k] is not None for k in ("rent_price", "neighborhood", "area_m2", "bedrooms")) for row in rows),
            "monthly_explicit": sum(row["rental_period"] == "monthly" for row in rows),
            "condo_usable": sum(row["condo_status"] in ("reported", "exempt", "included") for row in rows),
            "iptu_amount_usable": sum(row["iptu_status"] in ("reported", "exempt", "included") for row in rows),
            "flags": dict(flags), "availability_verified": 0, "published": 0}


def build_review(snapshot_dir, output_dir, database_url, limit=20):
    snapshot_dir, output_dir = Path(snapshot_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    rows, sources = [], {}
    for source in SOURCES:
        path = snapshot_dir / (source + ".html")
        if not path.exists():
            sources[source] = {"status": "missing_snapshot"}
            continue
        raw = path.read_bytes()
        parsed, stats = parse_cards(raw.decode("utf-8"), source, limit)
        items = [item.data() for item in parsed]
        provenance_path = snapshot_dir / (source + ".metadata.json")
        provenance = json.loads(provenance_path.read_text(encoding="utf-8")) if provenance_path.exists() else {}
        for item in items:
            item["provenance"] = {"search_url": SOURCES[source][1],
                                  "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
                                  "scrape_id": provenance.get("scrapeId"),
                                  "imported_at": stamp,
                                  "observation_scope": "search_card_only"}
        rows.extend(items)
        sources[source] = {"status": "parsed", **stats, **summary(items)}
    if not rows:
        raise ValueError("Nenhum snapshot disponível para comparação")
    pairs = duplicate_candidates(rows)
    involved = {pair[key] for pair in pairs for key in ("a", "b")}
    for row in rows:
        if row["source"] + ":" + row["external_id"] in involved:
            row["warnings"].append("possible_duplicate")
    report = {"generated_at": stamp, "scope": "Amostra não aleatória de uma página por fonte; sem verificação de disponibilidade",
              "sources": sources, "total": len(rows), "possible_duplicates": pairs,
              "published": 0, "items": rows}
    engine = create_engine(database_url)
    try:
        meta.create_all(engine)
        with engine.begin() as db:
            for row in rows:
                where = (review_items.c.source == row["source"]) & (review_items.c.external_id == row["external_id"])
                old = db.execute(select(review_items).where(where)).mappings().first()
                if old:
                    db.execute(update(review_items).where(where).values(data=row, last_imported_at=stamp))
                else:
                    db.execute(insert(review_items).values(source=row["source"], external_id=row["external_id"],
                        data=row, first_imported_at=stamp, last_imported_at=stamp))
    finally:
        engine.dispose()
    (output_dir / "comparison.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "index.html").write_text(render(report), encoding="utf-8")
    return {"status": "success", "total": len(rows), "sources": sources,
            "possible_duplicate_pairs": len(pairs), "published": 0,
            "report": str((output_dir / "index.html").resolve())}


def render(report):
    def cell(value):
        return escape(str(value)) if value is not None else "—"
    summary_rows = ''.join('<tr>' + ''.join('<td>' + cell(v) + '</td>' for v in
        (name, s.get('count', 0), s.get('core_complete', 0), s.get('monthly_explicit', 0),
         s.get('condo_usable', 0), s.get('iptu_amount_usable', 0))) + '</tr>'
        for name, s in report['sources'].items())
    details = []
    for row in report['items']:
        details.append(f'''<tr data-source="{cell(row['source'])}"><td>{cell(row['source'])}<br>{cell(row['external_id'])}</td>
<td><a href="{escape(row['url'], quote=True)}" target="_blank" rel="noopener noreferrer">{cell(row['title'])}</a><br>{cell(row['neighborhood'])}</td>
<td>{cell(row['rent_price'])}</td><td>{cell(row['condo_fee'])}<br>{cell(row['condo_status'])}</td>
<td>{cell(row['iptu'])}<br>Período: {cell(row['iptu_period'])}</td>
<td>{cell(row['area_m2'])} m² / {cell(row['bedrooms'])} quartos</td>
<td>{cell(', '.join(row['warnings'])) or 'Sem alertas automáticos; revisão pendente'}</td></tr>''')
    return f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alugaí — revisão das fontes</title><style>
body{{font-family:system-ui,sans-serif;margin:32px;background:#f5f7fa;color:#13233b}}main{{max-width:1400px;margin:auto}}
h1{{margin-bottom:8px}}p{{line-height:1.5}}table{{border-collapse:collapse;width:100%;background:white;margin:20px 0}}th,td{{text-align:left;padding:12px;border-bottom:1px solid #dde3ec;vertical-align:top;font-size:14px}}th{{background:#e7edf5}}a{{color:#1656a6}}.scroll{{overflow-x:auto}}select,input{{padding:10px;margin-right:12px}}.notice{{background:#fff3ce;padding:16px;border-radius:8px}}
</style><main><h1>Alugaí · base de revisão</h1><p>{report['total']} referências extraídas · 0 publicadas · {len(report['possible_duplicates'])} pares de possíveis duplicações</p>
<p class="notice">Amostra de cartões de busca. Preços não confirmam disponibilidade. IPTU sem periodicidade não foi convertido em custo mensal.
Nenhuma foto ou contato foi republicado. Possíveis duplicações permanecem separadas.</p>
<h2>Comparação da amostra</h2><div class="scroll"><table><thead><tr><th>Fonte</th><th>Anúncios</th><th>Preço/bairro/área/quartos</th><th>Mensal explícito</th><th>Condomínio utilizável*</th><th>Valor IPTU utilizável*</th></tr></thead><tbody>{summary_rows}</tbody></table></div>
<p>*Valor informado acima de R$ 1, isenção ou inclusão explícita; não significa verificação humana. A periodicidade do IPTU pode continuar desconhecida.</p>
<label>Fonte <select id="source"><option value="">Todas</option><option>olx</option><option>vivareal</option><option>ponta_negra</option></select></label>
<label>Buscar <input id="query" placeholder="Bairro, código ou alerta"></label>
<div class="scroll"><table id="items"><thead><tr><th>Fonte / ID</th><th>Anúncio / bairro</th><th>Aluguel anunciado (R$)</th><th>Condomínio (R$)</th><th>IPTU (R$)</th><th>Características</th><th>Revisar</th></tr></thead><tbody>{''.join(details)}</tbody></table></div>
<p>Gerado: {cell(report['generated_at'])}. Esta página é local e não altera o site público.</p></main>
<script>function filter(){{const s=document.getElementById('source').value,q=document.getElementById('query').value.toLocaleLowerCase();document.querySelectorAll('#items tbody tr').forEach(r=>r.hidden=(s&&r.dataset.source!==s)||!r.textContent.toLocaleLowerCase().includes(q));}}document.getElementById('source').onchange=filter;document.getElementById('query').oninput=filter;</script></html>'''
