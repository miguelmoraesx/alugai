# Alugaí: plano de implementação do MVP

**Estado: plano aprovado pelo usuário em 2026-11-02 (checkpoints de testes e decisões). Implementação em andamento: fase 0 liberada em 2026-11-03.** O andamento de cada fase é o registrado nos commits; a parte não implementada segue sem execução.

## Visão geral

**Objetivo.** Metabuscador privado de aluguel residencial em Manaus, que mostra o custo mensal real ou "confirme com o anunciante", e a origem de cada anúncio. Um único operador roda tudo localmente.

**Fluxo de dados.**

1. `sample` lê poucas páginas por site, depois dos termos lidos por uma pessoa. O resultado decide quais sites ficam no lote.
2. `collect` lê sitemap → página do anúncio → adaptador → validação → fotos → Postgres.
3. `review build` e `review apply`: o operador revê em HTML local e decide por arquivo.
4. O site Next.js lê somente views só de leitura. Publicar é uma consulta, nunca um campo: fonte liberada, versão atual aprovada, disponível, não expirada, não retirada, não inválida.
5. Dado alterado sai do site até nova aprovação. Página que sumiu sai depois de duas verificações. Sem confirmação em 30 dias, expira.

**Fases.** 0 Base → 1 Banco → 2 Obtenção → 3 Amostragem e adaptadores → 4 Validação → 5 Fotos → 6 Revisão → 8 Passada real. A fase 7 (Site) corre em paralelo a partir da fase 1, com dados sintéticos. Requisições reais só começam na fase 3, com PR próprio integrado e termos lidos.

**Estado do plano.**

- Passou por três contestações: duas rejeições e uma aprovação com ressalvas. As ressalvas editoriais estão aplicadas (seção 19).
- **Decisões:** registradas na seção 16; só falta indicar a unidade da UEA (P17). **Faltam** as pendências externas da seção 17. A primeira é o alinhamento com Miguel e Pedro.
- **Limite:** o autor só leu arquivos e documentação. **Nenhum comando, teste ou migração foi executado**, e nenhuma requisição foi feita às imobiliárias. Todo "esperado" é previsão. SQL nunca rodou.

---

Bases: documentos 00 e 01, reproduzidos com numeração de linha nos Apêndices A e B (o 01 prevalece sobre o 00); citações como `00:55` apontam para essas linhas. As contestações `03`, `05` e `07` e os planos intermediários não fazem parte deste documento; o resultado delas está na seção 19.

Legenda: **[USUÁRIO]** decisão do usuário. **[PROPOSTA]** padrão da sessão principal. **[FATO]** verificado. **[NOVA]** decisão deste plano.

**Evidência sobre o código.** Âncoras lidas contra `main@7d5ac7f` e a cópia do coletor. A identidade da cópia com a branch vem do `cmp` da sessão principal nos 107 arquivos versionados, nenhum diferente; o passo `F0.1` repete com `git`.

---

## 1. Escopo e forças

Um operador roda scripts locais que obtêm anúncios de aluguel de seis imobiliárias de Manaus, valida, revisa à mão e publica em um site Next.js privado. O produto só tem valor se o que aparece for verdadeiro.

**Escopo geográfico [USUÁRIO].** Lançamento só no município de Manaus. Os outros estados da região Norte e o interior do Amazonas ficam de fora. A **Zona Norte de Manaus** faz parte do produto (`region-norte`).

| # | NFR | Significado verificável |
|---|---|---|
| 1 | Veracidade do publicado (falha fechada) | Na dúvida, não aparece e a taxa não soma |
| 2 | Conformidade da coleta | robots, parada em bloqueio, trava de termos, dados fora do Git |
| 3 | Manutenibilidade por um operador | Poucas peças e estados; recuperação pelo CLI |
| 4 | Custo de revisão | O trabalho não se repete sem mudança real |
| 5 | Cobertura (~200) | Alvo sem mínimo rígido [USUÁRIO] |
| 6 | Latência e escala | Não otimizados |

Em conflito, vence o número menor.

---

## 2. Decisões de arquitetura

ADR curto. Rev.: dupla = barato desfazer; única = caro. Não há `AGENTS.md`; depois do checkpoint, estas decisões vão para `docs/decisoes.md`.

| Id | Decisão | Alternativas rejeitadas | Sacrifício | Rev. |
|---|---|---|---|---|
| D1 | `pg` com SQL à mão; está na lista de `serverExternalPackages` (documentação conferida) | `postgres`, fora da lista. Prisma/Drizzle: segundo dono do schema. API Python: mais um serviço | Sem tipos gerados; `NUMERIC` em string; mitigado por `map-row.ts` e `PUBLISHED_COLUMNS` | Dupla |
| D2 | Alembic com `op.execute(SQL)`; SQLAlchemy Core em `db/tables.py`; `alembic check` para colunas | `create_all` [USUÁRIO]. Autogenerate não cobre views nem expressão de CHECK | Colunas em dois lugares | Única após dados reais; migração só para a frente |
| D3 | `TEXT` + CHECK nomeado | ENUM: remover valor é caro | CHECK repetido | Dupla |
| D4 | Link `/?imovel=<public_id>`; um dialog controlado em `HomeClient`, com `key={property.id}`; ao fechar, `replaceState` tira o parâmetro | `#id`: servidor não vê. `/imovel/[id]`: segunda superfície | HTTP 200 em link indisponível; sem metadados | Dupla |
| D5 | `public_id`: 10 caracteres de `abcdefghjkmnpqrstuvwxyz23456789` | Hash de fonte + ID: reversível. Sequencial: expõe volume. UUID: longo | Nenhum relevante | **Única**, quando um link circular |
| D6 | Fotos por `GET /fotos/[publicId]/[position]`, via `published_listing_photos`; 404 ausente/retirado/sem arquivo, 503 banco fora, `no-store` | `public/`: risco de Git, segue servindo. `next/image` remoto: hotlink | Sem otimização; view extra (C5) | Dupla |
| D7 | `alugai/` na raiz, como na branch do Pedro; `tests/`, `migrations/`, `config/`; site em `lib/catalog/`, `e2e/` | `collector/`, workspaces: diff maior | Duas pilhas na raiz | Dupla |
| D8 | Testes do site só com Playwright Test (U17) | Vitest + Testing Library: mocks de Server Component e Leaflet. Cypress: sem ganho | Suíte lenta, Chromium | Dupla |
| D9 | Postgres real em três bancos: `alugai_test` (pytest), `alugai_e2e_test` (Playwright), `alugai_mig_test` (`T1.1`). Sem sufixo `_test`, recusa. Sem banco, falha | SQLite: views usam `LATERAL`, arrays, `now()` | Docker obrigatório | Dupla |
| D10 | Revisão derivada de `reviews`, só de inclusão: `approved`, `rejected`, `reopened`; correção em `resolved_*`; hash cobre o observado | `listing_overrides`: peça extra. `review_status`: redundante | `LATERAL` | Dupla até decisões reais |
| D11 | `listing_versions` com colunas próprias | JSONB contraria [USUÁRIO] | ~24 colunas duplicadas | Dupla |
| D12 | Foto: baixa só o necessário; views servem só `sha256` em `listings.photo_hashes`; foto que sai da seleção mantém arquivo; só retirada e rejeição apagam | Baixar tudo: ~1.000 requisições semanais | **Foto trocada sob a mesma URL não é detectada** (C1, U1) | Dupla |
| D13 | Página válida com dado impublicável: `invalid_since`/`invalid_reason`; sai do site, dados preservados, sem renovar `last_seen_at` | Gravar nulos: polui versões. `unavailable`: seria falso | Condição além das cinco do 00 (C2, U3) | Dupla |
| D14 | Revisão por HTML estático + `decisoes.txt` de uso único | Tela no Next: escrita e autenticação. Comando por anúncio: ~200 | Sem filtro no relatório | Dupla |
| D15 | Server Component + `HomeClient`; `searchParams` torna a rota dinâmica; `next build` sem banco | API + `fetch`: mais uma rota | Catálogo nas props | Dupla |
| D16 | `Fetcher` com `HostPolicy` (HTTPS, sem credenciais, porta 443, host listado; vale em URL inicial, `Location`, `<loc>`, foto), 3 entradas, intervalo por origem, cache de falha de robots | Clientes separados: duplica regras | Host de fotos próprio aumenta taxa total | Dupla |
| D17 | Sitemap com `defusedxml` | `xml.etree`: sem proteção. `lxml`: nativa | Dependência pequena | Dupla |
| D18 | Fontes em `config/sources.toml`; termos e status mudam por comando | Domínios no plano: só o da Ponta Negra é conhecido (`cards.py:16`) | Repositório público mostra os sites, se assim decidido (U21) | Dupla |
| D19 | PR-B1 (amostragem) antes de qualquer requisição | Tudo em um PR: código sem revisão contra terceiros | Um PR a mais (C14) | Dupla |
| D20 | Hero estático, sem anúncio; `page.tsx:206,209` quebra com catálogo vazio | Sortear anúncio: destaca foto de terceiros | Visual | Dupla |
| D21 | Parada por degradação **depois de gravar**, com aceite auditável; seção 5.3 | Adiar e descartar: preço falso até 30 dias e laço. Sem parada: catálogo cai em silêncio | Defeito de adaptador tira anúncios do site até a correção (C15, U18) | Dupla |
| D22 | Bairros: `config/neighborhoods.csv` é a única fonte | Apelido por comando: duas fontes | Editar arquivo | Dupla |
| D23 | Formato do hash congelado no pré-voo da fase 8. Mudança depois: `approve-batch` com colunas iguais aprova e copia `resolved_*` | Coluna de versão: diferença de colunas basta | Campo novo no hash exige revisão normal | **Única na prática** |
| D24 | **Sem restauração por backup.** Seção 5.8 | `pg_dump` + restaurar: republica retirado. Diário de decisões reaplicado: mais uma peça para evento raro | Perda do banco custa re-revisão (U19) | Dupla |

**Contrato do pool (`lib/catalog/db.ts`).** Instância em `globalThis`; `max: 5`; `connectionTimeoutMillis: 3000`; `statement_timeout: 5000`; listener em `pool.on("error")`, que registra sem detalhes (a documentação do `pg` avisa que, sem ele, o processo pode cair).

---

## 3. Schema

Migrações `0001_tables` e `0002_views_role`.

Peças além das sete do 00: `collection_runs` ([PROPOSTA] 01 §7; é também a sessão de revisão); `listing_review_state` (regra única de revisão); `listing_public_status` (01 §4); `published_listing_photos` (D6); `listings.photo_hashes` (D12).

### 3.1 Tabelas

```sql
CREATE TABLE sources (
  id                   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  slug                 TEXT NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9_]+$'),
  display_name         TEXT NOT NULL,
  domain               TEXT NOT NULL UNIQUE,
  adapter              TEXT,                   -- nulo até o adaptador existir; collect exige
  sitemap_urls         TEXT[] NOT NULL,
  photo_hosts          TEXT[] NOT NULL DEFAULT '{}',
  photo_robots_waivers JSONB NOT NULL DEFAULT '[]', -- [{host, by, at, reason}]; só para robots ausente
  status               TEXT NOT NULL DEFAULT 'candidate'
    CONSTRAINT ck_sources_status CHECK (status IN ('candidate','approved','suspended','removed')),
  collection_state     TEXT NOT NULL DEFAULT 'ok'
    CONSTRAINT ck_sources_collection_state CHECK (collection_state IN ('ok','blocked')),
  collection_state_at  TIMESTAMPTZ,
  collection_state_reason TEXT,
  terms_result         TEXT
    CONSTRAINT ck_sources_terms_result CHECK (terms_result IN ('allowed','silent','prohibited','not_found')),
  terms_checked_at     TIMESTAMPTZ,
  terms_checked_by     TEXT,
  terms_url            TEXT,
  notice_sent_at       TIMESTAMPTZ,
  created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT ck_sources_terms_complete CHECK (
    (terms_result IS NULL) = (terms_checked_at IS NULL)
    AND (terms_result IS NULL) = (terms_checked_by IS NULL)),
  CONSTRAINT ck_sources_blocked_has_reason CHECK (
    collection_state = 'ok' OR (collection_state_at IS NOT NULL AND collection_state_reason IS NOT NULL)),
  CONSTRAINT ck_sources_approved_needs_terms CHECK (
    status <> 'approved' OR (terms_checked_at IS NOT NULL AND terms_result <> 'prohibited'))
);

CREATE TABLE neighborhoods (
  id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  slug          TEXT NOT NULL UNIQUE,
  name          TEXT NOT NULL UNIQUE,
  aliases       TEXT[] NOT NULL DEFAULT '{}',
  zone          TEXT NOT NULL
    CONSTRAINT ck_neighborhoods_zone CHECK (zone IN ('region-norte','region-sul','region-leste',
      'region-oeste','region-centro-sul','region-centro-oeste')),
  near_ufam     BOOLEAN NOT NULL DEFAULT false,
  near_uea      BOOLEAN NOT NULL DEFAULT false,
  near_pim      BOOLEAN NOT NULL DEFAULT false,
  source_note   TEXT NOT NULL
);

CREATE TABLE collection_runs (
  id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  mode         TEXT NOT NULL CONSTRAINT ck_runs_mode CHECK (mode IN ('sample','collect','review')),
  source_id    BIGINT REFERENCES sources(id),  -- nulo em review
  started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at  TIMESTAMPTZ,
  status       TEXT NOT NULL DEFAULT 'running'
    CONSTRAINT ck_runs_status CHECK (status IN
      ('running','success','partial','blocked','layout_stop','failed','discarded')),
  counters     JSONB NOT NULL DEFAULT '{}',    -- só lidos no relatório; inclui aceite de mudança em massa
  reason       TEXT
);

CREATE TABLE listings (
  id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  public_id           TEXT NOT NULL UNIQUE
    CONSTRAINT ck_listings_public_id CHECK (public_id ~ '^[a-hjkmnp-z2-9]{10}$'),
  source_id           BIGINT NOT NULL REFERENCES sources(id),
  external_id         TEXT NOT NULL,
  source_url          TEXT NOT NULL CONSTRAINT ck_listings_url_https CHECK (source_url LIKE 'https://%'),
  advertiser_name     TEXT,
  creci               TEXT,
  source_title        TEXT NOT NULL,
  property_type       TEXT NOT NULL
    CONSTRAINT ck_listings_property_type CHECK (property_type IN
      ('apartment','house','condo_house','kitnet','studio','room','other')),
  bedrooms            SMALLINT CONSTRAINT ck_listings_bedrooms CHECK (bedrooms >= 0),
  bathrooms           SMALLINT CONSTRAINT ck_listings_bathrooms CHECK (bathrooms >= 0),
  parking_spaces      SMALLINT CONSTRAINT ck_listings_parking CHECK (parking_spaces >= 0),
  area_m2             NUMERIC(10,2) CONSTRAINT ck_listings_area CHECK (area_m2 > 0),
  rent_amount         NUMERIC(12,2) NOT NULL CONSTRAINT ck_listings_rent CHECK (rent_amount > 0),
  rent_period         TEXT NOT NULL
    CONSTRAINT ck_listings_rent_period CHECK (rent_period IN ('monthly','assumed_monthly','short_term','unknown')),
  condo_amount        NUMERIC(12,2) CONSTRAINT ck_listings_condo_amount CHECK (condo_amount >= 0),
  condo_status        TEXT NOT NULL
    CONSTRAINT ck_listings_condo_status CHECK (condo_status IN
      ('reported','exempt','included','unknown','on_request','needs_review')),
  iptu_amount         NUMERIC(12,2) CONSTRAINT ck_listings_iptu_amount CHECK (iptu_amount >= 0),
  iptu_status         TEXT NOT NULL
    CONSTRAINT ck_listings_iptu_status CHECK (iptu_status IN
      ('reported','exempt','included','unknown','on_request','needs_review')),
  iptu_period         TEXT NOT NULL DEFAULT 'unknown'
    CONSTRAINT ck_listings_iptu_period CHECK (iptu_period IN ('monthly','annual','unknown')),
  pet_policy          TEXT NOT NULL DEFAULT 'unknown'
    CONSTRAINT ck_listings_pet CHECK (pet_policy IN ('yes','no','unknown','on_request')),
  city                TEXT NOT NULL,
  neighborhood_raw    TEXT NOT NULL,
  neighborhood_id     BIGINT REFERENCES neighborhoods(id),
  street              TEXT,
  latitude            NUMERIC(9,6) CONSTRAINT ck_listings_lat CHECK (latitude BETWEEN -90 AND 90),
  longitude           NUMERIC(9,6) CONSTRAINT ck_listings_lng CHECK (longitude BETWEEN -180 AND 180),
  location_precision  TEXT NOT NULL DEFAULT 'none'  -- com coordenada: approximate, salvo a fonte declarar exata
    CONSTRAINT ck_listings_precision CHECK (location_precision IN ('exact','approximate','none')),
  photo_hashes        TEXT[] NOT NULL DEFAULT '{}', -- conjunto ordenado que entrou no content_hash
  first_seen_at       TIMESTAMPTZ NOT NULL,
  last_seen_at        TIMESTAMPTZ NOT NULL,   -- só página baixada e validada renova
  last_checked_at     TIMESTAMPTZ NOT NULL,
  source_updated_at   TIMESTAMPTZ,            -- lastmod do sitemap
  expires_at          TIMESTAMPTZ NOT NULL,   -- last_seen_at + 30 dias, gravado no código (coluna gerada exige IMMUTABLE)
  availability_status TEXT NOT NULL DEFAULT 'active'
    CONSTRAINT ck_listings_availability CHECK (availability_status IN ('active','verifying','unavailable')),
  missing_count       SMALLINT NOT NULL DEFAULT 0,
  last_missing_at     TIMESTAMPTZ,
  last_error          TEXT,
  invalid_since       TIMESTAMPTZ,
  invalid_reason      TEXT,
  withdrawn_at        TIMESTAMPTZ,
  withdrawn_by        TEXT,
  withdrawn_reason    TEXT,
  content_hash        TEXT NOT NULL CONSTRAINT ck_listings_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  warnings            TEXT[] NOT NULL DEFAULT '{}',
  evidence            JSONB NOT NULL DEFAULT '{}',
  CONSTRAINT uq_listings_identity UNIQUE (source_id, external_id),
  CONSTRAINT ck_listings_expiry_after_seen CHECK (expires_at > last_seen_at),
  CONSTRAINT ck_listings_coords_pair CHECK ((latitude IS NULL) = (longitude IS NULL)),
  CONSTRAINT ck_listings_precision_coords CHECK ((location_precision = 'none') = (latitude IS NULL)),
  CONSTRAINT ck_listings_condo_consistent CHECK (
    (condo_status = 'reported' AND condo_amount IS NOT NULL)
    OR (condo_status IN ('exempt','included','unknown','on_request') AND condo_amount IS NULL)
    OR condo_status = 'needs_review'),
  CONSTRAINT ck_listings_iptu_consistent CHECK (
    (iptu_status = 'reported' AND iptu_amount IS NOT NULL)
    OR (iptu_status IN ('exempt','included','unknown','on_request') AND iptu_amount IS NULL)
    OR iptu_status = 'needs_review'),
  CONSTRAINT ck_listings_invalid_pair CHECK ((invalid_since IS NULL) = (invalid_reason IS NULL)),
  CONSTRAINT ck_listings_withdrawn_complete CHECK (
    (withdrawn_at IS NULL) = (withdrawn_by IS NULL) AND (withdrawn_at IS NULL) = (withdrawn_reason IS NULL))
);
CREATE INDEX ix_listings_neighborhood ON listings(neighborhood_id);

-- Só campos do hash, mesmos tipos de listings.
CREATE TABLE listing_versions (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  listing_id BIGINT NOT NULL REFERENCES listings(id),
  capture_id BIGINT,                 -- FK adicionada após captures
  observed_at TIMESTAMPTZ NOT NULL,
  content_hash TEXT NOT NULL CONSTRAINT ck_versions_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  adapter_version TEXT NOT NULL,
  source_title TEXT NOT NULL,
  property_type TEXT NOT NULL CONSTRAINT ck_versions_property_type CHECK (property_type IN
    ('apartment','house','condo_house','kitnet','studio','room','other')),
  bedrooms SMALLINT, bathrooms SMALLINT, parking_spaces SMALLINT, area_m2 NUMERIC(10,2),
  rent_amount NUMERIC(12,2) NOT NULL,
  rent_period TEXT NOT NULL CONSTRAINT ck_versions_rent_period CHECK (rent_period IN
    ('monthly','assumed_monthly','short_term','unknown')),
  condo_amount NUMERIC(12,2),
  condo_status TEXT NOT NULL CONSTRAINT ck_versions_condo_status CHECK (condo_status IN
    ('reported','exempt','included','unknown','on_request','needs_review')),
  iptu_amount NUMERIC(12,2),
  iptu_status TEXT NOT NULL CONSTRAINT ck_versions_iptu_status CHECK (iptu_status IN
    ('reported','exempt','included','unknown','on_request','needs_review')),
  iptu_period TEXT NOT NULL CONSTRAINT ck_versions_iptu_period CHECK (iptu_period IN ('monthly','annual','unknown')),
  pet_policy TEXT NOT NULL CONSTRAINT ck_versions_pet CHECK (pet_policy IN ('yes','no','unknown','on_request')),
  neighborhood_raw TEXT NOT NULL, street TEXT, city TEXT NOT NULL,
  latitude NUMERIC(9,6), longitude NUMERIC(9,6),
  advertiser_name TEXT, creci TEXT,
  photo_hashes TEXT[] NOT NULL DEFAULT '{}'
);
CREATE INDEX ix_versions_listing ON listing_versions(listing_id, observed_at DESC);
CREATE INDEX ix_versions_hash ON listing_versions(listing_id, content_hash);

CREATE TABLE captures (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  run_id BIGINT NOT NULL REFERENCES collection_runs(id),
  source_id BIGINT NOT NULL REFERENCES sources(id),
  listing_id BIGINT REFERENCES listings(id),
  kind TEXT NOT NULL CONSTRAINT ck_captures_kind CHECK (kind IN ('sitemap','page','robots')),
  url TEXT NOT NULL,
  final_url TEXT,
  fetched_at TIMESTAMPTZ NOT NULL,
  http_status SMALLINT,
  body_sha256 TEXT,
  source_lastmod TIMESTAMPTZ,
  adapter_version TEXT,
  result TEXT NOT NULL CONSTRAINT ck_captures_result CHECK (result IN
    ('accepted','rejected','not_found','blocked','fetch_error','layout_error','internal_error','not_applicable')),
  reason TEXT,
  raw_path TEXT CONSTRAINT ck_captures_raw_path CHECK (raw_path !~ '(^/|\.\.)'),
  raw_expires_at TIMESTAMPTZ,
  CONSTRAINT ck_captures_raw_pair CHECK ((raw_path IS NULL) = (raw_expires_at IS NULL))
);
CREATE INDEX ix_captures_url ON captures(source_id, url, fetched_at DESC);
CREATE INDEX ix_captures_listing ON captures(listing_id);
CREATE INDEX ix_captures_run ON captures(run_id);
ALTER TABLE listing_versions ADD CONSTRAINT fk_versions_capture
  FOREIGN KEY (capture_id) REFERENCES captures(id);

CREATE TABLE reviews (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  listing_id BIGINT NOT NULL REFERENCES listings(id),
  run_id BIGINT REFERENCES collection_runs(id),
  decision TEXT NOT NULL CONSTRAINT ck_reviews_decision CHECK (decision IN ('approved','rejected','reopened')),
  reason TEXT,
  reviewer TEXT NOT NULL CONSTRAINT ck_reviews_reviewer CHECK (length(trim(reviewer)) > 0),
  decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  content_hash TEXT NOT NULL CONSTRAINT ck_reviews_hash CHECK (content_hash ~ '^[0-9a-f]{64}$'),
  resolved_condo_status TEXT CONSTRAINT ck_reviews_condo CHECK (resolved_condo_status IN
    ('reported','exempt','included','unknown','on_request')),
  resolved_condo_amount NUMERIC(12,2),
  resolved_iptu_status TEXT CONSTRAINT ck_reviews_iptu CHECK (resolved_iptu_status IN
    ('reported','exempt','included','unknown','on_request')),
  resolved_iptu_amount NUMERIC(12,2),
  resolved_iptu_period TEXT CONSTRAINT ck_reviews_iptu_period CHECK (resolved_iptu_period IN ('monthly','annual','unknown')),
  CONSTRAINT ck_reviews_reason_required CHECK (decision = 'approved' OR reason IS NOT NULL),
  CONSTRAINT ck_reviews_resolved_only_approved CHECK (decision = 'approved' OR
    (resolved_condo_status IS NULL AND resolved_iptu_status IS NULL)),
  CONSTRAINT ck_reviews_condo_pair CHECK (
    (resolved_condo_status IS NULL AND resolved_condo_amount IS NULL)
    OR (resolved_condo_status = 'reported' AND resolved_condo_amount IS NOT NULL)
    OR (resolved_condo_status IN ('exempt','included','unknown','on_request') AND resolved_condo_amount IS NULL)),
  CONSTRAINT ck_reviews_iptu_pair CHECK (
    (resolved_iptu_status IS NULL AND resolved_iptu_amount IS NULL)
    OR (resolved_iptu_status = 'reported' AND resolved_iptu_amount IS NOT NULL)
    OR (resolved_iptu_status IN ('exempt','included','unknown','on_request') AND resolved_iptu_amount IS NULL))
);
CREATE INDEX ix_reviews_latest ON reviews(listing_id, decided_at DESC, id DESC);

CREATE TABLE listing_photos (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  listing_id BIGINT NOT NULL REFERENCES listings(id),
  source_url TEXT NOT NULL,
  position SMALLINT CONSTRAINT ck_photos_position CHECK (position BETWEEN 1 AND 5), -- nulo: fora da seleção
  sha256 TEXT CONSTRAINT ck_photos_sha CHECK (sha256 ~ '^[0-9a-f]{64}$'),           -- mantido após apagar
  storage_path TEXT CONSTRAINT ck_photos_path CHECK (storage_path !~ '(^/|\.\.)'),
  content_type TEXT CONSTRAINT ck_photos_type CHECK (content_type IN ('image/jpeg','image/png','image/webp')),
  byte_size INTEGER,
  status TEXT NOT NULL DEFAULT 'pending'
    CONSTRAINT ck_photos_status CHECK (status IN ('pending','stored','failed','deleted')),
  fetched_at TIMESTAMPTZ,
  deleted_at TIMESTAMPTZ,
  last_error TEXT,
  CONSTRAINT uq_photos_url UNIQUE (listing_id, source_url),
  CONSTRAINT ck_photos_stored_complete CHECK (status <> 'stored' OR
    (sha256 IS NOT NULL AND storage_path IS NOT NULL AND content_type IS NOT NULL)),
  CONSTRAINT ck_photos_deleted_no_path CHECK (status <> 'deleted' OR storage_path IS NULL)
);
CREATE UNIQUE INDEX uq_photos_position ON listing_photos(listing_id, position) WHERE position IS NOT NULL;
```

