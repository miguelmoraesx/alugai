from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, func

from alugai.cards import parse_cards, exact_number, url_for
from alugai.parser import parse_page, SEED
from alugai.review import build_review, review_items, duplicate_candidates, render

# Synthetic fixtures retain only the observed semantic selectors, not real content.
OLX = '''<section class="olx-adcard">
<a data-testid="adcard-link" href="https://am.olx.com.br/imoveis/exemplo-123">Exemplo</a>
<span>R$ 4.000</span><h3 class="olx-adcard__price">R$ 3.100</h3>
<p class="olx-adcard__location">Manaus, Planalto</p>
<div class="olx-adcard__detail" aria-label="70 metros quadrados"></div>
<div class="olx-adcard__detail" aria-label="2 quartos"></div>
<div class="olx-adcard__detail" aria-label="5 ou mais banheiros"></div>
</section>'''

VR = '''<li data-cy="rp-property-cd"><a href="https://www.vivareal.com.br/imovel/exemplo-id-456/?source=ranking" title="Exemplo">
<div data-cy="rp-cardProperty-price-txt">R$ 5.500 / mês <p>Cond. R$ 1 • IPTU isento</p></div>
<h2 data-cy="rp-cardProperty-location-txt">Flores, Manaus</h2>
<li data-cy="rp-cardProperty-propertyArea-txt">Tamanho do imóvel 61 - 62 m²</li>
<li data-cy="rp-cardProperty-bedroomQuantity-txt">Quantidade de quartos 3</li>
</a></li>'''

LOCAL = '''<article class="c49-property-card">
<h2 class="c49-property-card_title">Exemplo à venda</h2>
<a class="c49btn-details" href="https://www.pontanegraimoveis.com.br/789/imoveis/exemplo">Detalhes</a>
<div class="c49-property-card_address">Flores, Manaus - AM</div>
<div class="c49-property-card_price">
<div class="c49-property-card_rent-price">R$ 800.000,00 <span>Venda</span></div>
<div class="c49-property-card_rent-price">R$ 2.550,00 <span>Locação</span></div>
<div class="c49-property-card_other-prices">IPTU <b>R$ 87,27</b> Condomínio <b>R$ 450,55</b></div></div>
<div class="c49-property-card_description">valor do anúncio de R$2.500,00 e o valor somente do aluguel</div>
</article>'''


def test_olx_real_layout_without_next_data():
    rows, _, errors = parse_page(OLX, SEED)
    assert not errors
    assert rows[0].rent_price == Decimal('3100')  # ignores old crossed price
    assert rows[0].area_m2 == 70
    assert rows[0].bathrooms is None
    assert rows[0].condo_fee is None


def test_vivareal_symbolic_fee_exemption_and_range():
    rows, _ = parse_cards(VR, 'vivareal')
    row = rows[0].data()
    assert row['condo_fee'] == '1.00'
    assert row['condo_status'] == 'needs_review'
    assert row['iptu'] == '0.00' and row['iptu_status'] == 'exempt'
    assert row['area_m2'] is None
    assert row['rental_period'] == 'monthly'
    assert row['monthly_total'] is None
    assert '?' not in row['url']


def test_local_sale_and_rental_same_class():
    rows, _ = parse_cards(LOCAL, 'ponta_negra')
    row = rows[0].data()
    assert row['rent_price'] == '2550.00'
    assert row['condo_fee'] == '450.55'
    assert row['iptu_period'] == 'unknown'
    assert 'description_price_conflict' in row['warnings']
    assert 'transaction_title_conflict' in row['warnings']


def test_sale_only_and_group_cards_are_skipped():
    sale = LOCAL.replace('Locação', 'Venda')
    rows, stats = parse_cards(sale + LOCAL, 'ponta_negra')
    assert len(rows) == 1 and stats['skipped_sale_or_group'] == 1
    group = '<li data-cy="rp-property-cd"><a href="#">Ver os 6 anúncios</a></li>'
    rows, stats = parse_cards(group + VR, 'vivareal')
    assert len(rows) == 1 and stats['skipped_sale_or_group'] == 1


@pytest.mark.parametrize('value', ['5+', '5 ou mais banheiros', '61 - 62 m²'])
def test_non_exact_numeric_values(value):
    assert exact_number(value) is None


def test_source_url_is_checked():
    with pytest.raises(ValueError):
        url_for('https://evil.example/imovel/123', 'vivareal')


def test_review_idempotent_separate_table_and_escaped_html(tmp_path):
    snapshots = tmp_path / 'snapshots'
    snapshots.mkdir()
    (snapshots / 'olx.html').write_text(OLX, encoding='utf-8')
    (snapshots / 'vivareal.html').write_text(VR, encoding='utf-8')
    (snapshots / 'ponta_negra.html').write_text(LOCAL, encoding='utf-8')
    db_url = 'sqlite:///' + (tmp_path / 'review.db').as_posix()
    result = build_review(snapshots, tmp_path / 'output', db_url)
    build_review(snapshots, tmp_path / 'output', db_url)
    assert result['total'] == 3 and result['published'] == 0
    engine = create_engine(db_url)
    with engine.connect() as db:
        assert db.scalar(select(func.count()).select_from(review_items)) == 3
        data = db.execute(select(review_items.c.data)).scalars().first()
        assert data['review_status'] == 'pending'
        assert data['publication_status'] == 'not_published'
    engine.dispose()
    data['title'] = '<script>alert(1)</script>'
    html = render({'sources': {}, 'total': 1, 'possible_duplicates': [], 'items': [data], 'generated_at': 'test'})
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in html


def test_similarity_does_not_merge_or_change_records():
    row = parse_cards(OLX, 'olx')[0][0].data()
    another = {**row, 'source': 'vivareal', 'external_id': '999'}
    rows = [row, another]
    assert len(duplicate_candidates(rows)) == 1
    assert len(rows) == 2
