# Decisões de arquitetura

Rev.: dupla = barato desfazer; única = caro. Origem: seção 2 do `PLANO.md`, aprovada em 2026-11-02. Mudanças de parâmetro e de decisão são registradas aqui.

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

## Registro de mudanças

- 2026-11-03: a base de cópia do código do Pedro fica fixada em `53a68a4`, porque a branch dele avançou para `d441ad7` (`PLANO.md`, seção 7.0).
- 2026-11-04: decisão do usuário: o trabalho do Pedro e este seguem em paralelo; o aproveitamento será conversado no futuro. O alinhamento continua necessário antes da integração na `main`.