`advertiser_type` do 01 é fixo em `agency`, sem consumidor: não vira coluna. `location_precision` fica no banco porque o 00 a lista, mas não vai ao site (seção 6.3).

### 3.2 Views

```sql
-- Interna. Regra única de revisão e valores efetivos.
CREATE VIEW listing_review_state AS
SELECT l.id AS listing_id, r.id AS review_id, cur.approved_current,
  CASE WHEN r.id IS NULL OR r.decision = 'reopened' OR r.content_hash <> l.content_hash
       THEN 'pending' ELSE r.decision END AS review_status,
  CASE WHEN cur.approved_current AND r.resolved_condo_status IS NOT NULL
       THEN r.resolved_condo_status ELSE l.condo_status END AS condo_status,
  CASE WHEN cur.approved_current AND r.resolved_condo_status IS NOT NULL
       THEN r.resolved_condo_amount ELSE l.condo_amount END AS condo_amount,
  CASE WHEN cur.approved_current AND r.resolved_iptu_status IS NOT NULL
       THEN r.resolved_iptu_status ELSE l.iptu_status END AS iptu_status,
  CASE WHEN cur.approved_current AND r.resolved_iptu_status IS NOT NULL
       THEN r.resolved_iptu_amount ELSE l.iptu_amount END AS iptu_amount,
  CASE WHEN cur.approved_current AND r.resolved_iptu_status IS NOT NULL
       THEN COALESCE(r.resolved_iptu_period, 'unknown') ELSE l.iptu_period END AS iptu_period
FROM listings l
LEFT JOIN LATERAL (
  SELECT * FROM reviews x WHERE x.listing_id = l.id ORDER BY x.decided_at DESC, x.id DESC LIMIT 1
) r ON true
CROSS JOIN LATERAL (
  SELECT COALESCE(r.decision = 'approved' AND r.content_hash = l.content_hash, false) AS approved_current
) cur;

-- Contrato do site. Lista fechada: warnings, evidence e caminhos nunca entram.
CREATE VIEW published_listings AS
SELECT
  l.public_id, l.source_title, s.display_name AS source_name, l.source_url,
  l.advertiser_name, l.creci, l.property_type,
  l.bedrooms, l.bathrooms, l.parking_spaces, l.area_m2,
  l.rent_amount, l.rent_period,
  st.condo_amount, st.condo_status, st.iptu_amount, st.iptu_status, st.iptu_period,
  f.iptu_monthly,
  l.rent_amount + f.condo_monthly + f.iptu_monthly AS monthly_total, -- NULL propaga
  l.pet_policy, l.city, n.name AS neighborhood, l.street,
  l.latitude, l.longitude, l.last_seen_at,
  array_remove(ARRAY[n.zone,
    CASE WHEN n.near_ufam THEN 'ufam' END,
    CASE WHEN n.near_uea  THEN 'uea'  END,
    CASE WHEN n.near_pim  THEN 'pim'  END], NULL) AS zones,
  COALESCE((SELECT array_agg(p.position ORDER BY p.position) FROM listing_photos p
            WHERE p.listing_id = l.id AND p.status = 'stored' AND p.position IS NOT NULL
              AND p.sha256 = ANY(l.photo_hashes)),
           '{}') AS photo_positions
FROM listings l
JOIN sources s ON s.id = l.source_id
JOIN neighborhoods n ON n.id = l.neighborhood_id          -- bairro não reconhecido fica fora
JOIN listing_review_state st ON st.listing_id = l.id
CROSS JOIN LATERAL (SELECT
  CASE st.condo_status WHEN 'reported' THEN st.condo_amount
                       WHEN 'exempt' THEN 0 WHEN 'included' THEN 0 END AS condo_monthly,
  CASE WHEN st.iptu_status IN ('exempt','included') THEN 0
       WHEN st.iptu_status = 'reported' AND st.iptu_period = 'monthly' THEN st.iptu_amount
       WHEN st.iptu_status = 'reported' AND st.iptu_period = 'annual' THEN round(st.iptu_amount / 12, 2)
  END AS iptu_monthly) f
WHERE s.status = 'approved'                                   -- 1. fonte liberada
  AND st.review_status = 'approved'                           -- 2. versão atual aprovada
  AND l.availability_status IN ('active','verifying')         -- 3. disponível
  AND l.expires_at > now()                                    -- 4. não expirado
  AND l.withdrawn_at IS NULL                                  -- 5. não retirado
  AND l.invalid_since IS NULL                                 -- D13
  AND l.rent_period IN ('monthly','assumed_monthly')          -- defesas: falham fechado
  AND l.property_type IN ('apartment','house','condo_house','kitnet','studio','room')
  AND l.city = 'Manaus'
  AND st.condo_status <> 'needs_review'
  AND st.iptu_status <> 'needs_review';

CREATE VIEW published_listing_photos AS
SELECT pl.public_id, p.position, p.storage_path, p.content_type
FROM published_listings pl
JOIN listings l ON l.public_id = pl.public_id
JOIN listing_photos p ON p.listing_id = l.id
WHERE p.status = 'stored' AND p.position IS NOT NULL
  AND p.sha256 = ANY(l.photo_hashes);

-- Exceção do 01 §4. Só existe o que um dia foi aprovado.
CREATE VIEW listing_public_status AS
SELECT l.public_id,
  CASE WHEN pl.public_id IS NOT NULL THEN 'published' ELSE 'unavailable' END AS state
FROM listings l
LEFT JOIN published_listings pl ON pl.public_id = l.public_id
WHERE EXISTS (SELECT 1 FROM reviews r WHERE r.listing_id = l.id AND r.decision = 'approved');
```

### 3.3 Papel do site

`0002` cria `alugai_site` com `LOGIN` e senha de `ALUGAI_SITE_DB_PASSWORD` (padrão só local), com `CONNECT` no banco corrente, `USAGE` em `public` e `SELECT` nas três views públicas. Criação com `DO` e teste de existência; o `downgrade` revoga sem apagar a role, global do cluster.

---

## 4. Transições

| Evento | Efeito | Teste |
|---|---|---|
| Sumiu do sitemap (descoberta completa, queda dentro do limite ou aceita) | `verifying`; continua na view; página entra no fim da lista | `T4.20`, `T1.7` |
| 404/410 em 2 verificações separadas | 1ª: `missing_count=1`, `verifying`. 2ª, com intervalo mínimo: `unavailable`, gravado na hora | `T4.21`, `T4.22`, `T4.19` |
| 200 "indisponível", redirecionamento para home, outro anúncio ou fora da política | Mesmo caminho do 404 | `T4.23`, `T4.24`, `T4.25`, `T3.20` |
| 401/403/429/CAPTCHA, inclusive desafio HTTP 200 em foto e XML | `blocked`; execução `blocked`; item corrente sem gravação; disponibilidade intacta | `T2.25`, `T2.41`, `T4.26`, `T5.7`, `T5.24` |
| Erro de rede | Conta na execução; `last_error`; disponibilidade intacta; 5 seguidos: `partial` | `T4.27`, `T4.48` |
| Erro de layout | Nada gravado; item segue; conta em D21 | `T4.28`, `T4.29` |
| `Disallow` em URL de página [NOVA] | Captura `fetch_error`, motivo `robots_disallow`; item segue; disponibilidade intacta; sem bloqueio da fonte. Sem confirmação, expira | `T2.42`, `T4.57` |
| `Disallow` em foto [NOVA] | Foto `failed`, motivo `robots_disallow`; página segue | `T5.23` |
| `unavailable` visto de novo, mesmo hash | `active`, `missing_count=0`, sem revisão | `T4.30` |
| `unavailable` visto de novo, hash novo | `active`, versão nova, pendente | `T4.31` |
| Expirou | Sai por `now()`; fotos ficam | `T1.7`, `T5.12` |
| Confirmado após expirar, mesmo hash | Renova, volta sem revisão | `T4.32` |
| `withdraw` | Registro em `data/retiradas.log`; `withdrawn_*`; fotos apagadas; coleta não requisita mais | `T6.8`, `T4.33` |
| Coleta nunca limpa `withdrawn_at` | Releitura com trava de linha antes de gravar | `T4.33`, `T4.49`, `T5.20` |
| `restore` | Limpa `withdrawn_*`; decisão `reopened`; registro `restore`; fotos selecionadas `deleted`→`pending`, sem rede | `T6.9`, `T6.23` |
| Rejeitado, mesmo hash | Permanece; sem fila; fotos apagadas; sem download | `T6.5`, `T5.9`, `T5.19` |
| Rejeitado, hash novo | Pendente; fotos baixadas na mesma coleta | `T1.14`, `T5.18` |
| `needs_review` | Aprovar recusa sem resolver; correção sobrevive ao mesmo hash; cai com hash novo | `T6.6`, `T6.7`, `T1.15` |
| Página válida, dado reprova [NOVA] | **Na hora:** `invalid_*`, sai da view, `last_seen_at` não renova, dados preservados | `T4.14`, `T4.34` |
| Volta válida, mesmo hash | Limpa `invalid_*`, sem revisão | `T4.11`, `T4.35` |
| Perda de campo antes preenchido | Versão nova, pendente | `T4.10`, `T4.13` |
| Degradação acima do limite (5.3) | Já gravados ficam; `layout_stop`; `blocked`; código 2 | `T4.11`-`T4.19` |
| Sitemap vazio ou incompleto | Ninguém vira `verifying`; `partial` | `T4.36` |
| Queda de sitemap acima do limite | Idem, até aceite | `T4.37` |
| Fora do sitemap, página válida | `active` | `T4.38` |
| `unavailable` fora do sitemap | Sem requisição | `T4.39` |
| A aprovado → B pendente → A | Aprovado, sem revisão | `T1.14` |
| A rejeitado → B pendente → A | Rejeitado; arquivos apagados depois do commit | `T5.21` |
| `reopen` | Decisão `reopened`; fora da view; fotos selecionadas `deleted`→`pending`, sem rede | `T6.10`, `T6.23` |
| Slug novo, mesmo ID | Confirmação; `source_url` atualizado; hash igual | `T4.25` |
| Banco recusa o dado | Rollback do item, `internal_error`, conta em D21, `partial`; banco fora: `failed` | `T4.50`, `T4.51` |
| Execução interrompida | Próxima `sample`/`collect` fecha só linhas `running` de `sample`/`collect` como `failed`; sessão de revisão não muda | `T3.9`, `T4.54` |
| Linha `stored` sem arquivo | `purge`: selecionada → `pending`; fora da seleção → `deleted` | `T5.14` |
| Fonte suspensa até voltar | Seção 5.9 | `T4.59` |
| Perda do banco | Seção 5.8 | `T4.56` |

### 4.1 O que a revisão pode fazer

| Situação | Aparece no relatório | Pode rejeitar | Pode aprovar |
|---|---|---|---|
| Pendente, comum | Sim | Sim | Sim |
| Pendente com `needs_review` | Sim, com o campo a resolver | Sim | Só resolvendo na linha |
| Pendente com `neighborhood_id` nulo | Sim | Sim | Não, até `neighborhood load` |
| Pendente com `title_has_phone` | Sim | Sim | Não |
| Pendente com foto de `sha256` conhecido fora de `stored` | Sim, com aviso | Sim | Não, até uma `collect` baixar. Se a fonte não entregar mais a foto, resta rejeitar (falha fechada) |
| Pendente com foto `failed` sem `sha256` | Sim, com `photo_failed` | Sim | Sim |
| Período ou tipo impublicável | Sim | Sim | Não |
| `invalid_since` | Só em contagem | Não | Não |
| Retirado | Não | Não | Não |
| Não pendente | Não | Não | Não |

`review apply` também recusa, para `a` e `r`: hash diferente; e anúncio com decisão posterior ao início da sessão, o que cobre `restore`/`reopen` feitos com o arquivo aberto.

---

## 5. Regras de execução do coletor

### 5.1 Pontos de entrada com rede

**Só `sample` e `collect` usam `Fetcher`**, sempre por `sources.open_fetcher(source)`, que chama `assert_collectable`. `T2.39` varre o código.

| Comando | Rede | Trava de fonte | Trava de arquivo | Teste |
|---|---|---|---|---|
| `sample`, inclusive `--robots-host` | Sim | Sim | Sim | `T3.2`, `T3.3`, `T3.7`, `T3.9` |
| `collect` | Sim | Sim; exige `adapter` | Sim | `T2.30`, `T4.26`, `T4.53`, `T4.55` |
| `purge` | Não | Não | Sim | `T5.22` |
| Demais | Não | Não | Não | `T6.24` |

`assert_collectable`: `status` em `candidate`/`approved`, termos preenchidos e não `prohibited`, `collection_state='ok'`. `FileLock` em `data/collector.lock`, `timeout=0`.

### 5.2 Algoritmo de `collect`

1. Fecha `running` de `sample`/`collect`, `assert_collectable`, abre execução, apaga HTML vencido.
2. `discover` + `classify_url`; deduplica por `external_id`; lê o registro de retiradas (5.8). Quem está retirado **sai da descoberta e dos conhecidos**.
3. Com descoberta completa, e queda dentro do limite ou aceita: conhecidos fora do sitemap, não retirados, fora do registro e não `unavailable`, viram `verifying`.
4. Lista, em ordem estável por `external_id` dentro de cada grupo: com foto selecionada `pending`, **conhecidos no sitemap, novos**, e ausentes por último. Assim, `--limit 5` depois de subir a `version` relê os mesmos anúncios já gravados.
5. Pulo:
   - conhecido: `lastmod` igual, confirmado há menos de 7 dias com a mesma versão de adaptador;
   - URL sem anúncio: rejeitada com o mesmo `lastmod` há menos de 30 dias e com a mesma versão;
   - sem `lastmod`: baixa sempre;
   - foto selecionada `pending`: nunca pula.
6. Para cada item, a seção 5.4, avaliando a seção 5.3 depois de cada item.
7. Fecha execução; status na seção 5.6.

**Subir a versão do adaptador é o caminho de recoleta.** O plano não tem `--force`.

### 5.3 Parada por degradação (D21)

**Grava sempre na hora; a regra só decide se continua.** Assim, um preço já visto como falso sai do site mesmo com execução interrompida, e não há nada adiado a perder.

**Degradado na execução:**
- `LayoutError`, de qualquer URL (não grava nada);
- conhecido sem `invalid_since` que passa a ser rejeitado;
- conhecido que perde campo antes preenchido: quartos, banheiros, vagas, área, ou taxa de `reported`/`exempt`/`included` para `unknown`;
- conhecido não `unavailable` com não encontrado (404/410, "indisponível", redirecionamento);
- `internal_error`.

**Não conta:** quem já tem `invalid_since` e é rejeitado de novo, quem já está `unavailable` e segue não encontrado, anúncio novo rejeitado, foto.

**Base:** conhecidos processados na execução, excluídos os já inválidos, somados às URLs com `LayoutError` ou `internal_error` fora desse conjunto. Todo degradado está na base, então a proporção não passa de 100%.

**Condição, avaliada depois de cada item:** `degradados ≥ 5` **e** `degradados / base ≥ 30%`. A parada é imediata: `layout_stop`, `blocked`, código 2. O que já foi gravado fica.

**Quanto pode sair do site.** O dano depende da forma do defeito. A recuperação é a mesma em todos: corrigir, subir `version`, e os afetados voltam sem revisão pelo mesmo hash (`invalid_*` limpo, ou A→B→A).

| Forma do defeito | O que acontece | Quanto sai |
|---|---|---|
| Atinge todas as páginas desde o início (âncora presente, valor vazio) | Para no 5º item | 5 anúncios por execução liberada |
| Parcial, abaixo de 30% | **Sem parada**: `success`, código 0. O sinal só aparece em `alugai report` | Todos os atingidos. Ex.: 25 de 100 |
| Começa no meio da execução | Para quando a proporção chega a 30% | Até 30% do processado. Ex.: 100 bons, depois ruins: ~43 |
| Âncora ausente (`LayoutError`) | Para no 5º; nada é gravado | Nenhum |
| Não encontrado em massa | 1ª execução: `missing_count=1`, para no 5º, ninguém sai. Execução liberada depois do intervalo: os processados viram `unavailable` na hora, e para no 5º | 5 por execução liberada; quando sobram menos de 5, sem parada |

**A parada avisa e limita por execução, mas não impede a queda.** Cada `source unblock` libera nova rodada, por isso o operador só deve desbloquear depois de examinar as capturas. No não encontrado em massa com 9 anúncios, dois `unblock` e quatro execuções derrubam todos (`T4.19`).

**`--limit`.** Não muda a gravação nem a regra. Execução menor apenas não alcança 5, e os dados gravados são os mesmos.

**Disponibilidade.** Layout nunca altera `availability_status`.

**Aceite auditável, para mudança real ou correção de adaptador.**

```
alugai source unblock <slug>
alugai collect <slug> --accept-mass-change --by <quem> --reason <motivo>
```

Na execução com a opção: a parada por degradação e a guarda de queda de sitemap ficam desligadas; `by`, `reason` e a contagem vão a `counters`; status normal. Exige fonte `ok`.

**Sem a opção.** Repetir a coleta avança em rejeição e perda de campo, pois quem já degradou não conta de novo. Com `LayoutError` ou `internal_error` nada foi gravado, e a repetição para no mesmo ponto: a saída é corrigir o adaptador ou usar o aceite. Não há impasse.

### 5.4 Fronteira de um item

1. Sem transação: `get_html` → `parse` → compara `final_url` → `validate`.
2. Reprovado: novo só grava captura; conhecido grava `invalid_*` + captura, em transação, e não baixa foto.
3. Aceito: `fetch_new_photos` baixa só URLs **sem linha**. `Blocked` encerra sem gravar o item; os arquivos ficam órfãos para `purge`.
4. Calcula o hash com os `sha256` conhecidos.
5. Se a última decisão não for "rejeitado com este hash": `fetch_missing_files` baixa selecionadas `pending`, `deleted` e `failed`. Bytes diferentes do `sha256` atualizam o valor e recalculam o hash.
6. Transação única: `SELECT ... FOR UPDATE`; se retirado, descarta tudo e remove a pasta. Zera posições e reatribui; grava fotos, `listings` com `photo_hashes` e `content_hash`, versão se o hash mudou, captura.
7. Depois do commit: se o estado derivado for `rejected` e houver arquivos, `delete_listing_photos`. Cobre A rejeitado → B → A e `r` durante a coleta.

### 5.5 Fotos

- **Caminho:** `$ALUGAI_PHOTOS_DIR/<public_id>/<sha256>.<ext>`.
- **Seleção:** 5 primeiras URLs, sem repetir `sha256`; repetida fica com `position=NULL`.
- **Hash:** `sha256` de toda selecionada com valor conhecido, em qualquer status. `sha256` nulo não entra.
- **Sai da seleção:** `position=NULL`, status e arquivo mantidos.
- **Apagar:** só `delete_listing_photos`, a pasta toda, depois de marcar `deleted` no banco. `failed` sem `sha256` continua `failed`.
- **Saídas de `deleted`:** `reopen`/`restore` → `pending`, só em selecionadas; rejeitado com hash novo, passo 5 da seção 5.4; rejeitado com mesmo hash: fica.
- **`failed`:** tentada de novo quando a página é processada, salvo rejeitado com mesmo hash.
- **Robots ausente em host de fotos:** `failed`, salvo liberação; uma tentativa por processo. **`waive-robots` vale só para robots ausente:** `Disallow` publicado depois prevalece.
- **HTML no lugar de imagem:** com marcador de desafio, `Blocked`. Sem marcador, `failed`, somando em `NETWORK_STOP_CONSECUTIVE`, junto com os erros de rede.

### 5.6 Status

| Status | Significado | Código |
|---|---|---|
| `success` | Terminou. Rejeição, `LayoutError` isolado e `Disallow` em página são normais e ficam em `counters` | 0 |
| `partial` | Falha de transporte, descoberta incompleta, queda não aceita, `internal_error` | 2 |
| `blocked` | 401/403/429/CAPTCHA ou robots ausente no host de páginas | 2 |
| `layout_stop` | Seção 5.3 | 2 |
| `failed` | Banco fora, registro de retiradas ilegível ou erro inesperado | 2 |
| `discarded` | Só sessão de revisão descartada | n/a |

### 5.7 HTML bruto

Captura aceita não grava arquivo. Rejeitada ou com erro: `data/html/<slug>/<capture_id>.html`, 7 dias. Amostra: `data/samples/<slug>/`, 30 dias. Todo comando começa apagando o vencido.

### 5.8 Perda do banco (D24)

**Não há restauração por backup.** Restaurar um dump devolveria ao site anúncio retirado depois do dump. Para operador único, local, com site privado, reconstruir é mais simples e falha fechado.

**Registro de retiradas.** `withdraw` acrescenta a `ALUGAI_RETIRADAS_LOG` (padrão `data/retiradas.log`), **antes** de gravar no banco, uma linha JSON com `action`, `source_slug`, `external_id`, `source_url`, `at`, `by`, `reason`. `restore` acrescenta `action: restore`. Vale a última linha de cada par. `collect` remove da descoberta quem está retirado: nem baixa a página, nem cria linha, nem baixa foto. `sample --url` recusa URL que esteja no registro. Linha ilegível: `collect` e `sample` encerram `failed`, sem requisição.

**Limite da garantia.** "Retirados não voltam" **depende de `data/retiradas.log` sobreviver**: é arquivo único, sem cópia, na mesma máquina do banco. Perder só o registro não tem efeito enquanto o banco existir, pois `withdrawn_at` continua filtrando. Perder os dois, como numa perda de disco, faz o anúncio voltar **pendente, sem aviso**, e ele pode ser reaprovado por engano. Nada é publicado sem aprovação humana (C20, U19).

**Procedimento se o banco for perdido** (`docs/coletor.md`):

1. Site fora do ar. `docker compose up -d --wait db`; `alembic upgrade head`.
2. `source sync`, `source terms`, `source set-status candidate`, `source waive-robots`, `source notice`, `neighborhood load`.
3. `alugai purge --all`, que limpa `data/photos` e exige a opção com banco vazio.
4. `collect` por site: tudo fica pendente, e os retirados não voltam.
5. Revisar de novo, `source set-status approved`. Subir o site.

**Consequências para o operador.**

- Refazer a revisão de ~200 anúncios e registrar de novo termos, status, liberações de robots e avisos.
- `public_id` novos: links antigos passam a "Não encontramos este anúncio".
- Rejeições anteriores não voltam: o anúncio reaparece pendente, e a decisão é humana.
- `docker compose down -v` apaga o banco: o documento avisa.
- Depois de reconstruir, `restore` de anúncio sem linha exige editar o registro à mão.

Se `withdraw` falhar depois de escrever o registro, o operador vê o erro e repete o comando, que é idempotente; até lá, a coleta já não toca o anúncio.

### 5.9 Recuperar fonte com dados ruins

Sem backup, é este o procedimento para dados ruins de uma fonte aprovada. **Nunca voltar direto a `approved` para coletar: isso republica os dados ruins até o fim da passada.**

| Passo | Comando | `sources.status` | No site |
|---|---|---|---|
| 1. Tirar do ar | `source set-status <slug> suspended` | `suspended` | Fora |
| 2. Corrigir o adaptador e subir `version` | Código | `suspended` | Fora |
| 3. Liberar coleta sem publicar | `source set-status <slug> candidate` | `candidate` | Fora; a view exige `approved` |
| 4. Desbloquear, se preciso | `source unblock <slug>` | `candidate` | Fora |
| 5. Recoletar | `collect <slug>`, com `--accept-mass-change` se a correção mudar muitos | `candidate` | Fora |
| 6. Conferir e revisar | `review build`, `review apply`, `report` | `candidate` | Fora |
| 7. Voltar | `source set-status <slug> approved` | `approved` | Só o aprovado com o hash atual |

No passo 7, dado corrigido com hash igual ao aprovado volta sem revisão, e hash novo só depois de aprovado no passo 6. `collect` em `suspended` é recusado de propósito (`T2.30`).

---

## 6. Contrato do site

### 6.1 Tipo

`lib/catalog/types.ts`. O nome `Property` é mantido, em módulo novo.

```ts
export const FEE_STATUSES = ["reported", "exempt", "included", "unknown", "on_request"] as const
export const IPTU_PERIODS = ["monthly", "annual", "unknown"] as const
export const PET_POLICIES = ["yes", "no", "unknown", "on_request"] as const
export const RENT_PERIODS = ["monthly", "assumed_monthly"] as const          // subconjunto do CHECK
export const PROPERTY_TYPES = ["apartment", "house", "condo_house", "kitnet", "studio", "room"] as const // sem "other"
export const PUBLISHED_COLUMNS = [
  "public_id", "source_title", "source_name", "source_url", "advertiser_name", "creci", "property_type",
  "bedrooms", "bathrooms", "parking_spaces", "area_m2", "rent_amount", "rent_period",
  "condo_amount", "condo_status", "iptu_amount", "iptu_status", "iptu_period", "iptu_monthly", "monthly_total",
  "pet_policy", "city", "neighborhood", "street", "latitude", "longitude", "last_seen_at", "zones", "photo_positions",
] as const

export type Property = {
  id: string; title: string; neighborhood: string; street: string | null; city: string
  rent: number; rentPeriod: (typeof RENT_PERIODS)[number]
  condo: number | null; condoStatus: (typeof FEE_STATUSES)[number]
  iptu: number | null; iptuStatus: (typeof FEE_STATUSES)[number]; iptuPeriod: (typeof IPTU_PERIODS)[number]
  iptuMonthly: number | null; monthlyTotal: number | null
  bedrooms: number | null; bathrooms: number | null
  parkingSpaces: number | null      // 0 = "Sem garagem"; null = oculto
  area: number | null
  petPolicy: (typeof PET_POLICIES)[number]; propertyType: (typeof PROPERTY_TYPES)[number]
  sourceName: string; sourceUrl: string; advertiserName: string | null; creci: string | null
  lastSeenAt: string                // ISO 8601
  latitude: number | null; longitude: number | null
  zones: string[]
  images: string[]                  // /fotos/<id>/<position>
}

export type SharedListing =
  | { kind: "none" } | { kind: "found"; id: string } | { kind: "unavailable" } | { kind: "not_found" }

// lib/catalog/queries.ts
export function getPublishedListings(): Promise<Property[]>  // ORDER BY last_seen_at DESC, public_id
export function resolveSharedListing(raw: string | string[] | undefined, listings: Property[]): Promise<SharedListing>
export function getPublishedPhoto(publicId: string, position: number): Promise<{ storagePath: string; contentType: string } | null>
// lib/catalog/map-row.ts
export function mapRow(row: PublishedRow): Property
// lib/catalog/format.ts: puras, fuso America/Manaus
export function formatBRL(value: number): string                // sem centavos só se inteiro; card, dialog, mapa
export function feeLabel(status, amount): string
export function iptuLabel(status, amount, period, iptuMonthly): string  // nunca recalcula
export function confirmLine(property: Property): string | null
export function seenLabel(iso: string): string                  // "Visto em 02/11/2026"
```

### 6.2 Mapeamento de cada campo atual

| Hoje | Novo | Usos (card, dialog e mapa são os componentes `property-*`) |
|---|---|---|
| `id` | `id` (`public_id`) | `page.tsx:168,278`; card `:26,36,61`; dialog `:21,28,102`; mapa `:29,144,149,154,165,198` |
| `title` | `title` (`source_title`, sem reescrita) | `page.tsx:54,141`; card `:42,60`; dialog `:29,56,75`; mapa `:162,195` |
| `neighborhood` | `neighborhood` (`neighborhoods.name`) | `page.tsx:30,33,54,141,168`; card `:26,42,60`; dialog `:21,29,56,76`; mapa `:162,195` |
| `rent` | `rent`, `rentPeriod` | `page.tsx:60`; card `:25,74,77`; dialog `:16,91`; mapa `:158,196` |
| `condo` | `condo`, `condoStatus` | Card `:25,77`; dialog `:16,92` |
| `iptu` | `iptu`, `iptuStatus`, `iptuPeriod`, `iptuMonthly` | Card `:25,77`; dialog `:16,93` |
| soma local | `monthlyTotal` | Card `:25,74`; dialog `:16,89` |
| `bedrooms`, `bathrooms`, `parkingSpaces` | `number \| null` | `page.tsx:56-58`; card `:65-67`; dialog `:80-82` |
| `area` | `number \| null` | Card `:68`; dialog `:83` |
| `petFriendly` | `petPolicy` | `page.tsx:59`; card `:69`; dialog `:84` |
| `source` | removido | Só em `lib/properties.ts` |
| `sourceLabel` | `sourceName` | Card `:80`; dialog `:97`; mapa `:195` |
| `advertiser` | removido (fixo `agency`) | `page.tsx:23,55`; card `:32-33,45-51`; dialog `:17-20,74`; mapa `:157,188,195`; `globals.css:128-130` |
| `latitude`, `longitude` | `number \| null` | Mapa `:160,166,172` |
| `zones` | `zones` | `page.tsx:23,30,55` |
| `images` | `images` | `page.tsx:206,209` saem; card `:30,42,55`; dialog `:25,56,60,63` |
| novos | `sourceUrl`, `lastSeenAt`, `advertiserName`, `creci`, `street` | Card `:80,81`; dialog `:74,76,100` |
| `quickFilters` | `lib/catalog/filters.ts` | Sai `owner`; `region-centro-oeste` depende de U7 |

### 6.3 Textos

| Situação | Texto |
|---|---|
| Taxa `reported` | Valor |
| `exempt` / `included` | Isento / Incluso no aluguel |
| `unknown` / `on_request` | Confirme com o anunciante / A combinar com o anunciante |
| IPTU com valor sem período | R$ X, período a confirmar |
| IPTU anual | R$ X por ano (R$ Y por mês) |
| Card com pendências | Uma linha "Confirme com o anunciante: condomínio, IPTU e pet", só com o que falta; `on_request` entra, e aparece por extenso no dialog |
| Total nulo | "Aluguel" e "taxas a confirmar", sem valor fechado |
| `assumed_monthly` | "Mensal presumido", discreto |
| Com coordenadas | "Localização aproximada, informada pela fonte", para todo anúncio |
| Link indisponível | Faixa "Este anúncio não está mais disponível" |
| Link inexistente ou mal formado | Faixa "Não encontramos este anúncio" |

---

## 7. Vigência e destino do código

**Base.** Site: `main@7d5ac7f`, com só `CLAUDE.md` não rastreado no status recebido. Coletor: cópia idêntica a `origin/codex/olx-collector`, nos 107 arquivos, por `cmp` da sessão principal; `.git/packed-refs:2` traz `53a68a4`. Conferido por leitura nas revisões e confirmado por amostragem nas contestações. Âncoras reconferidas por `grep -n` antes de cada edição.

**A branch `feat/catalogo-fontes-locais` nasce da `main`, que não tem coletor. Todo código Python parte de cópia com `git checkout 53a68a4 -- <arquivo>`, seguida de edição.** Linhas do coletor valem antes da edição.

**Crédito.** Commit que traz ou adapta código do Pedro: `Origem: origin/codex/olx-collector@53a68a4, <arquivo>:<linhas>` e `Co-authored-by: Pedro Belota <e-mail de git log -1 --format='%ae' origin/codex/olx-collector>`.

### 7.0 Atualização de 2026-11-03: a branch do Pedro avançou

A conferência `F0.1` encontrou `origin/codex/olx-collector` em `d441ad7`, um commit depois de `53a68a4`. **A base de cópia fica fixada em `53a68a4`:** todas as âncoras desta seção e o crédito continuam valendo, e os seis arquivos da fase 0 não mudaram entre os dois commits.

| Arquivo em `d441ad7` | Destino | Motivo |
|---|---|---|
| `alugai/detail.py` | Referência, fase 3 | `parse_ponta_detail` e `sanitize_description`; o restante não foi avaliado. O texto em `docs/firecrawl.md` afirma que o leitor da Ponta Negra foi validado ao vivo; a matriz da fase 3a confere |
| Acréscimos em `alugai/houses.py`, `cli.py` (`collect-houses`), `firecrawl.py`, `store.py`, `docs/firecrawl.md`, `tests/test_firecrawl.py` | Deixar | Coleta por Firecrawl em OLX, Viva Real e Ponta Negra, método fora do escopo [USUÁRIO]; a Ponta Negra segue no lote, pelo `Fetcher` |
| `alugai/network.py`, `parser.py` (`allowed_domains`) | Deixar | `HostPolicy` substitui; as âncoras de 7.1 valem em `53a68a4` |
| `tests/test_detail.py`, `test_houses.py`, `test_portal_details.py` | Referência | Casos sintéticos úteis na fase 3, reescritos com URLs `*.example` |

### 7.1 Branch do Pedro: destino de cada arquivo

| Arquivo | Destino | Linhas conferidas e ação |
|---|---|---|
| `alugai/__init__.py`, `__main__.py` | Trazer | Sem mudança |
| `alugai/network.py` | Adaptar | `:8,80,109` `canonical_url` → `HostPolicy`. `:26-33` intervalo → por origem. `:54-55` limite mantido. `:68-77` `check_block`: não decodifica binário. `:79-91` robots: cache de falha. `:96-97` `Disallow` → `DisallowedByRobots`. `:115-117` tipo → 3 entradas |
| `alugai/parser.py` | Adaptar parcialmente | `:13-14` `LayoutError` → `errors.py`. `:20-23` defesas → `HostPolicy`. `:28-47` `money` → `values.py`. `:50-56` `number` reescrita. `:119` regra mantida. Resto fica |
| `alugai/cards.py` | Adaptar + referência | `:16` domínio. `:31-33` `text` → `adapters/base.py`. `:36-63` base de `values.py`, com correções; `:48-49` isento → `None`. `:158-194` `ponta_card`, referência. Resto fica |
| `alugai/cli.py` | Referência | `:16-20` `positive`; `:54-74` trava, com alcance novo, e erros |
| `alugai/collector.py` | Referência | `:48,52,55-56,59` |
| `alugai/store.py` | Referência | `:67-90,92-101,103,112` |
| `alugai/review.py` | Adaptar parcialmente | `:23-41` trazidos, com Decimal. `render`, referência de escape |
| `alugai/firecrawl.py`, `probe.py` | Deixar | [USUÁRIO] |
| `tests/test_collector.py` | Adaptar parcialmente | `:38-47` → `test_values.py`. `:89-102` → `T4.21`, `T4.27`. `:105-181` → `test_network.py` |
| `tests/test_cards.py` | Adaptar parcialmente | `:28-37,61-68` → Code 49. `:54` comportamento alterado de propósito. `:80-82` → `test_values.py`. `:90-110,113-118` adaptados |
| `tests/test_firecrawl.py`, `tests/fixtures/search.html` | Deixar | Módulo e OLX não vêm |
| `compose.yaml` | Adaptar | `:9` configurável |
| `pyproject.toml` | Adaptar | `:10` adiciona `alembic`, `defusedxml` |
| `.gitignore` | Trazer | `:40-47`, mais `test-results/`, `playwright-report/` |
| `.env.example` | Adaptar | `:5-7` removidas; variáveis novas |
| `docs/coletor.md` | Adaptar na fase 8 | Mantém a seção de ética |
| `docs/integracao-catalogo.md`, `comparacao-fontes.md` | Referência | Citam fontes fora de escopo e anúncio real; não copiar |
| `docs/firecrawl.md`, `scripts/*.ps1` | Deixar | [USUÁRIO] |
| `README.md` | Referência | `:19-37` não vem; texto novo com crédito |

### 7.2 Site: edições ancoradas (fase 7)

Cópia em `main@7d5ac7f`; linha → conteúdo confirmado → mudança.

| Local | Conteúdo hoje | Mudança |
|---|---|---|
| `page.tsx:1,3-16,18-20` | Cliente, imports, `normalize` | Movido a `components/home-client.tsx` com `git mv`; **`:9` importa de `lib/properties`** → `lib/catalog` |
| `page.tsx:22-24` | `matchesQuickFilter`, `owner` | Sem `owner` |
| `page.tsx:26-31,33` | `locationGroups`, `allNeighborhoods` | `useMemo` sobre props |
| `page.tsx:35-49` | Estados | Novo `openId` |
| `page.tsx:51-63` | Filtro | Pet `=== "yes"`/`=== "no"`; quartos, banheiros, vagas: nulo fora com filtro, aviso |
| `page.tsx:65-66,278` | `slice`, mapa + lista | `mapProperties` memoizado |
| `page.tsx:104,141,168` | Contagens; datalist | Novas fontes; bairros únicos |
| `page.tsx:163` | "dona da kitnet" | Texto novo |
| `page.tsx:201-217` | Hero com `properties[4]`, "R$ 5.550" | Estático |
| `page.tsx:224,226` | "disponíveis", cores | "Cantinhos anunciados"; frase sai |
| `page.tsx:230-233` | Toggle | Mantido |
| `page.tsx:286,288` | Origem, WhatsApp | "Abra o anúncio original na imobiliária" |
| `page.tsx:296-306` | Seção de anunciante | Removida |
| `layout.tsx:6` | "fale direto com quem anuncia" | "...e veja a origem do anúncio." |
| `site-header.tsx:3-7,17,19-39` | Imports, link, formulário | Removidos |
| `property-card.tsx:3-6` | Imports; **`:5` importa `Property`**; `:6` dialog | Tipo novo; sem dialog |
| `property-card.tsx:12` | `money` | `formatBRL` |
| `property-card.tsx:14-24` | Props, estados | Acrescenta `onOpenDetails` |
| `property-card.tsx:25-27,32-33,45-51` | Total, WhatsApp, selos | Removidos |
| `property-card.tsx:28-31,37-44,53-55` | Galeria | 0 fotos: neutro; 1: sem navegação; sem `% 0` |
| `property-card.tsx:36,52` | `Card`, favorito | Mantidos |
| `property-card.tsx:60-61` | Título, prefixo | `#{id}` |
| `property-card.tsx:64-70` | Specs | Oculta nulos |
| `property-card.tsx:72-78` | Custo | `monthlyTotal`, rótulos |
| `property-card.tsx:80-81` | "Disponível hoje", WhatsApp | "Visto em"; "Ver detalhes"; "Ver anúncio original" |
| `property-details-dialog.tsx:3-5,10` | Imports; **`:5` importa `Property`**; `money` | Tipo novo; `formatBRL` |
| `property-details-dialog.tsx:12,44-48` | Assinatura, `DialogTrigger` | Controlado |
| `property-details-dialog.tsx:13-15` | Estados | Reiniciados por `key` |
| `property-details-dialog.tsx:16-22` | Soma, tipo, WhatsApp | Removidos |
| `property-details-dialog.tsx:23-26,50-70` | Galeria | Neutro sem fotos; crédito "Foto: <fonte>" |
| `property-details-dialog.tsx:27-41` | Compartilhar | `:28` → `` `${origin}/?imovel=${id}` `` |
| `property-details-dialog.tsx:73-77,79-85,87-95,97` | Cabeçalho, detalhes, custo, fonte | Textos da 6.3; rua; CRECI |
| `property-details-dialog.tsx:98-102` | Botões, código | "Ver anúncio original"; `#<id>` |
| `property-map.tsx:6,10` | **Importa `Property`**; `money` | Tipo novo; `formatBRL` |
| `property-map.tsx:29,144,149` | Ativo, reconciliação | Mantidos |
| `property-map.tsx:75` | `maxBounds` | Limite usado na validação |
| `property-map.tsx:153-169` | Marcadores (`:157,158,160,166`) | Classe fixa; só com coordenadas |
| `property-map.tsx:171-174` | `fitBounds` | Protegido |
| `property-map.tsx:187-188,191` | Texto, legenda, `aria-label` | Sem legenda; "anunciados" |
| `property-map.tsx:192-201` | Overlay (`:195,196,198`), carregamento | `<a href="#id">` → botão `onOpenDetails`; estado vazio |
| `globals.css:128-130` | Classes por anunciante | `.alugai-map-marker--agency` |
| `lib/properties.ts:1-20,22-74,76-86` | Tipo, dados, filtros | Removido; filtros movidos |
| `eslint.config.mjs:8-16` | Ignorados | + `.venv/**`, `data/**`, `test-results/**`, `playwright-report/**` (fase 0) |
| `tsconfig.json:42-45` | `exclude` | + `.venv`, `data` (fase 0) |
| `package.json:9,11` | `dev`, `start` | `-H 127.0.0.1`; novos `test:e2e`, `test:live` |
| `README.md:9,14,60,88` | Funcionalidades, `lib/properties.ts`, variáveis | Atualizados |

**Importadores de `lib/properties`, por busca:** `page.tsx:9`, `property-card.tsx:5`, `property-details-dialog.tsx:5`, `property-map.tsx:6`. Citam sem importar: `README.md:60`, `CLAUDE.md:28`. `CLAUDE.md` não é rastreado nem editado (P16). `components/ui/` não muda.

---

## 8. Regras gerais

**Teste primeiro.** Commit `test:` com teste e mínimo para rodar → saída vermelha colada no PR → commit `feat:`/`fix:`. Revisor confere com checkout do commit `test:`.

| Nível | Mínimo do commit | Falha aceita |
|---|---|---|
| Python, CLI | Stub | Asserção ou `NotImplementedError` |
| Schema | Migrações vazias aplicadas | Objeto ausente: `UndefinedTable`/`UndefinedColumn` na consulta do próprio teste, ou asserção sobre tabelas ausentes |
| Navegador | Commit `chore:` anterior: config, seed e servidor sobre a página atual | Asserção de página |
| Fitness | Varredura com stub, em árvore temporária | Asserção |

Falha de coleta, `ImportError` ou servidor que não sobe não valem.

**Controle positivo no navegador.** A página atual mostra dados de exemplo e não lê o banco, então teste só com "não aparece X" passaria sem implementação. Por isso todo spec **primeiro localiza um anúncio pelo título da seed**, ou espera o texto novo; isso falha na página atual. Vale para `T7.4`, `T7.6`, `T7.10`, `T7.30`, `T7.32` e os demais.

**Categorias.** Código copiado com teste trazido é `TRAZIDO`. O que não pode ficar vermelho antes da implementação é **verificação**, listada à parte na seção 10.4: se falhar, é defeito.

**Fim de fase.** `pytest -q -ra` com `0 failed, 0 skipped`; a partir da fase 7, também lint, `tsc`, build, `npm run test:e2e`.

**PRs,** todos para `feat/catalogo-fontes-locais` [USUÁRIO]:

| PR | Fases | Branch |
|---|---|---|
| PR-A | 0, 1, 2 | `feat/catalogo-base` |
| PR-B1 | 3a | `feat/catalogo-amostragem` |
| PR-B2 | 3b, 4 | `feat/catalogo-adaptadores` |
| PR-C | 5, 6 | `feat/catalogo-fotos-revisao` |
| PR-D | 7 | `feat/catalogo-site`, do commit de fim da fase 1; abre depois de PR-A |
| PR-E | 8 | `feat/catalogo-passada-real` |

**Variáveis (`.env.example`).** `ALUGAI_DB_PORT=55432`, `POSTGRES_PASSWORD`, `ALUGAI_DATABASE_URL`, `ALUGAI_TEST_DATABASE_URL`, `ALUGAI_SITE_DATABASE_URL`, `ALUGAI_E2E_ADMIN_DATABASE_URL`, `ALUGAI_E2E_SITE_DATABASE_URL`, `ALUGAI_SITE_DB_PASSWORD`, `ALUGAI_PHOTOS_DIR=data/photos`, `ALUGAI_RETIRADAS_LOG=data/retiradas.log`, `ALUGAI_USER_AGENT=AlugaiCollector/0.1`, `ALUGAI_REVIEWER=`.

**Como as variáveis chegam.** A CLI não lê `.env`: `set -a; . ./.env.example; set +a`. O site lê `.env.local`: `cp .env.example .env.local`, ignorado pelo `.gitignore` (`.env*`).

**Fixtures.** Sintéticas, com URLs `*.example`, em `tests/fixtures/` e `e2e/fixtures/`; HTML com `<!-- SINTETICO -->`. O checklist do PR declara que foram reescritas à mão. Testes usam `tmp_path` para fotos e registro de retiradas, nunca `data/`.

---

## 9. Fases

Testes definidos na seção 10.

### Fase 0: Base

**Objetivo.** Branch, esqueleto Python, Postgres em porta própria, bancos de teste, guardas.

**Pré-requisitos.** Liberação do usuário, P2, Docker.

**Arquivos.** Criar: `tests/test_repo_guard.py`, `tests/conftest.py`, `tests/dbsetup.py`, `docs/decisoes.md`. Trazer/adaptar: `.gitignore`, `.env.example`, `compose.yaml`, `pyproject.toml`, `alugai/__init__.py`, `__main__.py`. Alterar: `eslint.config.mjs`, `tsconfig.json`, `README.md`.

**Passos.**

- `F0.1` Conferir a branch:
  ```bash
  git fetch origin
  git merge-base --is-ancestor 53a68a4 origin/codex/olx-collector   # esperado: exit 0; a branch do Pedro segue ativa e pode avançar (ver 7.0)
  git diff --stat 53a68a4 origin/codex/olx-collector -- .gitignore .env.example compose.yaml pyproject.toml alugai/__init__.py alugai/__main__.py   # esperado: vazio; com diff: reconferir 7.1
  git merge-base --is-ancestor 7d5ac7f origin/main && git diff --stat 7d5ac7f origin/main -- app components lib package.json eslint.config.mjs tsconfig.json
  # esperado: exit 0 e diff vazio; com diff: reconferir 7.2
  # O código é trazido direto da branch; a cópia temporária usada no planejamento não é necessária.
  git grep -n canonical_url 53a68a4 -- alugai/network.py  # esperado: linhas 8, 80, 109
  ```
- `F0.2` `git switch -c feat/catalogo-base feat/catalogo-fontes-locais`; a branch de integração já foi publicada com este plano.
- `F0.3` `T0.*` vermelhos, salvo `T0.6`. `F0.4` Trazer com crédito. `F0.5` `compose.yaml:9` → `"127.0.0.1:${ALUGAI_DB_PORT:-55432}:5432"`. `F0.6` Ignorados em eslint e tsconfig.

**Contratos.** `tests.dbsetup.ensure_database(url)`: cria se ausente; recusa sem `_test`.

**Teste primeiro.** `T0.1`-`T0.5`, `T0.7`. Verificação: `T0.6`.

**Verificação.**

```bash
npm ci                                    # dependências do site, para o lint
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
set -a; . ./.env.example; set +a
docker compose up -d --wait db            # esperado: healthy
docker compose ps db                      # esperado: 127.0.0.1:55432->5432
.venv/bin/python -c "import psycopg, sqlalchemy, alembic, defusedxml" # esperado: sem erro
.venv/bin/pytest -q -ra tests/test_repo_guard.py  # esperado: 0 failed, 0 skipped
mkdir -p .venv/__probe && echo 'const =' > .venv/__probe/x.js; npm run lint; code=$?; rm -r .venv/__probe; test "$code" -eq 0
git check-ignore data/x .venv/x test-results/x   # esperado: as três linhas
```

**Riscos e rollback.** Rollback: apagar branch.

**Fora.** Tabelas, rede, site. **PR.** PR-A.

### Fase 1: Banco

**Objetivo.** Seção 3, com publicação provada. **Pré-requisitos.** Fase 0.

**Arquivos.** Criar: `alembic.ini`, `migrations/env.py`, `script.py.mako`, `versions/0001_tables.py`, `0002_views_role.py`, `alugai/domain.py`, `alugai/db/{__init__,engine,tables}.py`, `tests/factories.py`, `tests/test_schema.py`, `test_publication.py`, `test_enums_contract.py`.

**Passos.** Migrações vazias → `T1.*` vermelhos, salvo `T1.2` → `0001` → `0002` → `tables.py` com `include_object` ignorando views → `domain.py`.

**Contratos.** `StrEnum` para cada CHECK; constantes da seção 15; `new_public_id() -> str`.

**Teste primeiro.** `T1.1`, `T1.3`-`T1.18`. Verificação: `T1.2`.

**Verificação.**

```bash
.venv/bin/alembic upgrade head       # esperado: 0001, 0002
.venv/bin/alembic check              # esperado: "No new upgrade operations detected."
docker compose exec db psql -U alugai -d alugai -c '\dv'  # esperado: 4 views
.venv/bin/pytest -q -ra tests/test_schema.py tests/test_publication.py tests/test_enums_contract.py
```

**Riscos e rollback.** `alembic check` só vê colunas e tipos, e pode reclamar do índice parcial; ajustar `include_object`. Rollback: `alembic downgrade base`, sem dado real ainda.

**Fora.** Escrita pelo coletor. **PR.** PR-A. **Daqui a fase 7 pode começar.**

### Fase 2: Obtenção

**Objetivo.** Transporte, sitemap e trava, só com simulação. **Nenhuma requisição real.** **Pré-requisitos.** Fase 1.

**Arquivos.** Adaptar `alugai/network.py`. Criar: `errors.py`, `sitemap.py`, `sources.py`, `cli.py`, `config/sources.toml` (sem fontes reais nesta fase; entram na fase 3a, públicas conforme U21 = A), `tests/test_network.py`, `test_sitemap.py`, `test_sources.py`, `test_cli_sources.py`, `tests/e2e/test_obtain_flow.py`.

**Passos.** Portar testes do `Fetcher` com stub → `HostPolicy` → 3 entradas → sitemap → `open_fetcher` → comandos.

**Contratos.**

```python
@dataclass(frozen=True)
class HostPolicy:
    page_hosts: frozenset[str]; photo_hosts: frozenset[str]; robots_waived: frozenset[str]
    @classmethod
    def for_source(cls, source, extra_robots_hosts=()) -> "HostPolicy"
    def check(self, url: str, kind: Literal["page","photo","robots"]) -> None  # OffPolicy

class Fetcher:
    def __init__(self, policy, user_agent="AlugaiCollector/0.1", delay=5.0, client=None, sleep=time.sleep)
    def get_html(self, url) -> tuple[str, str]
    def get_xml(self, url) -> tuple[bytes, str]
    def get_image(self, url) -> FetchedImage
    def check_robots(self, host) -> RobotsResult

# errors.py: FetchError, Blocked(FetchError), RobotsUnavailable(Blocked), DisallowedByRobots(FetchError),
#            Missing(FetchError), OffPolicy(FetchError), LayoutError(ValueError), CollectionRefused(RuntimeError)

@dataclass(frozen=True)
class SitemapEntry: url: str; lastmod: datetime | None
@dataclass(frozen=True)
class Discovery: entries: list[SitemapEntry]; complete: bool; errors: list[str]
def discover(fetcher, sitemap_urls, keep_sitemap=lambda _: True, max_sitemaps=None, on_fetch=lambda info: None) -> Discovery
# on_fetch: chamado a cada sitemap (url, final_url, status, sha256, erro); sampling e pipeline gravam a captura kind='sitemap'
def assert_collectable(source) -> None
def open_fetcher(source, **kwargs) -> Fetcher
```

```
alugai source sync config/sources.toml
alugai source list
alugai source terms <slug> --result {allowed,silent,prohibited,not_found} --by <quem> [--url <url>]
alugai source set-status <slug> {candidate,approved,suspended,removed}
alugai source unblock <slug>
alugai source waive-robots <slug> <host> --by <quem> --reason <motivo>
alugai source notice <slug> --at <data>
alugai runs
```

`source terms prohibited` em fonte `approved` recusa, mandando suspender antes.

**Teste primeiro.** `T2.1`-`T2.42`.

**Verificação.**

```bash
.venv/bin/pytest -q -ra tests/test_network.py tests/test_sitemap.py tests/test_sources.py tests/test_cli_sources.py tests/e2e/test_obtain_flow.py
.venv/bin/alugai source list    # esperado: JSON
grep -rn "olx\|SEED" tests/test_network.py   # esperado: sem saída
```

**Riscos e rollback.** Marcadores amplos (`network.py:75`) e exigência de `user-agent:` (`network.py:88`) falham fechado; a amostra mede. Rollback: `git revert`.

**Fora.** Sites reais, adaptadores. **PR.** PR-A.

### Fase 3: Amostragem e adaptadores

**Objetivo.** Termos, até 5 anúncios por site pelo `Fetcher`, go/no-go, adaptadores. **Pré-requisitos.** PR-A; para requisições reais, PR-B1 integrado e U21 decidido.

**Arquivos.** Criar: `alugai/sampling.py`, `values.py`, `retiradas.py`, `adapters/{__init__,base,code49,procasa,gvb,habitamax}.py` (cada adaptador só se o site passar), `tests/test_sampling.py`, `test_values.py`, `tests/adapters/test_contract.py`, `tests/fixtures/<adaptador>/*`. Alterar: `config/sources.toml`, `cli.py`. Fora do Git: `data/fontes-matriz.md`.

#### 3a. Amostragem (PR-B1)

**Passos.**

1. `T3.1`-`T3.9`, `sampling.py`, `retiradas.py`, integrar PR-B1.
2. Preencher `config/sources.toml` (P5), com `adapter` vazio; `source sync`.
3. **Termos, leitura humana no navegador**, um site por vez: `source terms`. `prohibited` encerra.
4. `alugai sample <slug> ...`, um site por vez; parar em bloqueio.
5. Ler amostras sem rede; `alugai sample <slug> --robots-host <host>`.
6. Preencher a matriz.

```
alugai sample <slug> [--limit 5] [--max-sitemaps 3] [--sitemap-include <regex>] [--url-include <regex>] [--url-exclude <regex>] [--url <url> ...]
alugai sample <slug> --robots-host <host>
alugai purge [--samples]
```

```python
# retiradas.py: caminho sempre por parâmetro; a CLI lê ALUGAI_RETIRADAS_LOG
def append(path, action, source_slug, external_id, source_url, by, reason) -> None
def withdrawn(path, source_slug) -> Withdrawn   # .external_ids, .urls; linha ilegível levanta erro
```

Filtros ficam em `counters`. A Procasa exige `--sitemap-include` e `--url-exclude` [FATO 00, 01]. Seleção determinística: agrupa pelos dois primeiros segmentos, com dígitos normalizados, e faz rodízio. Não grava em `listings`.

**Matriz, só estrutura.** robots; codificação; HTML bruto traz dados; JSON-LD; `__NEXT_DATA__`; ID estável; aluguel e rótulo; página mista; condomínio; IPTU e período; pet; bairro; rua; cidade; CRECI; coordenadas e precisão; tipo; tipo na URL; fotos e host; robots do host; sinal de indisponível; âncoras do preço; blocos de outros anúncios; falsos positivos de `check_block`.

**Pontos de decisão, nunca presumidos.**

| Id | Pergunta | Se falhar |
|---|---|---|
| PD1 | Termos permitem? | Sai; entra reserva |
| PD2 | HTML bruto traz aluguel, rótulo e bairro (limiar na seção 15)? | Sai; entra reserva [USUÁRIO] |
| PD3 | ID estável na URL? | Só no HTML: decisão no checkpoint da amostra. Nenhum: sai |
| PD4 | Página mista separa preços com rótulo? | Rejeitada; site sai se for a maioria |
| PD5 | Um adaptador serve aos 3 Code 49? | Parâmetros; senão, separado |
| PD6 | Host de fotos e robots? | Sem robots: sem fotos ou `waive-robots`; com `Disallow`: sem fotos |
| PD7 | Coordenadas e IPTU com período | Registrar; sem geocodificar [01 §8] |
| PD8 | Volume: URLs × taxa da amostra | Abaixo do alvo: reservas na ordem Casa Manaus, Imóveis Manaus, Manaus Administradora, Lopes |
| PD9 | Cidade explícita? | Padrão só se o site for só de Manaus; senão, rejeita |
| PD10 | URL classifica aluguel e tipo? | Baixar e memorizar; refazer orçamento |
| PD11 | Âncora estrutural do preço? | Sem ela, vale só D21; decisão registrada |

**Checkpoint da amostra.** Parar e apresentar matriz, projeção e reservas.

#### 3b. Valores e adaptadores (PR-B2)

```python
# values.py
def money(value) -> Decimal | None
def parse_rent(text, *, label=None, title=None) -> ParsedRent
def parse_fee(text, label) -> ParsedFee       # isento/incluso: amount None
def parse_iptu(text) -> ParsedIptu
def exact_number(text) -> Decimal | None
def exact_count(text) -> int | None
def parse_pet(text) -> PetPolicy

# adapters/base.py
@dataclass(frozen=True)
class UrlInfo: kind: Literal["rental","mixed","other"]; external_id: str | None
@dataclass
class RawListing:
    external_id: str; source_url: str; source_title: str | None; transaction_label: str | None
    rent_text: str | None; condo_text: str | None; iptu_text: str | None; property_type_text: str | None
    bedrooms_text: str | None; bathrooms_text: str | None; parking_text: str | None
    area_text: str | None; pet_text: str | None
    city: str | None; neighborhood: str | None; street: str | None
    latitude: str | None; longitude: str | None; location_exact: bool  # True só se a fonte declarar
    advertiser_name: str | None; creci: str | None
    photo_urls: list[str]; evidence: dict
@dataclass(frozen=True)
class NotFound: reason: str
class Adapter(Protocol):
    name: str; version: str             # sobe em toda mudança que afete a extração
    def keep_sitemap(self, sitemap_url: str) -> bool: ...
    def classify_url(self, url: str) -> UrlInfo: ...
    def parse(self, html: str, final_url: str, requested_url: str) -> RawListing | NotFound: ...
```

Cada adaptador declara **âncoras estruturais** (bloco de preço, título). Ausente: `LayoutError`. Presente sem valor: `rent_text` traz o texto ou `None`, e a validação decide. Adaptador é puro; sem busca recursiva em JSON (`parser.py:119`).

**Passos.** `T3.10`-`T3.17` e `values.py` → por adaptador: fixtures à mão, contrato vermelho, implementação → PD5 → `purge --samples` → `adapter` no TOML.

**Teste primeiro.** `T3.1`-`T3.22`.

**Verificação.**

```bash
.venv/bin/alugai sample <slug> --limit 5    # só após PR-B1 e termos
git status --porcelain data/                # esperado: vazio
.venv/bin/pytest -q -ra tests/test_values.py tests/test_sampling.py tests/adapters/ tests/test_repo_guard.py
```

**Riscos e rollback.** Amostra pequena não prova adaptador; D21 e piloto mitigam. Amostra expira em 30 dias (C12). Rollback: `purge --samples`, `git revert`; fonte reprovada vai a `removed`.

**Fora.** Escrita em `listings`. **PR.** PR-B1; PR-B2.

### Fase 4: Validação

**Objetivo.** `RawListing` em dado válido ou rejeição rastreável; transições; gravação. **Pré-requisitos.** Fases 1, 2, 3b. Adaptador falso e `MockTransport`; aprovações por `tests/factories.py`, porque `review apply` é da fase 6.

**Arquivos.** Criar: `alugai/validation.py`, `hashing.py`, `lifecycle.py`, `pipeline.py`, `config/neighborhoods.csv`, `tests/test_validation.py`, `test_hashing.py`, `test_lifecycle.py`, `test_pipeline.py`, `test_neighborhoods.py`, `tests/e2e/test_collect_cycle.py`. Alterar: `cli.py`.

**Regras.**

| Condição | Resultado | Motivo |
|---|---|---|
| Sem preço; "Sob consulta"; zero | Rejeita | `rent_missing`, `rent_on_request`, `rent_zero` |
| "A partir de"; dia, temporada, diária | Rejeita | `rent_from_price`, `rent_short_term` |
| Sem rótulo de locação nem "/mês"; só venda | Rejeita | `rent_unclear`, `sale_only` |
| Não residencial; tipo não identificado | Rejeita | `non_residential`, `property_type_unknown` |
| Outra cidade; sem título; sem bairro; URL fora de HTTPS | Rejeita | `city_not_manaus`, `title_missing`, `neighborhood_missing`, `url_invalid` |
| Bairro não reconhecido | Aceita, alerta | `neighborhood_unknown` |
| Telefone no título | Aceita, **alerta bloqueante** | `title_has_phone` |
| "venda/vendo" no título; valor implausível; página mista; presumido | Aceita, alerta | `transaction_title_conflict`, `rent_implausible`, `mixed_sale_rent`, `rent_assumed_monthly` |
| Taxa simbólica | Aceita, `needs_review` | `condo_needs_review`, `iptu_needs_review` |
| Contagem > 100; coordenada fora de `property-map.tsx:75` | Aceita, campo nulo, alerta | `count_implausible`, `coords_out_of_bounds` |
| Rua com aparente nº de apartamento | Aceita, remove trecho, alerta | `street_sanitized` |

Coordenada presente: `approximate`, ou `exact` com `location_exact`. Ausente: `none`.

Tipos: apartamento, flat, cobertura → `apartment`; casa, sobrado → `house`; casa em condomínio → `condo_house`; kitnet; studio; quarto → `room`; galpão, sala, loja, terreno, ponto, prédio, sítio, chácara → `other` (U3).

**Contratos.**

```python
def validate(raw, *, neighborhoods) -> Accepted | Rejected
def content_hash(listing, photo_hashes) -> str
# JSON canônico: chaves ordenadas, Decimal 2 casas, coordenadas 6, texto NFC sem espaço duplicado,
# hashes ordenados. Campos do 01 §3.
# lifecycle.py
def observe_valid(db, row, normalized, photo_hashes, hash, *, capture, now) -> ChangeResult
def observe_invalid(db, row, reasons, *, capture, now) -> None
def observe_missing(db, row, *, capture, run_id, now) -> None
def mark_sitemap_absent(db, row, *, now) -> None
def mark_seen(db, listing_id, now) -> None
# pipeline.py
def collect(db, source, fetcher, adapter, *, limit=None, accept: MassChangeAcceptance | None = None,
            retiradas_path, now=utcnow) -> RunResult
```

```
alugai collect <slug> [--limit N] [--accept-mass-change --by <quem> --reason <motivo>]
alugai neighborhood load config/neighborhoods.csv
```

**Bairros.** Colunas `slug,name,aliases,zone,near_ufam,near_uea,near_pim,source_note`. Upsert por `slug`; slug com anúncio ligado não é removido; religa `neighborhood_id` sem mudar o hash; CSV vazio recusado. **Nenhum bairro é preenchido por este plano.** Na fase 4 os testes usam CSV temporário, e o arquivo versionado nasce só com o cabeçalho; o conteúdo real segue U7, e a coluna `near_uea` depende da unidade indicada em P17.

**Erro no item.** `IntegrityError`/`DataError`: rollback, `internal_error`, D21, `partial`. `OperationalError`: `failed`.

**Teste primeiro.** `T4.1`-`T4.59`.

**Verificação.**

```bash
.venv/bin/pytest -q -ra tests/test_validation.py tests/test_hashing.py tests/test_lifecycle.py tests/test_pipeline.py tests/test_neighborhoods.py tests/e2e/test_collect_cycle.py
```

**Riscos e rollback.** Defeito de adaptador tira anúncios do site conforme a tabela da seção 5.3. Rollback: `git revert`, `alembic downgrade`, sem dado real ainda.

**Fora.** Fotos (hash com lista vazia), aprovação por comando. **PR.** PR-B2.

### Fase 5: Fotos

**Objetivo.** Seções 5.4 e 5.5. **Pré-requisitos.** Fase 4.

**Arquivos.** Criar: `alugai/photos.py`, `tests/test_photos.py`. Alterar: `pipeline.py`, `cli.py`.

**Contratos.**

```python
def fetch_new_photos(fetcher, row, urls, *, photos_dir) -> PhotoPlan        # URLs sem linha
def fetch_missing_files(fetcher, row, plan, *, photos_dir) -> PhotoPlan     # pending, deleted, failed selecionadas
def apply_photo_plan(db, listing_id, plan) -> list[str]                     # só banco; zera e reatribui posições
def delete_listing_photos(db, listing_id, *, photos_dir) -> int             # banco primeiro
def mark_photos_pending(db, listing_id) -> int                              # só position NOT NULL; sem rede
def reconcile(db, *, photos_dir, allow_empty_db=False) -> ReconcileResult
```

```
alugai purge [--samples] [--all]
```

`purge` chama `reconcile`, sob trava, e só apaga caminhos no padrão `<public_id>/<sha256>.<ext>`. Com banco vazio e pasta com arquivos, exige `--all`.

**Consequências.** Foto nova baixada muda o hash, e o anúncio sai até revisão. Foto nova que falha não entra nem é servida; quando baixar, o hash muda. Rotação de URL com os mesmos bytes não muda nada para o usuário.

**Teste primeiro.** `T5.1`-`T5.25`. Os testes percorrem `collect` com fotos, sem criar linhas à mão, para ficarem vermelhos enquanto o código de fotos não existir.

**Verificação.**

```bash
.venv/bin/pytest -q -ra tests/test_photos.py
git check-ignore data/photos/x.jpg
```

**Riscos e rollback.** Primeira passada longa. Rollback: `git revert`.

**Fora.** Marca d'água (nunca removida), redimensionamento, serving. **PR.** PR-C.

### Fase 6: Revisão

**Objetivo.** Decidir com rastreio, medindo tempo e rejeições. **Pré-requisitos.** Fases 4 e 5; U20 decidido.

**Arquivos.** Criar: `alugai/review.py`, `report.py`, `tests/test_review.py`, `test_report.py`, `tests/e2e/test_review_cycle.py`. Alterar: `cli.py`.

**Interfaces.**

```
alugai review build [--source <slug>] [--output data/review] [--discard]
alugai review apply data/review/decisoes.txt --by <revisor>
alugai review approve-batch --by <revisor>
alugai reopen <public_id> --reason <motivo> --by <revisor>
alugai withdraw <public_id> --reason <motivo> --by <revisor>
alugai restore <public_id> --reason <motivo> --by <revisor>
alugai report [--source <slug>]
```

**Sessão.**

- `review build` abre `collection_runs(mode='review')`. Com sessão aberta, recusa, salvo `--discard`: status `discarded`, e o arquivo vira `decisoes-<run_id>.descartado.txt`.
- `decisoes.txt` começa com `# sessao: <run_id>`. `review apply` exige a sessão aberta.
- Sintaxe validada **antes** de gravar: erro aborta sem efeito, e a sessão segue aberta.
- Sintaxe válida: aplica linha a linha conforme a seção 4.1, lista recusas, fecha a sessão como `success` e renomeia para `decisoes-<run_id>.aplicado.txt`.

```
# sessao: 123
? <public_id> <hash12>            # título; ignorado
a <public_id> <hash12>
r <public_id> <hash12> motivo livre
a <public_id> <hash12> condo=reported:300.00 iptu=reported:1200.00:annual
a <public_id> <hash12> condo=exempt iptu=unknown
```

**Relatório.** HTML estático, com `html.escape`, sem JavaScript: dados, alertas, evidência, fotos por caminho relativo, link, diferença contra a última versão aprovada, duplicados, o que falta para aprovar.

**`alugai report`.** Por fonte e motivo: rejeições; `versoes_novas`, `invalidos_novos`, `indisponiveis_novos`; `aprovados`, `possiveis_duplicados`; totais calculados. Em `revisao`: tempo.

**Tempo.** Soma das sessões `success` / decisões; total, não por fonte; pausas contam.

**Lote.** Exige última decisão `approved` com hash diferente do atual; nenhum alerta bloqueante; condições da 4.1. **Copia `resolved_*` da decisão anterior**, e o resultado segue a condição de `needs_review`. `reopened` nunca passa. Colunas iguais (mudança de canonizador, D23) sempre passam; preço, taxas, tipo e fotos nunca. **Mudança em título, anunciante ou CRECI não passa em lote (U20): vai para revisão individual.** O lote só aceita mudança sem nada visível, então alertas não bloqueantes não têm efeito próprio nele.

**Teste primeiro.** `T6.1`-`T6.25`.

**Verificação.**

```bash
.venv/bin/pytest -q -ra tests/test_review.py tests/test_report.py tests/e2e/test_review_cycle.py
.venv/bin/alugai report      # esperado: JSON com "por_fonte" e "revisao"
```

**Riscos e rollback.** Decisão errada se desfaz com `reopen`. Rollback: `git revert`.

**Fora.** Tela de administração, múltiplos revisores, edição de título. **PR.** PR-C.

### Fase 7: Site

**Objetivo.** Ler as views, com a apresentação do 00 e do 01. **Pré-requisitos.** Fase 1; paralela às fases 2 a 6, com dados sintéticos.

**Arquivos.** Criar: `lib/catalog/{types,db,queries,map-row,format,filters}.ts`, `components/home-client.tsx` (via `git mv app/page.tsx`), `app/page.tsx`, `app/error.tsx`, `app/fotos/[publicId]/[position]/route.ts`, `playwright.config.ts`, `e2e/fixtures/{seed.sql,photos/*}`, `e2e/helpers/db.ts`, `e2e/global-setup.ts`, `e2e/unit/*.spec.ts`, `e2e/{contract,catalog,details,filters,map,shared-link,photos,copy,db-down}.spec.ts`. Alterar e remover: seção 7.2.

**Privacidade.** A documentação do Next informa padrão `0.0.0.0`; os scripts usam `127.0.0.1`. Operador não usa `npx next` direto.

**Rota de fotos.**

```ts
export async function GET(_req: Request, { params }: { params: Promise<{ publicId: string; position: string }> })
```

Valida formato e faixa antes de consultar; consulta parametrizada; caminho resolvido permanece na pasta; `ENOENT` → 404; banco fora → 503.

**Banco indisponível.** `getPublishedListings` não engole erro; `app/error.tsx` mostra "Catálogo temporariamente indisponível".

**Execução dos testes.** `playwright.config.ts` com `workers: 1`, `testDir: "e2e"`, servidores `next start -H 127.0.0.1 -p 3100` (`ALUGAI_E2E_SITE_DATABASE_URL`) e `-p 3101` (porta inválida). `global-setup` chama `tests/dbsetup.py` e migra. `beforeEach` chama `resetSeed()`. Tiles do OpenStreetMap interceptados. Conferência real em `e2e-live/`, com config própria.

**Teste primeiro.** `T7.1`-`T7.34`, com controle positivo (seção 8).

**Verificação.**

```bash
npm install pg && npm install -D @types/pg @playwright/test
npx playwright install chromium
set -a; . ./.env.example; set +a
npm run lint && npx next typegen && npx tsc --noEmit
npm run build                       # esperado: exit 0, sem banco; "/" marcada ƒ
npm run test:e2e                    # esperado: 0 failed, 0 skipped
grep -rn "wa.me\|lib/properties\|Disponível hoje" app components lib # esperado: sem saída
```

**Riscos e rollback.** Refatoração grande em `page.tsx`. `content-visibility` (`property-card.tsx:36`) pode interferir em rolagem. Rollback: `git revert` de PR-D.

**Fora.** Hospedagem, autenticação, geocodificação, favoritos persistentes, formulário, SEO. **PR.** PR-D.

### Fase 8: Passada real

**Objetivo.** Primeiro um site, depois os seis. **Pré-requisitos.** Fases 0 a 7 integradas; checkpoints resolvidos; bairros carregados; `.env.local` criado.

**Arquivos.** Alterar: `docs/coletor.md` (operação e seções 5.8, 5.9), `config/sources.toml`, `README.md`. Criar: `tests/e2e/cycle_driver.py`, `tests/test_cycle_driver_offline.py`, `e2e/cycle.spec.ts`, `e2e-live/live.spec.ts`, `playwright.live.config.ts`. Local: `data/resultado-passada.md`. Código de produção só em correção com teste novo.

**Contratos.** Nenhum novo. Hash congelado (D23).

**Passos.**

1. **Pré-voo:** `T8.1`, suíte completa.
2. **Piloto: Ponta Negra** (58 URLs, 13 estimados), com `status=candidate`. `alugai collect ponta_negra --limit 5`; conferir à mão. Corrigiu o adaptador: subir `version` e repetir com `--limit 5`, que relê os mesmos cinco. Se parar por `layout_stop` numa correção conferida: `source unblock` e `--accept-mass-change`. Depois, sem limite.
3. `review build`, revisão, `review apply`, `source set-status ponta_negra approved`. Conferir com `npm run build && npm run start`.
4. **Portão do piloto:** o usuário vê `alugai report` e o site, e autoriza.
5. Demais, em ordem crescente de URLs: S C Jardim, Habitanorte, Habitamax, Procasa, GVB; cada um com `--limit 5` antes.
6. Abaixo do alvo: reservas (PD8), por toda a fase 3. **Sem relaxar validação.**
7. **Segunda passada ~7 dias depois:** mede `lastmod`, mudanças, sumiços, custo de revisão repetida.
8. Agregados em `data/resultado-passada.md`.

**Orçamento (primeira passada, tetos).**

| Site | URLs | Observação |
|---|---|---|
| Procasa | 211 + ~111 sub-sitemaps [FATO] | Baixa 211, não os ~77 residenciais, salvo tipo na URL |
| Habitanorte / Ponta Negra / S C Jardim | ≤ 179 / ≤ 58 / ≤ 28 | Total do sitemap |
| GVB | ≤ 978 | Depende de PD10 |
| Habitamax | ≤ 182 | Sem `lastmod`: baixa sempre |

Teto ~1.636 páginas × 5 s ≈ 2 h 16 min; sem o teto da GVB, ~658 ≈ 55 min. Fotos: ~1.090 × 5 s ≈ 1,5 h. `Crawl-delay` maior aumenta. Passadas seguintes caem pelo pulo.

**Teste primeiro.** `T8.3`. Verificações: `T8.1`, `T8.2`. Falha real vira teste vermelho antes do conserto.

**Verificação.** Seção 13, e:

```bash
.venv/bin/alugai runs
.venv/bin/alugai report
git status --porcelain | grep -E '^.. data/' # esperado: sem saída
git ls-files | grep -E '\.(jpe?g|png|webp)$' | grep -v '^e2e/fixtures/photos/' # esperado: sem saída
```

**Riscos e rollback.**

- Bloqueio: parar, **não contornar**; `unblock` só depois de entender a causa.
- `layout_stop`: conferir capturas antes de desbloquear; defeito: nova `version`; mudança real: `unblock` e `--accept-mass-change`.
- Dados ruins de uma fonte: seção 5.9, nunca o atalho `approved`.
- Perda do banco: seção 5.8. Não há restauração por backup.

**Fora.** Integração na `main`, hospedagem, aviso às imobiliárias, agendamento. **PR.** PR-E. A integração na `main` depende de Miguel e Pedro [USUÁRIO].

---

## 10. Lista de teste-primeiro (para aprovação no checkpoint)

Fonte única; IDs usados no restante do documento. Cada teste está na fase em que pode passar. Resumo e contagem:

| Categoria | F0 | F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 | Total |
|---|---|---|---|---|---|---|---|---|---|---|
| 10.1 Trazidos | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | 2 |
| 10.2 Reescritos | 0 | 0 | 8 | 1 | 2 | 0 | 2 | 0 | 0 | 13 |
| 10.3 Novos | 6 | 17 | 34 | 19 | 57 | 25 | 23 | 34 | 1 | 216 |
| 10.4 Verificações | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 4 |
| **Total** | 7 | 18 | 42 | 22 | 59 | 25 | 25 | 34 | 3 | **235** |

### 10.1 Já têm teste, trazidos (`TRAZIDO`, sem vermelho)

Mesmo comportamento; só o import é ajustado.

- `T3.18` `test_money`, `test_ambiguous_money_rejected` (`test_collector.py:38-47`)
- `T3.19` Não exatos: `5+`, `5 ou mais`, `61 - 62 m²` (`test_cards.py:80-82`)

### 10.2 Já têm teste, reescritos (vermelhos até adaptar)

URLs `https://fonte.example`; sem `SEED`, `collector`, `store`.

| Id | Teste | Origem em `test_collector.py`, salvo nota |
|---|---|---|
| `T2.2` | Robots com curinga: `DisallowedByRobots` antes da página | `:105-113` |
| `T2.3` | 401/403/429 sem nova tentativa | `:116-126` |
| `T2.4` | Bloqueio com compressão corrompida | `:129-134` |
| `T2.5` | `Crawl-delay` | `:137-145` |
| `T2.6` | HTML comprimido decodificado uma vez | `:148-154` |
| `T2.7` | Robots 404/500/302 em host de páginas bloqueia | `:157-160` |
| `T2.8` | Redirecionamento reconfere robots | `:163-172` |
| `T2.9` | Redirecionamento externo: `OffPolicy` | `:175-181` |
| `T3.11` | Venda + locação pega o preço certo | `test_cards.py:61-68` |
| `T4.21` | 404 em 2 verificações separadas | `:97-100` |
| `T4.27` | Falha não muda dados nem `last_seen_at` | `:89-96` |
| `T6.1` | Relatório escapa HTML | `test_cards.py:107-110` |
| `T6.14` | Duplicado alerta, nunca mescla | `test_cards.py:113-118` |

### 10.3 Precisam de teste novo

**Fase 0.**
- `T0.1` `scan_tracked` acusa `data/`, `.env`, `.venv/`, HTML fora de fixtures.
- `T0.2` `scan_forbidden` acusa `playwright`, `selenium`, `firecrawl`, `/_int/`, `olx.com.br`, `vivareal` em `alugai/`.
- `T0.3` `.env.example` sem Firecrawl.
- `T0.4` Compose com porta configurável e `127.0.0.1`.
- `T0.5` Recusa banco sem `_test`.
- `T0.7` `ensure_database` cria e é idempotente.

**Fase 1** (banco real).
- `T1.1` up-down-up em `alugai_mig_test`: tabelas existem depois de `up` e somem depois de `down`.
- `T1.3` `StrEnum` = CHECK.
- `T1.4` Dinheiro `numeric`, datas `timestamptz`.
- `T1.5` Identidade e `public_id`.
- `T1.6` Constraints: `parking=0` passa; negativo, lat sem lng, `none` com coordenada, `reported` sem valor, `unknown` com valor, `approved` sem termos, `prohibited` com `approved`, 6ª posição, posição repetida, `..` em caminho, `reason` nulo em rejeição, hash inválido, valor inválido nos CHECKs de versão falham.
- `T1.7` Matriz de publicação. Fora: fonte `candidate`/`suspended`/`removed`; sem revisão; hash mudou; `rejected`; `reopened`; `unavailable`; expirado; retirado; inválido; `short_term`; período `unknown`; `other`; `needs_review` em cada taxa; bairro nulo; outra cidade. Dentro: `verifying`, fonte `blocked`.
- `T1.8` `monthly_total`: soma; exempt/included = 0; annual ÷ 12; unknown, on_request, IPTU sem período = `NULL`; `assumed_monthly` permite.
- `T1.9` Colunas = lista fechada.
- `T1.10` `alugai_site` lê 3 views; negado em tabelas e `listing_review_state`; `INSERT` negado.
- `T1.11` `listing_public_status`: publicado; indisponível; nunca aprovado e inexistente sem linha.
- `T1.12` `published_listing_photos`: só publicado, `stored`, com posição; `photo_positions` ordenado.
- `T1.13` `1000/12 = 83.33`.
- `T1.14` Derivação: rejeitado + hash novo = pendente; A→B→A aprovado; A aprovado → B rejeitado → A pendente; desempate por `id`.
- `T1.15` Correção com mesmo hash, inclusive `resolved_iptu_period`; não com hash novo.
- `T1.16` `neighborhood_id` não altera revisão.
- `T1.17` `new_public_id`.
- `T1.18` Foto `stored` com `sha256` fora de `photo_hashes` não é servida.

**Fase 2.**
- `T2.1` `get_html` fora da OLX (hoje `ValueError` [FATO]).
- `T2.10` `www` dentro da política, com `final_url`.
- `T2.11` Host fora, sem requisição.
- `T2.12` `get_xml`: `application/xml`, `text/xml`.
- `T2.13` XML gzip.
- `T2.14` Limite de descompressão.
- `T2.15` `get_image` com assinatura.
- `T2.16` HTML sem marcador no lugar de imagem ou XML: `FetchError`.
- `T2.17` Corpo binário não varrido.
- `T2.18` Host de foto listado.
- `T2.19` Robots ausente em foto: `RobotsUnavailable`.
- `T2.20` `waive-robots` libera robots ausente; `Disallow` depois prevalece.
- `T2.21` Intervalo por origem.
- `T2.22` Codificação por cabeçalho e meta.
- `T2.23` User-Agent sem `@`.
- `T2.24` Sitemap: `urlset`, índice, `lastmod`, `<loc>` relativo; fora da política descartado (defeito 9).
- `T2.25` Bloqueio grava só `collection_state`.
- `T2.26` Entidade externa falha.
- `T2.27` Falha parcial: `complete=False`.
- `T2.28` Sitemap vazio: `LayoutError`.
- `T2.29` `keep_sitemap`, `max_sitemaps` reduzem requisições.
- `T2.30` `open_fetcher` recusa: termos nulos, `prohibited`, `suspended`, `removed`, `blocked`.
- `T2.31` Aceita: `candidate`, `approved`, `not_found`, `silent`.
- `T2.32` `source terms` grava autor; `set-status approved` sem termos falha; `terms prohibited` em aprovada recusa com mensagem.
- `T2.33` E2E: robots + índice + subsitemap, com `on_fetch` chamado para cada sitemap. A gravação de `kind='sitemap'` é conferida em `T3.4` e `T4.47`.
- `T2.34` `HostPolicy` recusa `http://`, porta 8443, credenciais, em URL inicial, `Location`, `<loc>`, foto.
- `T2.35` `MAX_RESPONSE_BYTES`.
- `T2.36` Piso de 2 s.
- `T2.37` Falha de robots em cache: N fotos, 1 pedido.
- `T2.38` `source sync` idempotente; `unblock`, `waive-robots`, `notice`, `runs`.
- `T2.39` `Fetcher(` só em `open_fetcher`, por AST.
- `T2.40` `source sync` aceita `adapter` vazio.
- `T2.41` Desafio 200 em HTML, com marcador, em `get_image` e `get_xml`: `Blocked`.
- `T2.42` `Disallow` em `get_html` e `get_image`: `DisallowedByRobots`, não `Blocked`.

**Fase 3.**
- `T3.1` Fixtures: marcador em `.html`; telefone e domínios do TOML proibidos, em `tests/fixtures/` e `e2e/fixtures/`.
- `T3.2` `sample`: `limit`; recusa por trava.
- `T3.3` `sample`: para no bloqueio.
- `T3.4` `sample`: só em `data/`, com prazo, sem `listings`; capturas `kind='sitemap'`; `--url` no registro de retiradas recusada; registro ilegível: `failed`.
- `T3.5` Seleção determinística, rodízio.
- `T3.6` Filtros reduzem requisições: Procasa simulada sem venda nem busca.
- `T3.7` `--robots-host`: só `/robots.txt`; respeita trava; `kind='robots'`; 403 marca `blocked`.
- `T3.8` `purge --samples`; prazo.
- `T3.9` `sample` recusa com trava presa; fecha `running` de `sample`/`collect`; não toca sessão de revisão.
- `T3.10` Defeito 1: "Sob consulta Cond. R$ 300" não vira 300.
- `T3.12` Defeito 2: "A partir de".
- `T3.13` Defeito 3: dia, diárias no título, temporada, noite.
- `T3.14` Períodos: `/mês`, mensal; `label="Locação"` = `assumed_monthly`; sem nada = `unknown`.
- `T3.15` `"1.000 m²"` = 1000; `"45,5 m²"`; `"45.5"`.
- `T3.16` `parse_fee`: dois-pontos, "incluído", "Sob consulta", "a combinar" = `on_request`; isento e incluso com `amount=None`; R$ 1 e R$ 0 = `needs_review`; ausente = `unknown`.
- `T3.17` `parse_iptu`: anual, mensal, parcelas, sem período; `parse_pet`.
- `T3.20` Contrato, todo adaptador: `aluguel_mensal`, `locacao_sem_mes`, `venda_e_aluguel`, `venda_apenas`, `indisponivel_200`, `layout_quebrado`, `ancora_de_preco_ausente`, `com_outros_anuncios`, `foto_relativa`, `sem_campos_opcionais`.
- `T3.21` `classify_url`: `external_id` igual com slug trocado; busca = `other`.
- `T3.22` `source sync` recusa adaptador fora do registro; aceita fonte sem adaptador.

**Fase 4.**
- `T4.1` Toda linha da tabela de validação.
- `T4.2` Defeito 4: "Vendo casa" R$ 350.000 com alertas, ou rejeitado sem locação; "Galpão comercial" rejeitado.
- `T4.3` Rua nunca inferida; nº removido.
- `T4.4` Desconhecido é nulo.
- `T4.5` Hash muda com cada campo do 01 §3; não muda com tempos, `warnings`, `evidence`, `neighborhood_id`, `source_updated_at`, ordem de fotos, espaços.
- `T4.6` Colunas de versão = campos do hash.
- `T4.7` Primeira gravação cria `public_id` e versão.
- `T4.8` `mark_seen`: 30 dias.
- `T4.9` Defeito 5: mesmo hash não cria versão.
- `T4.10` Defeito 5: condomínio ausente, isolado: versão nova `unknown`, anterior preservada, pendente.
- **`T4.11` Seletor quebrado com âncora presente e valor vazio, 9 conhecidos publicados:** para no 5º; exatamente 5 com `invalid_since`, 4 intactos; `layout_stop`, `blocked`, código 2. Correção, nova `version`, `unblock`: os 5 limpam, mesmo hash, de volta à view sem revisão; dados iguais aos originais.
- **`T4.12` Mudança real:** (a) 3 de 9 viram "Sob consulta": gravados na hora, `success`, fora da view. (b) 6 de 9: para no 5º; `unblock`; `--accept-mass-change`: o 6º é gravado, execução `success`, `counters` com `by`, `reason`, contagem; 3 restantes publicados.
- **`T4.13` Piloto, sitemap com 20 URLs:** `--limit 5` com v1 grava 5; v2 lê condomínio não informado, `--limit 5` relê **os mesmos 5**: versão nova `unknown`, pendentes em `listing_review_state`, versão v1 preservada; `layout_stop` no 5º; `unblock` e nova coleta: sem nova degradação, `success`. A prova até a view fica em `T6.25`.
- **`T4.14` Interrupção:** item 1 vira "Sob consulta", item 2 recebe 429: item 1 já fora da view, com `invalid_since`; execução `blocked`.
- **`T4.15` `--limit`:** 2 de 2 degradados: mesmos dados gravados que os da execução sem limite para esses itens; sem parada, por não atingir 5; nenhum atalho além disso.
- `T4.16` Versão nova ignora pulo e memória; reprocessa com hash igual, sem revisão.
- **`T4.17` Estoque:** anúncio já inválido, rejeitado em 20 execuções e em versão nova, não conta; Habitamax simulada não para.
- **`T4.18` Base, ordem e limites:** 100 conhecidos, 10 degradados: não para; 25 de 100: **não para**, `success`, 25 fora da view, contados em `report`; 100 bons depois ruins: para ao chegar a 30%, com ~43 fora; 5 ausentes com `LayoutError`, processados por último com base grande: não para; 5 de 5 em base 5: para; `LayoutError` de anúncio já inválido entra na base, e a proporção nunca passa de 100%.
- **`T4.19` Não encontrado em massa, 9 publicados, site redireciona à home, sem aceite:** 1ª: itens 1-5 com `missing_count=1`, nenhum sai, `layout_stop`. `unblock`, 2ª com intervalo: itens 1-5 `unavailable` na hora, fora da view; `layout_stop` no 5º. `unblock`, 3ª: itens 6-9 com `missing_count=1`, 4 abaixo do mínimo, `success`. 4ª com intervalo: itens 6-9 `unavailable`, `success`. Variante com `--accept-mass-change`: sem parada, `counters` com autor. Volta com mesmo hash, sem revisão.
- `T4.20` Sumiço: `verifying`, consultado na mesma execução, por último.
- `T4.22` 2 verificações na mesma execução contam uma; intervalo mínimo.
- `T4.23` 200 "indisponível".
- `T4.24` Redirecionamento à home.
- `T4.25` Para outro anúncio conta; slug novo com mesmo ID confirma e atualiza `source_url`.
- `T4.26` Bloqueio preserva o site; próximo `collect` recusa.
- `T4.28` Defeito 6: erro isolado não aborta, `success`.
- `T4.29` `LayoutError` em proporção para, sem gravar; repetição para no mesmo ponto; `--accept-mass-change` segue.
- `T4.30` Defeito 8: `unavailable` volta só por página validada.
- `T4.31` `unavailable` com hash novo.
- `T4.32` Expirado renova sem revisão.
- `T4.33` Defeito 8: retirado não é requisitado nem limpo.
- `T4.34` Página vira inválida: sai na hora.
- `T4.35` Volta válida: limpa.
- `T4.36` Sitemap vazio ou incompleto não marca ninguém.
- **`T4.37` Queda real, em dois ciclos:** 1º `partial`, código 2, ninguém marcado; 2º com `--accept-mass-change`: ausentes `verifying`, consultados, 404 contado; `counters` com autor.
- `T4.38` Fora do sitemap, válida: `active`.
- `T4.39` `unavailable` ausente sem requisição.
- `T4.40` Sitemap não renova `last_seen_at`.
- `T4.41` Pulos: 6 dias pula; 7 baixa; sem `lastmod` baixa; memória de rejeição só para URL sem anúncio.
- `T4.42` Rejeitado novo: só captura.
- `T4.43` Defeito 7: rejeições abaixo do limite: `success`, 0.
- `T4.44` HTML bruto: política e prazo.
- `T4.45` `neighborhood load` idempotente; religa sem mudar revisão.
- `T4.46` CSV vazio, zona inválida, apelidos em colisão, slug com anúncio.
- `T4.47` E2E: cria, repete, preço muda, 404 duas vezes; capturas `kind='sitemap'` e `kind='page'`.
- `T4.48` `NETWORK_STOP_CONSECUTIVE`.
- `T4.49` Retirada durante a coleta: gravação descartada.
- `T4.50` `IntegrityError`: rollback, `internal_error`, segue, `partial`.
- `T4.51` `OperationalError`: `failed`.
- `T4.52` `isento` percorre até `listings` sem violar CHECK.
- `T4.53` `collect` com `adapter` nulo recusa, sem requisição.
- `T4.54` `collect` com sessão de revisão aberta: sessão intacta; só `running` de coleta fecha.
- `T4.55` `collect` recusa com trava presa.
- **`T4.56` Perda do banco, com registro em `tmp_path`:** X retirado, banco vazio, `collect`: nenhuma requisição à página de X, nenhuma linha; demais pendentes; linha `restore` volta a coletar. Com banco cheio: X no registro e com linha não vira `verifying` nem é requisitado. Registro ilegível: `failed`, sem requisição.
- `T4.57` `Disallow` em página: item segue, disponibilidade intacta, fonte `ok`, `success`.
- `T4.58` `source_updated_at` vem de `lastmod`; `--accept-mass-change` exige `--by`, `--reason` e fonte `ok`.
- **`T4.59` Recuperação, seção 5.9, com aprovações por factory:** fonte aprovada, A publicado com dado ruim e B com dado certo; `suspended`: ambos fora; `collect` recusado; `candidate`: ambos fora; v2 em `collect`: A com hash novo pendente, B com mesmo hash; durante todo o caminho, view vazia para a fonte; `approved`: só B volta; A só depois de aprovado.

**Fase 5.**
- `T5.1` Limite de 5.
- `T5.2` Caminho, `sha256`, relativo.
- `T5.3` URL conhecida: zero requisições.
- `T5.4` URL nova muda o hash.
- `T5.5` Mesmos bytes em URL nova: hash igual, imagem servível.
- `T5.6` Foto nova falha: página segue, não entra no hash.
- `T5.7` 403 em foto: nada do item gravado; fonte `blocked`.
- `T5.8` Robots ausente: `failed`, página segue.
- `T5.9` Rejeitado, mesmo hash: sem requisição.
- `T5.10` `mark_photos_pending` e `reconcile` não deixam `pending` fora da seleção.
- `T5.11` Sai da seleção: arquivo mantido; A→B→A serve de novo sem download.
- `T5.12` Expirado e `unavailable` mantêm fotos baixadas por `collect`.
- `T5.13` Troca de posições sem violar índice.
- `T5.14` `purge`: `stored` sem arquivo selecionada → `pending`, fora da seleção → `deleted`; órfãos removidos; idempotente.
- `T5.15` Duas URLs com mesmos bytes: uma posição.
- `T5.16` Selecionada `pending` força entrada e ignora pulo.
- `T5.17` Caminho não escapa; `.gitignore` cobre.
- **`T5.18` Rejeitado, só preço muda, mesmas URLs:** na mesma coleta, hash novo, `review_status='pending'`, fotos antes `deleted` agora `stored`, e nenhuma selecionada com `sha256` conhecido fora de `stored`. A aprovação por comando é provada em `T6.4`.
- `T5.19` Rejeitado, mesmo hash, foto `failed`: sem nova tentativa; hash igual.
- `T5.20` Retirada durante o download: item descartado; pasta removida.
- `T5.21` A rejeitado → B → A, e rejeição durante a coleta: arquivos apagados depois do commit.
- `T5.22` `purge` recusa com trava presa; só apaga no padrão; banco vazio exige `--all`.
- `T5.23` `Disallow` em foto: `failed`, página segue, fonte `ok`.
- `T5.24` Desafio 200 com marcador em foto: `Blocked`, nada gravado do item.
- `T5.25` HTML sem marcador em fotos consecutivas: `NETWORK_STOP_CONSECUTIVE`.

**Fase 6.**
- `T6.2` `apply` aprova com hash igual.
- `T6.3` Hash divergente recusado, em `a` e `r`.
- `T6.4` Matriz da seção 4.1: aparece, rejeita, aprova, cada linha; inclui anúncio de `T5.18` aprovável depois da coleta.
- `T6.5` Rejeitado fora da fila; fotos apagadas.
- `T6.6` Correção gravada, inclusive `iptu=reported:1200.00:annual`.
- `T6.7` Correção sobrevive à recoleta; cai com hash novo.
- `T6.8` `withdraw`: registra no log antes do banco, em `tmp_path`; apaga fotos, sai; funciona durante coleta; repetir é idempotente.
- `T6.9` `restore` exige nova revisão e registra.
- `T6.10` `reopen`: pendente, sai, aprovável depois de baixar.
- `T6.11` Arquivo aplicado não reaplica.
- `T6.12` `withdraw` → `restore` → recoleta → arquivo antigo: recusado; e com a sessão ainda aberta: decisão posterior ao início da sessão recusa a linha.
- `T6.13` `reviews` só de inclusão, por varredura.
- `T6.15` `build` com sessão aberta recusa; `--discard`: `discarded`, arquivo renomeado, não conta no tempo.
- `T6.16` Linha para não pendente recusada.
- `T6.17` Erro de sintaxe: nada gravado, sessão aberta; corrigido, aplica.
- `T6.18` Lote: preço, taxa, tipo e foto recusados; `reopened` recusado; alerta bloqueante recusado; título, anunciante e CRECI recusados (U20).
- `T6.19` Canonizador mudou, colunas iguais: lote aprova; **`resolved_*` copiado**, valor corrigido segue na view.
- `T6.20` Diferença contra versão aprovada; `alugai report`: por motivo e fonte, `versoes_novas`, `invalidos_novos`, `indisponiveis_novos`, `aprovados`, `possiveis_duplicados`, totais, tempo.
- `T6.21` Tempo = soma das sessões `success` / decisões.
- `T6.22` E2E: `collect` → `build` → `apply` → 1 publicado; preço muda → 0; aprova → 1; `withdraw` → 0; `listing_public_status` = `unavailable`.
- `T6.23` `reopen` e `restore`: zero requisições, mesmo com fonte `blocked`; fotos selecionadas `pending`.
- `T6.24` `withdraw`, `review apply`, `report`, `reopen`, `restore` funcionam com trava presa.
- **`T6.25` Piloto até a view:** cenário de `T4.13`; `review build`, `review apply` aprovam; fonte `approved`; **dado da v2 na view**, com condomínio "não informado".

**Fase 7** (`alugai_e2e_test`).
- `T7.1` `format`: rótulos, `iptuLabel` usa `iptuMonthly`, `confirmLine`, `formatBRL` (`87,27`, `1.800`), `seenLabel`.
- `T7.2` `mapRow`.
- `T7.3` `PUBLISHED_COLUMNS` = colunas da view; `FEE_STATUSES` = CHECK menos `needs_review`; `IPTU_PERIODS`, `PET_POLICIES` = CHECK; `RENT_PERIODS`, `PROPERTY_TYPES` ⊂ CHECK, com exclusões explícitas.
- `T7.4` Anúncio da seed aparece, e sem `warnings`, `evidence`, `storage_path` no HTML.
- `T7.5` Só publicáveis.
- `T7.6` Catálogo vazio: estado vazio do catálogo, sem erro.
- `T7.7` Mudar hash e recarregar: some, sem rebuild.
- `T7.8` Sem "Disponível hoje", `wa.me`; "Visto em"; link com `href`, `rel`, `target`.
- `T7.9` Taxa desconhecida sem total; "taxas a confirmar".
- `T7.10` Em anúncio da seed com nulos: sem `NaN`/`null`/`undefined`; `0` "Sem garagem".
- `T7.11` Linha "Confirme".
- `T7.12` Textos, rua, CRECI, crédito, `#<id>`.
- `T7.13` Dialog sem fotos.
- `T7.14` Pet: `yes`, `no`, `unknown` em nenhum.
- `T7.15` Quartos, banheiros, vagas com nulo fora; aviso; sem `owner`.
- `T7.16` Zonas e bairros dos dados; UFAM, UEA, PIM.
- `T7.17` Sem coordenadas: só lista; todos sem: estado vazio; sem erro de console.
- `T7.18` Botão do mapa abre além dos 12.
- `T7.19` `/?imovel=` além dos 12.
- `T7.20` Indisponível, inexistente, mal formado.
- `T7.21` "Compartilhar" gera URL que abre.
- `T7.22` Foto: 200, tipo, `no-store`; outro anúncio, posição 6, `..`: 404; retirar: 404 na hora.
- `T7.23` Ausentes: "Anunciar", "proprietário", "corretor", "WhatsApp", "fale direto", "R$ 5.550", "unsplash".
- `T7.24` Banco fora: mensagem, sem "0 cantinhos".
- `T7.25` `quickFilters` sem `owner`, ids = CHECK.
- `T7.26` Nada importa `lib/properties`.
- `T7.27` Scripts com `-H 127.0.0.1`; `start` real em loopback (`ss -ltn`).
- `T7.28` A na foto 3, depois B com 1: "1 / 1".
- `T7.29` Card com 0 e 1 foto.
- `T7.30` Anúncio da seed aparece; `pg_terminate_backend`; processo vivo e anúncio aparece de novo. Opções do pool conferidas.
- `T7.31` Rota de fotos com banco fora: 503.
- `T7.32` Foto responde 200; arquivo removido; 404.
- `T7.33` R$ 1.250,50 igual em card e mapa; fechar tira `?imovel=`.
- `T7.34` Ordem da lista: `last_seen_at DESC, public_id`.

**Fase 8.**
- `T8.3` O driver falha sem transporte simulado.

### 10.4 Verificações (sem etapa vermelha; se falhar, é defeito)

Não têm como falhar antes da implementação, ou exercitam só código já pronto.

- `T0.6` Lint ignora `.venv` (comando na fase 0). Se passar antes do ajuste, registrar que a hipótese era falsa e manter.
- `T1.2` `alembic check` limpo. Com migrações e tabelas vazias, já passa.
- `T8.1` Ponta a ponta entre pilhas, **em um único teste** de `e2e/cycle.spec.ts`, com seed só no início: `cycle_driver.py <passo>` com `MockTransport`; Playwright confere `initial`, `approve`, `price_change`, `reapprove`, `page_gone_1`, `page_gone_2`, `return_same`, `sob_consulta` (some), `withdraw` (some, foto 404), `expire`, `photo_added`. Roda com tudo implementado.
- `T8.2` `e2e-live/live.spec.ts`, por `npm run test:live`: recusa banco `_test`, confere contagem contra o banco real; todo card com link e "Visto em". Depende de dados reais.

---

## 11. Defeitos e testes

| Defeito | Situação | Teste |
|---|---|---|
| 1. "Sob consulta Cond. R$ 300" | Adaptador Viva Real não vem; regra em `parse_rent` | `T3.10` |
| 2. "A partir de" | Testado | `T3.12`, `T4.1` |
| 3. Diária sem temporada | Testado | `T3.13`, `T4.1` |
| 4. "Vendo casa", "Galpão" | Testado | `T4.2` |
| 5. `upsert` com `None` | `store.py` não vem; regra nova | `T4.9`, `T4.10`, `T4.13` |
| 6. Aborta em `LayoutError` | Regra nova | `T4.28`, `T4.29` |
| 7. Rejeitado vira `partial`; `.ps1` | Status testado; **`.ps1` não se aplica** | `T4.43`, `T4.26` |
| 8. `export` e reativação | `export` não vem; **cartão não se aplica** | `T1.7`, `T4.30`, `T4.33`, `T4.40` |
| 9. Href relativo; `next_urls` | Relativo testado; **`next_urls` não se aplica** | `T2.24`, `T3.20` |
| `exact_number("1.000 m²")` | Testado | `T3.15` |
| `fee`: dois-pontos, incluído, sob consulta; sem `on_request` | Testado | `T3.16`, `T1.3` |
| `ValueError` fora da OLX | Testado | `T2.1` |
| Sem XML e imagem | Testado | `T2.12`-`T2.16` |
| Robots ausente | Página mantém; foto com liberação | `T2.7`, `T2.19`, `T2.20` |
| Porta 5432 | Testado | `T0.4` |
| Link além de 12; hash não lido | Mecanismo novo | `T7.18`, `T7.19` |
| `properties[4]`, "R$ 5.550" | Testado | `T7.6`, `T7.23` |
| WhatsApp, "Disponível hoje" | Testado | `T7.8` |
| `layout.tsx:6`, `page.tsx:226,288,302`, `site-header.tsx:30-36` | Testado | `T7.23` |
| Prefixo `ALG-` | Formato novo | `T1.17`, `T7.12` |
| Lint na `.venv` | Hipótese testada | `T0.6` |
| Testes do `Fetcher` acoplados | Extraídos | `T2.2`-`T2.9` |
| `.env.example` com Firecrawl | Testado | `T0.3` |
| Postgres nunca testado | Suíte `db` | `T1.*` |
| `review_status` fixo | Derivado | `T1.14` |

---

## 12. Grafo de dependências

```
0 ──> 1 ──> 2 ──> 3a ──[checkpoint da amostra]──> 3b ──> 4 ──> 5 ──> 6 ──┐
      │                                                                  ├─> 8
      └──────────────> 7 (dados sintéticos) ────────────────────────────┘
```

- **Em paralelo:** 7 com 2 a 6; mudança em `0002` atualiza `T1.9` e `T7.3` no mesmo PR. Adaptadores diferentes, com amostra de um site por vez. O conteúdo de `neighborhoods.csv` pode ser preparado antes; o arquivo entra na fase 4.
- **Nunca em paralelo:** `sample`, `collect`, `purge`.
- **Portões humanos:** checkpoint do plano; termos; amostra; piloto.

---

## 13. Critérios de pronto do MVP

| # | Critério | Verificação | Esperado |
|---|---|---|---|
| M1 | ~200 aprovados, com link e "Visto em" | `SELECT count(*) FROM published_listings;` + `npm run test:live` (`T8.2`) | Conforme U2: **≥ 180**, ou reservas esgotadas com aceite registrado |
| M2 | Taxa desconhecida nunca em total | `T1.8`, `T7.9` | Verde |
| M3 | Alterado ou retirado some sozinho | `T8.1`; segunda passada: `alugai report` traz `versoes_novas`, `invalidos_novos`, `indisponiveis_novos`, com amostra conferida à mão | Verde; números declarados, ainda que zero |
| M4 | Rejeição por site e tempo de revisão | `alugai report` | Por fonte e motivo; tempo total e médio |
| M5 | Nada de terceiros no Git | `T0.1`, `T3.1`, comandos da fase 8 | Verde; sem saída |
| M6 | Coleta conforme as regras | `T2.30`, `T2.39`, `T4.26`; `SELECT s.slug FROM sources s WHERE EXISTS (SELECT 1 FROM captures c WHERE c.source_id=s.id) AND (s.terms_checked_at IS NULL OR s.terms_result='prohibited');` | Verde; sem linhas |
| M7 | Só as views chegam ao site | `T1.10`, `T7.4` | Verde |
| M8 | Links funcionam | `T7.19`, `T7.20` | Verde |
| M9 | Qualidade | `pytest -q -ra`, lint, `next typegen && tsc`, build, `test:e2e` | 0 failed, 0 skipped |
| M10 | Base do Pedro preservada; crédito | `git merge-base --is-ancestor 53a68a4 origin/codex/olx-collector || echo "BASE AUSENTE"`; `for f in alugai/__init__.py alugai/__main__.py alugai/network.py alugai/values.py alugai/adapters/base.py alugai/review.py compose.yaml pyproject.toml .gitignore .env.example tests/test_network.py tests/test_values.py; do git log feat/catalogo-fontes-locais --format=%B -- "$f" | grep -q 'Co-authored-by: Pedro Belota' || echo "SEM CREDITO $f"; done` | Sem saída |
| M11 | Duplicados relatados | `alugai report`: `aprovados`, `possiveis_duplicados` | Presentes |
| M12 | Total é útil, ou se sabe que não é | `SELECT count(*) FILTER (WHERE monthly_total IS NOT NULL), count(*) FROM published_listings;` | Só relatar (C4) |
| M13 | Site só em loopback | `T7.27` | Verde |

---

## 14. Conflitos encontrados

Nenhuma decisão foi alterada por conta própria.

- **C1. Foto trocada x custo.** 01 §3 pede hash de bytes. Literalmente, ~1.000 downloads por passada. D12: troca sob a mesma URL não é detectada. U1.
- **C2. Transições incompletas.** Sem regra para página válida com dado impublicável. D13. U3.
- **C3. Meta de ~200.** 00 "Pronto quando ~200", 01 "alvo sem mínimo". Estimativa de 218 com ~8% de folga, por URL; reservas são o caso esperado. U2.
- **C4. Total pode passar vazio.** Critério satisfeito com zero totais, e `cards.py:71` deixa o período de IPTU como desconhecido, sem outra atribuição. `M12` expõe.
- **C5. "Site lê somente `published_listings`" (00).** Exceção do 01 §4, mais `published_listing_photos`. Escolha E1.
- **C6. "Fotos apagadas quando retirado" (00) é ambíguo.** Só retirada e rejeição apagam; `unavailable` pode voltar sem revisão; foto fora da seleção fica. Fotos de terceiros em disco sem prazo. U1.
- **C7. Reversão exige revisão com o mesmo hash.** Exige `reopened`, além do 00.
- **C8. Revisão reaberta precisa das fotos.** `reopen`/`restore` só ficam aprováveis depois de uma `collect`; com fonte `blocked`, esperam o desbloqueio. Falha fechada.
- **C9. Telefone no título.** 00: alerta; título não editável. Só alerta publicaria telefone de terceiros. Adotei bloqueante. U3.
- **C10. `expires_at`.** Não pode ser gerada; gravado por código (`T4.8`).
- **C11. Zonas.** `lib/properties.ts:76-86` tem cinco; pelo que sei há Centro-Oeste, **não verificado**. U7.
- **C12. Prazo da amostra x "sem prazos".** 30 dias; passar disso repete requisições.
- **C13. Nome de anunciante.** Pessoa física aceita pelo 01; dívida antes de público (P13).
- **C14. Grupo de PRs.** "3-4" do 00 contra D19. Escolha E2.
- **C15. Dano da parada por degradação (D21).** A contestação da v1 pediu parada antes de gravar; aqui a regra para depois, para que preço visto como falso saia na hora, mesmo com execução interrompida. **Custo real** (tabela da seção 5.3): defeito que atinge tudo desde o início, 5 anúncios por execução liberada; defeito parcial abaixo de 30%, **todos os atingidos, sem parada e com `success`** (25 de 100, por exemplo); defeito no meio da execução, até 30% do processado (~43 depois de 100 bons); não encontrado em massa, nenhum na 1ª execução e 5 por execução liberada, até o catálogo inteiro com dois `unblock`. Volta sem revisão em todos. U18.
- **C16. `location_precision` sem uso no site.** O 00 lista, 01:55 deixa fora do hash; texto único. U13.
- **C17. Loopback x celular.** `-H 127.0.0.1` impede abrir em outro aparelho; o README (`:15`) destaca responsivo. Testar com emulação. U13.
- **C18. Foto de execução interrompida.** Fica órfã até `purge`, sem exibição.
- **C19. Sem restauração.** 01:42 exige que retirada só se reverta por comando. Restaurar dump violaria; por isso D24. **Custo:** perda do banco refaz a revisão, `public_id` mudam (contra a estabilidade de 00:59 nesse evento extremo), rejeições anteriores voltam a ser decididas. U19.
- **C20. Registro de retiradas fora do banco.** `data/retiradas.log` guarda URL, autor e motivo em arquivo local, fora do Git. **"Retirados não voltam" depende de esse arquivo sobreviver**: é único, sem cópia, na mesma máquina do banco. Perdidos os dois, o anúncio volta pendente, sem aviso, e pode ser reaprovado. U19.
- **C21. `Disallow` em página.** A tabela do 01 não cobre. Item segue sem confirmar e expira. Alternativa: parar o site inteiro por uma URL vetada, sem saída.
- **C22. Lote e "sem impacto".** 01:57 permite lote para "mudança sem impacto"; 00:55 diz que dado alterado volta à revisão. Título, anunciante e CRECI aparecem no site, então a mudança é visível. **Decidido em U20: revisão individual.**
- **C23. Fontes no repositório público.** 00:8 diz que o repositório é público; `config/sources.toml` e os adaptadores mostram quais sites são coletados, antes do aviso às imobiliárias (P8). Não é dado de anúncio. **Decidido em U21: opção A, tudo público desde a fase 3.**

---

## 15. Parâmetros ajustáveis após a amostragem

Constantes em `alugai/domain.py`. **Valores iniciais sem dado real**; mudam com registro em `docs/decisoes.md`, sem decisão do usuário.

| Constante | Inicial | Teste |
|---|---|---|
| `MISSING_MIN_INTERVAL` | 20 h | `T4.22` |
| `DEGRADED_STOP_MIN` / `DEGRADED_STOP_RATIO` | 5 / 30% | `T4.11`, `T4.12`, `T4.18` |
| `NETWORK_STOP_CONSECUTIVE` | 5 | `T4.48` |
| `SITEMAP_SHRINK_ABORT` | > 50%, com ≥ 10 conhecidos | `T4.37` |
| `REJECTED_URL_MEMO_DAYS` | 30, só URL sem anúncio | `T4.41` |
| `SITEMAP_GUNZIP_MAX_BYTES` | 50 MB | `T2.14` |
| `RENT_PLAUSIBLE_MIN/MAX` | R$ 200 / R$ 50.000, só alerta | `T4.1` |
| `COUNT_PLAUSIBLE_MAX` | 100 | `T4.1` |
| PD2 | ≥ 4 de 5 páginas | Matriz |
| PD7 | < 50% de coordenadas registra decisão | Matriz |
| Tabela de tipos, salvo sítio e chácara (U3) | Fase 4 | `T4.1` |

**Fixos por decisão anterior:** `EXPIRY_DAYS=30`, `MAX_PHOTOS=5` [USUÁRIO]; `SKIP_IF_CONFIRMED_WITHIN=7 dias`, `MISSING_CHECKS_TO_UNAVAILABLE=2`, `RAW_HTML_TTL=7/30` [PROPOSTA]; `DELAY_SECONDS=5`, piso 2 s, `MAX_RESPONSE_BYTES=8 MB` [Pedro].

---

## 16. Decisões do usuário

**Registradas em 2026-11-02: o usuário aceitou todas as recomendações.** O texto de cada item abaixo fica como registro do que foi decidido e do que se abriu mão.

| Item | Decisão |
|---|---|
| U1 | Sim: fotos que saíram ficam em disco e foto trocada no mesmo endereço não é detectada; rever antes de abrir ao público |
| U2 | MVP encerra a partir de 180 aprovados, ou com reservas esgotadas e aceite registrado |
| U3 | Sim às quatro regras rígidas de publicação |
| U7 | Lista da Prefeitura; seis zonas se ela confirmar; "perto" é conter o local ou fazer divisa; Polo Industrial = Distrito Industrial. **Unidade da UEA não indicada (P17)** |
| U13 | Sim às quatro escolhas de aparência |
| U16 | Lista de testes aprovada |
| U17 | Sim: Playwright só para testar o site |
| U18 | Sim: anúncio que piora sai do site na hora |
| U19 | Sim: sem restauração; perda do banco refaz a revisão |
| U20 | Não pode em lote: revisão individual |
| U21 | Opção A: lista de fontes e adaptadores públicos desde a fase 3 |

As escolhas E1 a E6 foram apresentadas e não houve objeção.

A numeração tem saltos de propósito: os números são citados no restante do plano e não foram trocados. Foram juntadas as perguntas com a mesma resposta.

### U1. Fotos: o que fica em disco e o que não se detecta

**Pergunta.** Podemos manter no seu computador fotos de anúncios que saíram da imobiliária, e aceitar que uma foto trocada no mesmo endereço passe despercebida?

- **Se sim:** a coleta semanal não baixa de novo cerca de 1.000 fotos. Se a imobiliária trocar a imagem mantendo o endereço, o site continua mostrando a antiga. Fotos de anúncios que sumiram ficam guardadas sem prazo, em disco local.
- **Se não:** cada passada baixa as fotos de novo, com até 1,5 h a mais e mais carga nos sites, e toda troca volta para revisão. Fotos de anúncio sumido passam a ter prazo, e quem voltar precisa baixar de novo.

**Recomendação: sim.** Antes de abrir o site ao público, isso precisa ser revisto junto com a autorização das fotos.

### U2. Quando o MVP está pronto se não chegar a 200 anúncios

**Pergunta.** A meta é cerca de 200 anúncios aprovados, e a estimativa inicial é 218 antes de qualquer filtro. Se ficar abaixo, o que encerra o MVP?

- **Com a recomendação:** vale a partir de 180. Abaixo disso, tentamos os quatro sites reserva; se ainda faltar, você aceita o número final, registrado. A validação nunca é afrouxada para ganhar volume.
- **Com outro número:** você define o corte. Número mais alto significa mais sites reserva, e cada um pode exigir um leitor novo.

**Recomendação: 180, ou reservas esgotadas com seu aceite.**

### U3. Regras rígidas de publicação

**Pergunta.** Aceita estas quatro regras, que tiram anúncios do site em caso de dúvida?

1. Anúncio cuja página passa a dizer "Sob consulta", só venda ou temporada sai do site até voltar ao normal.
2. Título com telefone não pode ser publicado. Como o título é copiado da fonte e não se edita, a única saída é rejeitar.
3. Uma foto ruim rejeita o anúncio inteiro, sem aprovação parcial.
4. Sítio e chácara não são tratados como residenciais e ficam fora.

- **Se sim:** menos anúncios, e nenhum com preço já visto como falso ou telefone de terceiros.
- **Se não, em cada uma:** (1) o preço antigo fica até 30 dias; (2) telefone de terceiros pode aparecer; (3) entra aprovação por foto, com mais estados; (4) sítio e chácara entram.

**Recomendação: sim às quatro.**

### U7. Bairros e "perto de"

**Pergunta.** Os filtros dependem de uma tabela de bairros feita à mão. Três respostas são necessárias:

1. Qual lista oficial usar?
2. Uso as seis zonas, incluindo Centro-Oeste, se a lista confirmar? O site hoje tem cinco.
3. O que conta como "perto" da UFAM, da UEA e do Polo Industrial, e qual unidade da UEA vale?

- **Com a recomendação:** a tabela usa uma fonte citável, e "perto" é verificável num mapa.
- **Com outro critério:** muda só a tabela. Enquanto não houver resposta, os filtros de "perto" ficam vazios e os anúncios com bairro sem cadastro não publicam.

**Recomendação:** lista da Prefeitura de Manaus; seis zonas, se ela confirmar; "perto" é bairro que contém o local ou faz divisa com ele; Polo Industrial = Distrito Industrial. **A unidade da UEA precisa ser indicada por você.**

### U13. Aparência do site

**Pergunta.** Aceita estas quatro escolhas?

1. A abertura da página mostra só a marca, sem foto nem preço de anúncio.
2. "A combinar com o anunciante" aparece junto de "Confirme com o anunciante" no cartão, e por extenso nos detalhes.
3. Todo anúncio com mapa diz "Localização aproximada, informada pela fonte", mesmo quando a fonte for exata.
4. O site abre só neste computador.

- **Se sim:** menos variações de tela, e nenhuma afirmação de endereço exato. Para ver no celular, será preciso simular no navegador.
- **Se não:** indique qual muda. Em (1), uma foto de terceiros fica em destaque. Em (4), o catálogo e as fotos ficam acessíveis para quem estiver na mesma rede.

**Recomendação: sim às quatro.**

### U16. Lista de testes

**Pergunta.** Aprova a lista de testes antes de começar? Cada mudança tem um teste escrito e visto falhando antes do código. A lista tem 235 itens, com resumo por fase no início da seção 10.

- **Se sim:** a implementação segue a lista, e todo teste novo descoberto é acrescentado.
- **Se não:** aponte o que falta ou sobra. Cortar testes reduz o tempo de trabalho, e reduz também a garantia de que nada indevido chega ao site.

**Recomendação: aprovar**, lendo ao menos os itens em destaque da fase 4.

### U17. Playwright só para testar o site

**Pergunta.** Você proibiu Playwright na coleta. Posso usá-lo só para testar o site, nunca para obter dados das imobiliárias?

- **Se sim:** os testes abrem o site em um navegador de verdade. Um teste automático falha se Playwright aparecer no código de coleta.
- **Se não:** uso outras ferramentas, sem navegador real, com mais simulação e menos segurança de que o site funciona de ponta a ponta.

**Recomendação: sim.**

### U18. Defeito no leitor de um site: quanto pode sair do ar

**Pergunta.** Quando a coleta vê que um anúncio mudou para pior, ele sai do site na hora. Isso protege contra preço falso, mas um defeito no nosso leitor também tira anúncios bons. Aceita esse risco?

Quanto sai, conforme o defeito:

- Atinge tudo desde o início: a coleta para em 5 anúncios, e cada liberação sua pode tirar mais 5.
- **Atinge só parte, menos de 30%: a coleta não para e termina como sucesso.** Por exemplo, 25 de 100 saem, e o sinal aparece só no relatório.
- Começa no meio da coleta: até 30% do que foi processado, por exemplo cerca de 43 depois de 100 bons.
- Páginas aparentemente sumidas em massa: nenhum sai na primeira coleta; depois, 5 a cada liberação, e o catálogo inteiro pode cair depois de duas liberações.

Em todos, corrigido o leitor, os anúncios voltam sem nova revisão. Mudança real em massa se aceita com um comando que registra quem e por quê.

- **Se sim:** nenhum preço visto como falso fica publicado. O custo é o site ficar menor até a correção, e é preciso ler o relatório depois de cada coleta.
- **Se não:** guardar as mudanças até o fim da coleta e só gravar se parecerem normais. Um preço falso poderia ficar até 30 dias no site, e o fluxo fica mais complexo. Foi o desenho rejeitado na revisão anterior.

**Recomendação: sim.**

### U19. Se o banco de dados se perder

**Pergunta.** O plano não tem restauração por cópia de segurança, porque restaurar faria voltar ao site anúncio retirado depois da cópia. Aceita reconstruir do zero nesse caso?

- **Se sim:** é preciso refazer a revisão de cerca de 200 anúncios e registrar de novo termos e liberações. Os links compartilhados antigos deixam de funcionar. Nada vai ao site sem nova aprovação. **Anúncios retirados não voltam só enquanto o arquivo `data/retiradas.log` sobreviver.** Esse arquivo é único, sem cópia, no mesmo computador. Numa perda de disco, os retirados voltam à fila de revisão sem aviso, e cabe a você não aprovar de novo.
- **Se não:** acrescentamos um diário de decisões reaplicado na restauração, com peça e testes a mais, para um evento raro.

**Recomendação: sim.** Se retiradas passarem a importar, guarde cópia desse arquivo fora do computador.

### U20. Aprovação em lote de mudanças em título, anunciante ou CRECI

**Pergunta.** Quando só muda o título, o nome do anunciante ou o CRECI, isso pode ser aprovado em lote, sem abrir anúncio por anúncio? E um alerta não impeditivo, como "vendo" no título, deve barrar o lote?

- **Se pode em lote:** menos trabalho quando muitos anúncios mudam só no texto. Em troca, um título como "Vendo casa" ou um nome de pessoa física pode aparecer no site sem ninguém ter visto.
- **Se não pode:** essas mudanças vão para revisão individual. Mais trabalho nas mudanças em massa de texto. O lote fica só para mudanças internas, em que nada visível muda.

**Recomendação: não pode; revisão individual.** Com isso, a pergunta sobre alertas deixa de existir, porque o lote só aceita mudança sem nada visível.

### U21. Lista de fontes no repositório público

**Pergunta.** O repositório é público. A partir da fase 3, a lista de sites coletados e os leitores de cada um ficam visíveis para qualquer pessoa? Hoje a branch do Pedro já mostra um dos domínios. Nenhuma das alternativas coloca dados de anúncios, HTML ou fotos no Git.

- **A. Tudo público desde a fase 3.** Simples, e Miguel e Pedro revisam tudo nos PRs. As imobiliárias podem descobrir a coleta antes de serem avisadas.
- **B. Lista de fontes fora do Git, leitores públicos.** Esconde os domínios, mas os nomes e a estrutura dos leitores ainda indicam as plataformas. Um clone novo não funciona sem o arquivo local, e os revisores não veem a lista.
- **C. Trabalhar em repositório privado até o aviso às imobiliárias.** Nada fica exposto. Depende de Miguel e dá trabalho para trazer de volta ao repositório principal na integração.

**Recomendação: A**, porque o MVP é privado, nada do que fica público é dado de anúncio, e é o caminho mais simples. Se a descoberta antes do aviso preocupar, **C**. B protege pouco.

### Escolhas já tomadas no plano

Não pedem resposta; avise se discordar.

- **E1.** O site lê uma segunda consulta só para fotos, além da principal, para o caminho do arquivo não chegar ao navegador (C5).
- **E2.** O código de amostragem é revisado antes da primeira requisição, em PR próprio (C14).
- **E3.** O piloto é na Ponta Negra, e depois seguem S C Jardim, Habitanorte, Habitamax, Procasa e GVB, do menor para o maior. Você autoriza a continuação depois de ver o piloto.
- **E4.** O registro da amostra fica fora do Git, em `data/fontes-matriz.md`.
- **E5.** Padrões do documento 01 adotados, com estes ajustes: sem coluna para o tipo de anunciante, pois é sempre imobiliária; decisão "reaberto" e correção guardada na própria revisão; tempo de revisão medido por sessão; intervalo entre requisições por site; conteúdo que volta ao já aprovado dispensa nova revisão; precisão da localização não vai ao site.
- **E6.** Página vetada pelo robots segue sem confirmação e expira, sem parar o site inteiro (C21).

**Depois da amostra.** PD3, PD7, PD8, PD10 e PD11, com dados reais.

---

## 17. Pendências externas

Nenhuma está totalmente resolvida; o estado parcial está em cada linha.

| # | Pendência | Quem | Bloqueia |
|---|---|---|---|
| P1 | Alinhamento com Miguel e Pedro. Em 2026-11-03 o Pedro publicou nova coleta por Firecrawl em OLX, Viva Real e Ponta Negra (7.0), método fora do escopo deste plano. **Decisão do usuário em 2026-11-04:** os dois trabalhos seguem em paralelo, e o aproveitamento será conversado no futuro. Não bloqueia as fases 0 a 8; continua necessário antes da integração na `main` [USUÁRIO] | Usuário | Integração |
| P2 | Permissão de abrir PR em `miguelmoraesx/alugai`. Branch e push funcionam (escrita) | Miguel | PR-A |
| P3 | Existência de deploy da `main` | Usuário | Integração |
| P4 | Termos dos 6 sites e reservas | Humano | Fase 3a |
| P5 | Domínios, sitemaps, hosts, das notas da sessão principal para o TOML | Sessão principal | Fase 3a |
| P6 | Carga de `neighborhoods` | Operador | Dados reais |
| P7 | Chromium. Docker, Compose, porta 55432 e `alembic`/`defusedxml` em Python 3.14.4 confirmados na fase 0; compatibilidade em uso, na fase 1 | Operador | Fases 1, 7 |
| P8-P12 | Aviso às imobiliárias; advogado; autorização de fotos; título copiado; canal de remoção | Usuário | Tornar público |
| P13 | Pessoa física como anunciante | Usuário | Tornar público |
| P14 | Licença (`README.md:114`) e crédito | Miguel e Pedro | Integração |
| P15 | Tiles do OpenStreetMap, se público | Usuário | Tornar público |
| P16 | `CLAUDE.md` descreve arquitetura antiga | Usuário | Nada |
| P17 | Unidade da UEA que vale para "perto da UEA" (U7) | Usuário | Filtro "perto da UEA"; demais dados, não |

---

## 18. Autoverificação

1. **Perguntei antes de desenhar?** Respostas no 00 e 01; o restante na seção 16.
2. **NFRs sem empate?** Sim, seção 1.
3. **Opções reais?** Sim, seção 2.
4. **Sacrifício e risco?** Seções 2, 5.3 e 14.
5. **ADR?** Condensado; vai a `docs/decisoes.md`.
6. **Guardrails verificáveis?** Testes, comandos e SQL. Limite: **nada foi executado por este autor**; as referências cruzadas foram conferidas por releitura e busca, não por execução.

---

## 19. Resolução das contestações

### 19.1 Contestação final (`07`)

| Id | Situação | Como |
|---|---|---|
| M1 | **Corrigido** | `T4.13` para em `listing_review_state`; prova na view em `T6.25`. `T5.18` assere estado da fase 5; aprovação em `T6.4` |
| M2 | **Corrigido** | Regra de gravação imediata mantida; `T4.19` descreve a sequência real em quatro execuções; texto da 5.3 corrigido |
| M3 | **Corrigido** | Seção 5.9 com todos os estados, por `candidate`. `T4.59`. Sem peça nova |
| M4 | **Corrigido** | Tabela da 5.3, fase 4, C15 e U18 alinhados, com o caso sem parada. `T4.18` |
| M5 | **Decidido pelo usuário** | U20: revisão individual; C22; `T6.18` |
| M6 | **Decidido pelo usuário** | U21: opção A; C23; referência de D18 corrigida |
| B1 | Corrigido | `retiradas.py` recebe caminho; `ALUGAI_RETIRADAS_LOG`; testes em `tmp_path` |
| B2 | Corrigido | Declarado em 5.8, C20 e U19 |
| B3 | Corrigido | `waive-robots`, `notice` na reconstrução |
| B4 | Corrigido | `T4.11` restrito a âncora presente; texto da 5.3 sobre `LayoutError` |
| B5 | Corrigido | Base contém todo degradado; `T4.18` |
| B6 | Corrigido | Conhecidos antes de novos, em ordem estável; `T4.13` com 20 URLs |
| B7 | Corrigido | Numeração contínua, `T5.10` |
| B8 | Corrigido | Controle positivo nos specs (seção 8); `T1.1` assere tabelas; seção 10.4 para `T0.6`, `T1.2`, `T8.1`, `T8.2` |
| B9 | Corrigido | `discover` com `on_fetch`; `T2.33`, `T3.4`, `T4.47` |
| B10 | Corrigido | Chaves do relatório em `T6.20`; 5.6 classifica `LayoutError` isolado e `Disallow`; registro ilegível falha fechado; `sample --url` consulta; retirado no registro sai dos conhecidos; `withdraw` idempotente |
| B11 | Corrigido | Marcado [USUÁRIO] na seção 1 |
| B12 | Declarado | Seção 4.1: resta rejeitar, falha fechada. Sem mudança de regra |
| B13 | Corrigido | `npm ci` na fase 0; `.env.local` na seção 8 |
| Nits | Corrigidos | Import em 10.1; `neighborhoods.csv` na seção 12; `--all` na fase 5; `cards.py:71` em C4 |

### 19.2 Contestação da v2 (`05`)

Todos corrigidos; **nenhum recusado.**

| Id | Como |
|---|---|
| A1 | Gravação adiada removida; aceite auditável; `--limit` declarado. `T4.11`-`T4.15`, `T4.19`, `T4.37` |
| A2 | Sem restauração (D24, 5.8); registro de retiradas. `T4.56`, `T6.8`, `T6.9` |
| M1 | Base, momento e estoque definidos. `T4.17`, `T4.18` |
| M2 | Não encontrado conta. `T4.19` |
| M3 | Aceite cobre queda de sitemap. `T4.37` |
| M4 | Só `running` de coleta fecha; `discarded`. `T3.9`, `T4.54`, `T6.15` |
| M5 | Dois passos de download em volta do hash. `T5.18`, `T5.19` |
| M6 | `DisallowedByRobots`; liberação só para ausente. `T2.20`, `T2.42`, `T4.57`, `T5.23` |
| M7 | Desafio 200 = `Blocked`. `T2.16`, `T2.41`, `T5.24`, `T5.25` |
| M8 | Testes realocados. `T3.9`, `T3.22`, `T4.52`, `T4.55`, `T5.20`, `T5.22`, `T6.23`, `T6.24` |
| M9 | Lote copia `resolved_*`. `T6.19` |
| M10 | Matriz da 4.1. `T6.4` |
| B1-B12 | `T5.10`, `T5.21`, `T5.20`, `T6.12`, `T6.15`, `T7.34`, `T7.1`, `T2.32`, `T4.53`, `T2.38`, `T5.22`, `T8.1`; critérios tautológicos retirados |
| B13 | Não se aplica: backup removido |

**Desvio registrado.** A contestação da v1 pedia parada "antes de gravar"; o plano para depois (C15, U18).

**Recusados de B13 da v1.** `counters` fica, pois alimenta o relatório exigido e nenhuma regra o consulta. Os PRs ficam, pois o 00 pede PRs pequenos, e só PR-B1 é adicional.

### 19.3 O que saiu ao longo das revisões

Gravações adiadas; `--force`; `DEGRADED_STOP_CONSECUTIVE`; `--fields` de `approve-batch`; backups com `pg_dump`; memória de rejeição para anúncio conhecido; `photos retry`; `review close`; `neighborhood alias`; download dentro de `restore`; consultas tautológicas dos critérios.

---

## Apêndice A. Documento 00: escopo e entendimento

Reprodução sem alterações de conteúdo, com a numeração original. Onde difere do Apêndice B, prevalece o B.

```text
   1  # Alugaí: escopo, decisões e relatório de entendimento (FASE 2)
   2  
   3  Insumo para os agentes de contestação e planejamento. Escrito pela sessão principal.
   4  As seções marcam o que foi VERIFICADO (executado/lido) e o que é SUPOSIÇÃO.
   5  
   6  ## 1. Onde está o código
   7  
   8  - Repositório: `/home/gassis/documentos/trabalho/alugai`, branch `main` (remoto `miguelmoraesx/alugai`, público).
   9    Working tree com `CLAUDE.md` não commitado. Site Next.js 16 + React 19 + Tailwind + Leaflet. Sem testes.
  10  - Coletor Python: só na branch remota `origin/codex/olx-collector` (2 commits à frente da `main`, autor Pedro Belota).
  11    Cópia para leitura sem git em:
  12    `<cópia temporária do coletor>/`
  13    (ignorar `.venv/` e `data/`). Inclui `alugai/`, `tests/`, `docs/`, `compose.yaml`, `pyproject.toml`, `scripts/`.
  14  - Arquivos centrais do site na `main`: `lib/properties.ts`, `app/page.tsx`, `components/property-card.tsx`,
  15    `components/property-details-dialog.tsx`, `components/property-map.tsx`, `components/site-header.tsx`, `app/globals.css`.
  16  
  17  ## 2. Produto
  18  
  19  Metabuscador de aluguel residencial em Manaus. Mostrar o custo mensal real e a origem do anúncio.
  20  Fase atual: MVP PRIVADO, sem prazo definido, um único operador (o usuário roda os scripts e revisa).
  21  
  22  ## 3. Decisões do usuário (não reabrir; contestar só se houver defeito concreto, indicando a consequência)
  23  
  24  ### Fontes e coleta
  25  - Primeiro lote, somente Manaus: Procasa, Habitanorte, Ponta Negra Imóveis, S C Jardim, GVB Imóveis, Habitamax.
  26  - Obtenção por SCRIPT, não coleta manual.
  27  - Padrão único: sitemap -> página do anúncio -> adaptador por plataforma
  28    (4 adaptadores: Code 49 [Habitanorte, Ponta Negra, S C Jardim], Procasa, GVB, Habitamax).
  29  - Site cuja página de anúncio não traz dados no HTML bruto vai para plano B (captura da página carregada no navegador) ou sai do lote.
  30  - Sumiço do sitemap é sinal para verificar, nunca para remover diretamente.
  31  - Fora do escopo: OLX, Viva Real, Chaves na Mão, Firecrawl, Playwright, chamada a `/_int/`, região Norte, formulário de anúncio.
  32  - Regras do script: respeitar robots.txt; parar o site em 401/403/429/CAPTCHA sem contornar; identificação honesta sem dado pessoal; não acessar áreas proibidas.
  33  - Meta de cerca de 200 anúncios, sem baixar a qualidade da validação. Candidatos reserva: Casa Manaus, Imóveis Manaus, Manaus Administradora, Lopes.
  34  
  35  ### Modelo de dados (contrato coletor <-> site)
  36  Tabelas: `sources`, `captures`, `listings`, `listing_versions`, `reviews`, `neighborhoods`, `listing_photos`.
  37  - `sources`: domínio, adaptador, status, termos lidos por quem e quando (`terms_checked_at`), aviso enviado.
  38  - `captures`: URL, data, status HTTP, hash, versão do adaptador.
  39  - `listings`, identidade `source_id` + `external_id`. Campos:
  40    - origem: `source_url` (obrigatório), `advertiser_name`, `creci`, `source_title`
  41    - imóvel: `property_type`, `bedrooms`, `bathrooms`, `parking_spaces`, `area_m2` (número desconhecido = null; "5 ou mais" não vira 5)
  42    - aluguel: `rent_amount`, `rent_period` (sem aluguel claro não passa da validação; "Sob consulta" no aluguel fica fora do site)
  43    - condomínio: `condo_amount`, `condo_status` (reported, exempt, included, unknown, on_request, needs_review)
  44    - IPTU: `iptu_amount`, `iptu_status`, `iptu_period` (mensal, anual, desconhecido)
  45    - pet: `pet_policy` (yes, no, unknown, on_request)
  46    - local: `city`, `neighborhood_raw`, `neighborhood_id`, `street` (opcional, só se a fonte publicar, sem nº de apartamento, sem inferir), `latitude`, `longitude`, `location_precision`
  47    - tempo: `first_seen_at`, `last_seen_at`, `source_updated_at`, `expires_at`
  48    - estado: `availability_status`, `review_status`, `withdrawn_at`, `content_hash`
  49    - interno (nunca vai ao site): `warnings`, `evidence`
  50  - `listing_versions`: cópia normalizada a cada mudança; substitui `collector_price_history`.
  51  - `reviews`: decisão, motivo, revisor, data, hash da versão aprovada.
  52  - `neighborhoods`: bairro, nomes alternativos, zona, proximidade UFAM/UEA/PIM. Tabela manual. Nome não reconhecido vai para revisão.
  53  - `listing_photos`: URL de origem, hash, local de armazenamento, status, data. Limite de 5 por anúncio. Fora do Git.
  54  - Publicação é CALCULADA, nunca um campo: fonte liberada + versão atual aprovada + disponível + não expirado + não retirado.
  55  - Aprovação presa ao `content_hash`: dado alterado volta para revisão e sai do site até nova aprovação (inclui preço).
  56  - `monthly_total` calculado, só quando aluguel, condomínio e IPTU são conhecidos e o período permite. `on_request`/`unknown` não entram.
  57  - Site lê somente a view `published_listings`, sem `warnings`/`evidence`.
  58  - Tipos reais: NUMERIC, TIMESTAMPTZ, colunas próprias. Migrações desde o início. Os 52 registros atuais não migram.
  59  - Expiração: 30 dias sem nova confirmação. Links compartilhados precisam de ID público estável e mensagem de "anúncio indisponível".
  60  
  61  ### Apresentação
  62  - Título: copiado da fonte (`source_title`), com alerta na revisão para telefone ou conflito de venda.
  63  - Fotos: baixadas e exibidas (até 5), porque o MVP é privado. Sem remover marca d'água, com crédito à fonte, apagadas quando o anúncio é retirado. Revistas antes de publicar.
  64  - Rua: exibida quando a fonte publicar; caso contrário, só bairro.
  65  - Textos: `unknown` -> "Confirme com o anunciante"; `on_request` -> "A combinar com o anunciante"; `exempt` -> "Isento"; `included` -> "Incluso no aluguel". IPTU com valor sem período -> "R$ X, período a confirmar", fora da soma.
  66  - Card: uma única linha "Confirme com o anunciante: condomínio, IPTU e pet"; sem total fechado se faltar taxa.
  67  - "Disponível hoje" sai; entra "Visto em [data]". Ação principal: "Ver anúncio original" (sem WhatsApp, sem telefone de terceiros, sem descrição completa).
  68  - Sem coordenadas: anúncio só na lista. Filtro "aceita pet" mostra só `yes`.
  69  
  70  ### Operação
  71  - Revisão humana MANTIDA antes de publicar. Relatório HTML local com dados, fotos e link + comandos aprovar/rejeitar.
  72  - Tudo local: Postgres em Docker, script, `next dev`. Sem hospedagem nesta fase. Dados, HTML e fotos fora do Git (repositório é público). HTML bruto pelo menor tempo possível.
  73  - Branch de trabalho `feat/catalogo-fontes-locais`, a partir da `main`, trazendo só o necessário da branch do Pedro, com crédito nos commits. Não apagar nem reescrever a branch do Pedro.
  74  - Trazer: `network.py`, funções de valor de `parser.py`, testes do `Fetcher`, `pyproject.toml`, ajustes de `.gitignore`, `compose.yaml`, `ponta_card` como referência.
  75  - Não trazer: `firecrawl.py`, `probe.py`, adaptadores OLX/Viva Real, scripts PowerShell.
  76  - PRs pequenos para `main`.
  77  - Termos dos sites, aviso às imobiliárias e advogado ficam para depois, MAS há trava proposta: script só roda contra site com `terms_checked_at` preenchido (planejado; sinalizado ao usuário como proposta aceita ao dizer "decisões estabelecidas"; será reconfirmada no checkpoint).
  78  - Requisitos antes de tornar público (dívida registrada): autorização de fotos, reavaliar título copiado, termos, avisos, advogado, canal de remoção.
  79  
  80  ### Fases aprovadas em alto nível
  81  0 Base; 1 Banco; 2 Obtenção; 3 Adaptadores; 4 Validação; 5 Fotos; 6 Revisão; 7 Site (pode correr em paralelo a partir da fase 1 com dados sintéticos); 8 Passada real (primeiro um site, depois seis).
  82  PRs: 0-2; 3-4; 5-6; 7.
  83  Pronto quando: ~200 aprovados no site privado com link de origem e "Visto em"; taxa desconhecida nunca em total; anúncio alterado/retirado some sem intervenção no site; números de rejeição por site e tempo de revisão disponíveis.
  84  
  85  ## 4. Entendimento do código atual (VERIFICADO por leitura, salvo indicação)
  86  
  87  ### Coletor
  88  - Dois modelos desconectados: `Listing` (`parser.py`) em `collector_listings`; `Candidate` (`cards.py`) em `collector_review_items` (`review.py`).
  89  - OLX fixa: `canonical_url` em `parser.py` só aceita olx.com.br; `Fetcher.rules`/`FirecrawlFetcher.request` a chamam; `Store.due(source="olx")`; `collector.py` usa `mark_error("olx", ...)`.
  90  - `Fetcher.get` rejeita resposta sem `text/html`, portanto não lê sitemap XML nem imagens.
  91  - `Fetcher.rules` trata robots ausente (ex.: 404) como `Blocked`.
  92  - `review.py::build_review` lê um arquivo por fonte (`<source>.html`), limite padrão 20, e sobrescreve o registro ao reimportar.
  93  - `Store`: datas e preços como texto, dados em JSON, `create_all` sem migrações. Postgres nunca testado segundo `docs/coletor.md`.
  94  - Não existe comando de aprovação/publicação; `review_status` é valor fixo em `cards.py`.
  95  - Testes: 62 passam, cobertura 77%, `cli.py` 0% (EXECUTADO em Python 3.14, sobre a cópia). `requires-python >=3.11`.
  96  
  97  ### Defeitos reproduzidos com HTML sintético (EXECUTADOS)
  98  1. Viva Real "Sob consulta Cond. R$ 300" -> aluguel 300.
  99  2. "A partir de R$ 1.000 / mês" -> valor exato mensal.
 100  3. "R$ 150 / dia" e título "diárias" -> sem marcar temporada.
 101  4. OLX "Vendo casa" R$ 350.000 -> aluguel sem alerta; "Galpão comercial" idem. Sem campo de tipo.
 102  5. `Store.upsert(detail=True)` com campo None apaga valor e cria histórico falso.
 103  6. `refresh` aborta em LayoutError no primeiro anúncio.
 104  7. Um cartão rejeitado -> status `partial`; `.ps1` não roda refresh (leitura, não executado).
 105  8. `export` inclui `unavailable`; cartão reativa anúncio indisponível.
 106  9. Href relativo rejeita cartão. `next_urls` sempre vazio no caminho de cartões.
 107  
 108  ### Site (`main`)
 109  - `app/page.tsx` é inteiro `"use client"`; importa o array de `lib/properties.ts`; filtra por `useMemo`; mapa recebe `filteredProperties`, cards recebem `visibleProperties`.
 110  - `Property` exige condo, iptu, latitude, longitude, petFriendly, advertiser, zones, images. Sem URL de origem nem data.
 111  - Hero depende de `properties[4]` e texto fixo "R$ 5.550". "Disponível hoje" fixo em `property-card.tsx`. WhatsApp fictício em card e dialog.
 112  - `quickFilters` e `zones` ligam dados a filtros; prefixo `region-` tem significado; `owner` é especial.
 113  - Lint, build e `tsc` passaram na `main` (EXECUTADO em cópia). Rota `/` é estática.
 114  
 115  ## 5. Fatos sobre os sites (VERIFICADO em 02/11/2026 por requisições leves; NÃO repetir requisições aos sites)
 116  
 117  | Site | Sitemap | Separação de aluguel | lastmod | Estimativa residencial | Observação |
 118  |---|---|---|---|---|---|
 119  | Procasa | índice, 348 sub-sitemaps (111 aluguel) | caminho `/imoveis/aluguel/<tipo>/am/<cidade>/<bairro>` | sim | ~77 de ~211 de aluguel | Listagem usa AngularJS, 0 preços no HTML; dados vêm de `/_int/` (vedado no robots). Anúncio `/imovel/<slug>/<codigo>`: dados no HTML + JSON-LD `Product` (só 1 anúncio de sítio analisado; conteúdo do bloco NÃO lido). Página de "venda e aluguel" mostra os dois preços; 34 preços e 7 links de outros anúncios na página. Fotos em `static.sitemidas.com.br` (logos observados; origem das fotos de anúncio é SUPOSIÇÃO) |
 120  | Habitanorte | direto, 179 URLs | `<id>/imoveis/locacao-...`; também `/imobiliaria/<tipo>/locacao/imoveis/<id>` | sim | ~47 | Code 49 |
 121  | Ponta Negra | direto, 58 URLs | `<id>/imoveis/locacao-...` | sim | 13 | Code 49; `ponta_card` testado em cartões, não na página do anúncio |
 122  | S C Jardim | direto, 28 URLs | inclui `venda-locacao-` | sim | ~9 | Code 49 |
 123  | GVB | índice WordPress, 978 URLs | `imovel/<id>...`, `imovel/aluguel...`, categorias misturadas | sim | ~44 | Tem termos de uso |
 124  | Habitamax | direto, 182 URLs | `imovel/...-para-alugar-...` | NÃO | ~28 | `__NEXT_DATA__` na home; página do anúncio não analisada |
 125  
 126  SUPOSIÇÕES ainda não verificadas: dados completos no HTML do anúncio nos outros 5 sites; adaptador único serve aos 3 sites Code 49; contagens são por URL de sitemap, não anúncios confirmados; soma estimada ~218 pode cair com filtros.
 127  
 128  ## 6. Restrições para quem trabalhar neste material
 129  - Não editar nada no repositório. Não fazer commit nem criar branch.
 130  - Não fazer requisições aos sites das imobiliárias.
 131  - Escrever em português do Brasil.
```

## Apêndice B. Documento 01: entendimento apurado

```text
   1  # Relatório final apurado (FASE 4)
   2  
   3  Complementa `00-escopo-e-entendimento.md` e prevalece sobre ele em caso de conflito.
   4  A contestação do entendimento rejeitou a seção 3 por não fechar o contrato de dados; os fatos de código se confirmaram.
   5  
   6  Legenda: **[USUÁRIO]** decisão do usuário, não reabrir. **[PROPOSTA]** padrão da sessão principal, ainda não confirmado pelo usuário: o plano deve adotá-lo e listá-lo na seção "A confirmar no checkpoint". Pode ser melhorado se justificar. **[FATO]** verificado.
   7  
   8  ## 1. Decisões novas do usuário
   9  
  10  - **[USUÁRIO] Plano B eliminado.** Site cuja página de anúncio não traz os dados no HTML bruto sai do lote e entra um reserva. Sem coleta manual e sem Playwright na coleta.
  11  - **[USUÁRIO] Aluguel:** "Locação" + preço, sem "/mês", publica como mensal presumido, separado do explícito e visível na revisão. Dia, temporada e "a partir de" ficam fora.
  12  - **[USUÁRIO] Amostra antes dos adaptadores:** leitura dos termos antecipada para o início da fase 3; poucas páginas por site, somente em armazenamento local. Antes disso, nada roda contra sites reais.
  13  - **[USUÁRIO] Integração:** PRs internos para `feat/catalogo-fontes-locais`. Essa branch só entra na `main` quando o MVP estiver pronto e alinhado com Miguel e Pedro. A `main` fica intacta. Isso substitui "PRs para main" do documento 00.
  14  - **[USUÁRIO] Sem prazos.** Trava de termos aceita: script só roda contra site com termos verificados.
  15  
  16  ## 2. Ciclo de vida e estados [PROPOSTA]
  17  
  18  ### Valores
  19  - `sources.status`: `candidate`, `approved`, `suspended`, `removed`. Só `approved` publica.
  20  - `sources.collection_state`: `ok`, `blocked`, com data e motivo. **Separado de `status`**: um 429 interrompe a coleta sem tirar anúncios do site.
  21  - `sources.terms_result`: `allowed`, `silent`, `prohibited`, `not_found`, com `terms_checked_at` e `terms_checked_by`. `prohibited` impede a coleta. `not_found` permite no MVP privado e entra na dívida de publicação.
  22  - `sources.display_name` para crédito à fonte; `photo_hosts` lista explícita.
  23  - `availability_status`: `active`, `verifying`, `unavailable`.
  24  - Revisão: `reviews` é a única fonte de verdade. `pending`/`approved`/`rejected` é derivado comparando a última decisão com o `content_hash` atual. Sem coluna redundante, salvo justificativa.
  25  - `rent_period`: `monthly`, `assumed_monthly`, `short_term`, `unknown`. Só os dois primeiros publicam.
  26  - `condo_status` e `iptu_status`: `reported`, `exempt`, `included`, `unknown`, `on_request`, `needs_review`.
  27  - `iptu_period`: `monthly`, `annual`, `unknown`.
  28  - `pet_policy`: `yes`, `no`, `unknown`, `on_request`.
  29  - `property_type`: enumeração residencial mais `other` não residencial, definida no plano. Não residencial não publica.
  30  - `location_precision`: `exact`, `approximate`, `none`.
  31  - `listing_photos.status`: `pending`, `stored`, `failed`, `deleted`.
  32  
  33  ### Transições
  34  | Evento | Resultado |
  35  |---|---|
  36  | Sumiu do sitemap | `verifying`, continua publicado; o script consulta a página na mesma execução |
  37  | Página 404/410 em 2 verificações separadas | `unavailable`, sai do site |
  38  | HTTP 200 com "indisponível", ou redirecionamento para home ou outro anúncio | Conta como não encontrado; os padrões vêm do adaptador |
  39  | 401/403/429/CAPTCHA, erro de rede ou de layout | Não altera disponibilidade; só `collection_state` e a execução |
  40  | `unavailable` observado de novo, mesmo hash | Volta a `active`, sem nova revisão |
  41  | Expirou (30 dias sem confirmação) | Sai do site; fotos ficam. Nova confirmação com mesmo hash renova sem revisão |
  42  | `withdrawn_at` | Definido só por comando, a pedido; nunca limpo por coleta. Fotos apagadas. Reversão só por comando e exige nova revisão |
  43  | Rejeitado com mesmo hash | Permanece rejeitado, sem voltar à fila. Fotos apagadas. Hash novo volta à fila |
  44  | `needs_review` | Não pode ser aprovado sem o revisor resolver o status; a correção é uma decisão registrada e sobrevive à recoleta se o dado da fonte não mudar |
  45  
  46  O defeito 8 (reativação) e o defeito 6 (aborto em layout) eram comportamento intencional do código do Pedro: tratar como mudança de regra, não como correção de bug. Layout quebrado continua parando o site na execução, mas um anúncio individual sem dados não aborta os demais, salvo proporção alta definida no plano.
  47  
  48  ### Confirmação e frequência
  49  - `last_seen_at` só é renovado por página de anúncio baixada e validada; presença no sitemap não conta. "Visto em" nunca afirma mais do que foi verificado.
  50  - Execução manual pelo operador, sugestão semanal. Anúncio retirado na fonte pode ficar no site até o próximo ciclo: tolerância aceita no MVP privado.
  51  - Com `lastmod` igual, pular o download só se a última confirmação tiver menos de 7 dias. Habitamax sem `lastmod`: baixa sempre.
  52  
  53  ## 3. Hash, versões e reaprovação [PROPOSTA]
  54  
  55  - `content_hash` cobre somente o que o usuário vê: `source_title`, tipo, quartos, banheiros, vagas, área, aluguel e período, condomínio e IPTU (valor, status e período), pet, `neighborhood_raw`, `street`, cidade, coordenadas, `advertiser_name`, `creci`, e os hashes ordenados das fotos.
  56  - Fica de fora: tempos, `warnings`, `evidence`, `neighborhood_id`, `source_updated_at`.
  57  - Nova versão de adaptador só exige revisão se o hash mudar; a revisão mostra a diferença em relação à versão aprovada e permite aprovar em lote uma mudança sem impacto.
  58  - Foto trocada na fonte muda o hash e volta para revisão.
  59  
  60  ## 4. Identidade e links [PROPOSTA]
  61  
  62  - `public_id` próprio, estável, sem expor a fonte.
  63  - Cada adaptador define `external_id` a partir de código estável da fonte, nunca do slug; se não existir, o site é tratado no piloto de amostragem.
  64  - Link compartilhado: decisão de mecanismo do plano. Deve abrir anúncio além dos 12 primeiros, o que hoje falha (`page.tsx:65`, `property-map.tsx:198`, `property-details-dialog.tsx:28`). Hoje `page.tsx` não lê o hash.
  65  - Exceção mínima à regra da view: view pública separada só com `public_id` e estado, para distinguir "indisponível" de "inexistente", ou justificativa melhor.
  66  
  67  ## 5. Total mensal [PROPOSTA]
  68  
  69  - `monthly` e `assumed_monthly` permitem total. O site indica a presunção de forma discreta.
  70  - `exempt` e `included` somam 0. `unknown`, `on_request`, `needs_review` impedem o total.
  71  - IPTU `annual` divide por 12, arredondado a centavos. Parcelas sem clareza: período `unknown`, fora do total.
  72  - Total será raro em IPTU sem período: medir na amostra, sem inventar.
  73  
  74  ## 6. Etapa de amostragem [USUÁRIO + PROPOSTA]
  75  
  76  Nova etapa no início da fase 3: ler termos dos 6 sites; baixar pelo próprio `Fetcher` até 5 anúncios por site, variando tipo e "venda e aluguel", em `data/`; preencher matriz por site com HTML bruto ok?, JSON-LD?, ID estável?, aluguel e período, taxas, pet, rua, CRECI, coordenadas, tipo, fotos e host, sinal de indisponível.
  77  Saída: go/no-go por site, projeção de volume e regra para reservas. Fixtures versionadas são sintéticas, reescritas à mão a partir da estrutura observada, sem conteúdo real. HTML bruto: apagar após validação; no máximo 7 dias, ou 30 para amostras de depuração.
  78  
  79  Meta: ~200 é alvo sem mínimo rígido. Se a projeção ficar abaixo, ativar reservas na ordem, pelo mesmo filtro. Sem baixar validação. Relatar "aprovados" e "possíveis duplicados".
  80  
  81  ## 7. Medição [PROPOSTA]
  82  
  83  Adicionar `collection_runs` (modo, fonte, início, fim, contadores, motivo). `captures` ganha resultado da validação e motivo; rejeitado por validação não vira publicável, mas fica rastreável. Tempo de revisão: início e fim da sessão de revisão, ou `reviews.started_at`. Rejeição por site sai de consulta.
  84  
  85  ## 8. Lacunas menores [PROPOSTA]
  86  
  87  - **Duplicados:** não deduplicar; só alertar na revisão, reaproveitando a ideia de `review.py::duplicate_candidates`. Conta separada.
  88  - **Anunciante:** todas as fontes são imobiliárias. `advertiser_type` fixo `agency`. Selo "Direto com proprietário", filtro `owner` e cores por tipo saem da interface. CRECI exibido; nome de pessoa física só se a fonte o exibir como anunciante.
  89  - **Mapa:** sem centróide e sem geocodificação nesta fase. A amostra mede a cobertura de coordenadas. O site tem estado vazio de mapa. Se a cobertura for baixa, vira decisão registrada no checkpoint da amostra.
  90  - **Campos nulos:** quartos, banheiros, vagas e área nulos são ocultados; `parking_spaces = 0` continua "Sem garagem". Lista sem fotos usa visual neutro sem `NaN`. Toggle de soma com total nulo mostra aluguel e "taxas a confirmar". Filtros numéricos excluem nulos, com aviso discreto. "Aceita pet: não" mostra só `no`.
  91  - **View:** `published_listings` agrega fotos, fonte, zonas e proximidade. Papel de banco só-leitura para o site. `locationGroups` e `allNeighborhoods` em `page.tsx:26-34` passam a vir dos dados.
  92  - **Ferramentas:** Alembic controla o schema (Python). Driver Postgres no Next, escolha do plano. Fotos servidas por rota do Next a partir de pasta local fora do Git, com proteção contra path traversal. A rota `/` deixa de ser estática.
  93  - **`Fetcher`:** `canonical_url` em `network.py:8,80,109` vira política de hosts por fonte, incluindo redirecionamentos; hoje `Fetcher.get` em site não OLX lança ValueError (executado). Precisa retornar bytes para imagem e aceitar XML. Robots ausente no host de páginas mantém bloqueio. Host de fotos só se listado em `photo_hosts`; robots ausente nele é bloqueio salvo liberação explícita registrada. Intervalo por origem, não global, a avaliar; custo atual de ~18 min páginas e ~1,5 h fotos.
  94  - **Funções reaproveitadas:** `amount`, `fee`, `exact_number`, `count` estão em `cards.py:36-63`. Defeitos adicionais [FATO]: `exact_number("1.000 m²")` retorna 1.0; `fee("Condomínio: R$ 300")`, `fee("Condomínio incluído")` e `fee("Condomínio Sob consulta")` retornam `unknown`; `on_request` não existe no código.
  95  - **Porta [FATO]:** 127.0.0.1:5432 já está ocupada nesta máquina por PostgreSQL nativo. Usar outra porta configurável.
  96  - **Destino de cada arquivo da branch do Pedro:** o plano precisa classificar cada um como trazer, adaptar, referência ou deixar: `cli.py`, `collector.py`, `store.py`, `review.py`, `parser.py`, `cards.py`, `network.py`, `tests/*`, `.env.example` (traz chave Firecrawl), `docs/*`, README, `compose.yaml`, `pyproject.toml`, `.gitignore`.
  97  - **Testes do `Fetcher`:** estão em `tests/test_collector.py`, que importa `collector` e `store` e usa `SEED` da OLX; exigem extração e reescrita.
  98  - **Interface, além do listado no 00:** `app/layout.tsx:6` ("fale direto com quem anuncia"), `page.tsx:226` (cores), `page.tsx:288` (WhatsApp), `page.tsx:302` (proprietário), `property-card.tsx:61` (prefixo `ALG-`), `site-header.tsx:30-36` (formulário que descarta dados). Formulário e chamada "Anunciar" ficam ocultos no MVP. Dados de exemplo saem do fluxo real; a `main` não é afetada até a integração.
  99  - **`eslint.config.mjs`:** adicionar `.venv/` e `data/` aos ignorados (hipótese não executada de que o lint varreria a `.venv`).
 100  - **`neighborhoods`:** carga inicial manual com fonte e critério de proximidade de UFAM/UEA/PIM definidos no plano. Em `lib/properties.ts`, as zonas são só de demonstração.
 101  - **Fotos de anúncio rejeitado:** apagadas.
 102  - **Procasa [FATO, por requisição desta sessão]:** os sub-sitemaps de aluguel listam tanto anúncios `/imovel/<slug>/<codigo>` (211 únicos em Manaus) quanto páginas de busca `/imoveis/aluguel/...` (107). Slugs "para-venda-e-aluguel" existem. A descoberta é possível sem a listagem.
 103  
 104  ## 9. Pendências fora do alcance do plano (registrar, nunca dar como resolvidas)
 105  Alinhamento com Miguel e Pedro antes de iniciar a branch; existência de deploy da `main`; resultado dos termos; aviso às imobiliárias e advogado antes de tornar público; autorização de fotos; título copiado.
```
