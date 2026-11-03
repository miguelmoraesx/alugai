# Coletor OLX — primeira versão

Serviço Python independente do frontend Next.js, com dois trabalhos: descobrir
referências novas e verificar referências já armazenadas. O desenvolvimento fica
na branch `codex/olx-collector`. Deploy e tarefas recorrentes não foram ativados.

## Estado da validação

- Testes automatizados usam HTML sintético explicitamente identificado, sem anúncios reais.
- A tentativa inicial de obter a página de Manaus por HTTP retornou **403 Forbidden**.
- Existe agora um [provedor Firecrawl e experimento de comparação](firecrawl.md).
  A primeira chamada anônima à API também retornou 403, antes de obter páginas da OLX.
- O adaptador `__NEXT_DATA__` é experimental: aceita `props.pageProps.ads`, `ad` ou
  `adDetails`, mas **não foi validado contra HTML real atual da OLX**. Não há
  promessa de quantidade, completude ou acesso ao catálogo.
- A coleta autenticada pelo plugin Firecrawl obteve HTML real das buscas da OLX,
  Viva Real e Ponta Negra Imóveis. O parser de cartões atual foi conferido nessa
  amostra: **52 referências estão na base separada de revisão**, sem publicação.
  O fallback de cartões atende à busca atual da OLX, que não usa `__NEXT_DATA__`.
  Páginas de detalhes e disponibilidade ainda não foram verificadas.
- Há parsers conservadores de páginas de detalhe para OLX, Viva Real e Ponta
  Negra Imóveis, usados pelo comando `collect-houses` (Firecrawl). Eles aceitam
  apenas casas com IPTU e período explícitos; veja
  [firecrawl.md](firecrawl.md). Veja a
  [comparação das fontes e o comando de revisão](comparacao-fontes.md).
- SQLite permite testar localmente sem serviços externos. PostgreSQL tem configuração
  e driver preparados, mas não foi testado neste ambiente: o Docker daemon está desligado.
- A interface continua usando os imóveis demonstrativos existentes. O coletor não
  inventa fotos, coordenadas, telefones ou valores para preencher os campos do frontend.

## Instalação — PowerShell

Execute na raiz do repositório. Requisito: Python 3.11 ou superior.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

Não é necessário ativar o ambiente virtual. Em Linux/macOS use `.venv/bin/python`.
O pacote não modifica a instalação Node e não precisa de chave de IA.
O provedor HTTP permanece o padrão; Firecrawl é uma opção explícita.

## Demonstração offline, sem coletar a OLX

```powershell
.\.venv\Scripts\python.exe -m alugai --database-url sqlite:///data/demo.db import-html tests/fixtures/search.html --fixture
.\.venv\Scripts\python.exe -m alugai --database-url sqlite:///data/demo.db export --source olx-fixture --output data/demo.json
.\.venv\Scripts\python.exe -m alugai --database-url sqlite:///data/demo.db runs
```

Repetir a importação atualiza os registros, sem criar duplicações ou repetir o histórico
de preços. `--fixture` separa os exemplos na fonte `olx-fixture`, excluída das consultas
e atualizações reais. Nunca importe o arquivo de teste sem essa opção.

Para conferir um HTML real obtido legitimamente, use `import-html caminho.html --url URL`
sem `--fixture`. Esse comando não faz requisições. A amostra deve ser uma página de
aluguel do recorte pretendido: não há classificador que certifique a categoria.
Não versione HTML real, dados de anunciantes ou exportações no Git.

## Execução HTTP

```powershell
# Uma página e até cinquenta anúncios por execução, por padrão.
.\.venv\Scripts\python.exe -m alugai discover --limit 50 --max-pages 1
.\.venv\Scripts\python.exe -m alugai refresh --limit 50 --stale-hours 24
.\.venv\Scripts\python.exe -m alugai export --output data/listings.json
.\.venv\Scripts\python.exe -m alugai runs
```

A busca inicial é:
`https://www.olx.com.br/imoveis/aluguel/estado-am/regiao-de-manaus/manaus`.
`--seed` permite configurar outra URL HTTPS da OLX. Os argumentos globais, como
`--database-url`, devem vir antes do subcomando.

Para usar o transporte Firecrawl, acrescente `--provider firecrawl` e, opcionalmente,
`--max-api-calls 13`. As regras abaixo sobre transporte direto e redirecionamentos
referem-se ao provedor HTTP. Limitações do transporte terceirizado estão em
[docs/firecrawl.md](firecrawl.md).

O transporte utiliza o identificador `AlugaiCollector/0.1`, uma requisição por vez e
intervalo mínimo padrão de cinco segundos. Consulta o `robots.txt` de cada origem,
incluindo subdomínios de anúncios, e respeita regras com curingas, Crawl-delay e
Request-rate. Cada destino de redirecionamento é validado antes do acesso.

HTTP 401/403/429 e desafios reconhecidos encerram a execução sem novas tentativas.
O `Retry-After` é registrado; não há rotação de proxies, disfarce de navegador ou
resolução de CAPTCHA. Falhas na obtenção de robots também suspendem a coleta.

A paginação só segue links `rel="next"` presentes no HTML e dentro do limite
`--max-pages`. Não são geradas URLs para contornar regras. A OLX publica restrições
para parâmetros como `o`, `q`, `ps` e `pe`; por isso uma primeira página acessível
não implica que a próxima possa ser coletada. A política real é consultada a cada execução.

Os códigos de saída são `0` para sucesso e `2` para execução parcial, bloqueada ou
com erro. O JSON da execução e a tabela `collector_runs` diferenciam esses estados.
Uma descoberta parcial conserva os registros válidos já processados, sem declarar
que a busca inteira foi concluída.

Antes do uso comercial, confirmar as condições de acesso e reutilização aplicáveis:
[termos OLX](https://ajuda.olx.com.br/s/article/termos-e-condicoes-de-uso) e
[robots.txt](https://www.olx.com.br/robots.txt). A autorização de acesso não é inferida
da existência de uma URL pública. O projeto não implementa republicação de fotos,
descrições completas ou contatos pessoais.

## Dados e atualização

Tabelas criadas automaticamente no primeiro uso:

| Tabela | Conteúdo |
| --- | --- |
| `collector_listings` | Chave composta fonte/ID, dados normalizados, status, hash e datas |
| `collector_price_history` | Primeira observação e alterações de aluguel/condomínio |
| `collector_runs` | Modo, início, término, contadores e motivo de falha |

O JSON contém ID externo, URL, título, cidade, bairro, aluguel, condomínio, área,
quartos, banheiros, vagas e indicação conservadora de periodicidade.
Valores monetários são strings decimais para preservar centavos. Campos desconhecidos
são `null`, não zero. Um título com indicação de temporada é marcado `short_term`;
sem indicação explícita, a periodicidade permanece `unknown`. A categoria de busca
não é prova de que o preço representa aluguel mensal.

Não há cálculo de custo mensal total: IPTU, taxas e periodicidade ainda precisam de
extração/validação antes disso. Não há geocodificação nem deduplicação entre anúncios
diferentes do mesmo imóvel; a deduplicação atual é por fonte/ID.

Uma descoberta não apaga campos de detalhes que o cartão omitiu. A verificação de
detalhes tem relógio próprio, para que descobrir o mesmo anúncio diariamente não
impeça sua atualização. Anúncios nunca verificados têm prioridade; os demais entram
na fila após `--stale-hours` desde a última tentativa de detalhes.

- `active`: anúncio observado com dados válidos.
- `pending_verification`: última tentativa falhou; os últimos valores válidos são mantidos.
- `unavailable`: duas verificações consecutivas receberam 404/410; isso **não significa alugado**.

Erro de rede, parser ou bloqueio nunca vira remoção. Anúncios ausentes da página de
busca não são removidos. Uma nova observação válida reativa o registro.
`last_seen_at` representa a última observação válida; `last_checked_at`, a última tentativa.
Não houve ainda implementação de expiração automática por idade para a interface.

## PostgreSQL

Com o Docker Desktop em execução:

```powershell
docker compose up -d db
$env:ALUGAI_DATABASE_URL = 'postgresql+psycopg://alugai:alugai_local@localhost:5432/alugai'
.\.venv\Scripts\python.exe -m alugai runs
```

O Compose publica a porta somente em `127.0.0.1` e usa volume persistente. A senha
é apenas para desenvolvimento local; configure `POSTGRES_PASSWORD` e ajuste a URL
para outro ambiente. O arquivo `.env.example` é uma referência: o CLI não carrega
`.env` automaticamente. Sem `ALUGAI_DATABASE_URL`, usa `data/collector.db` (SQLite).

A criação de tabelas é inicial, não um sistema de migrações. Alterações futuras de
schema precisam de migração explícita, principalmente se já houver dados reais.
A trava de arquivo impede execuções simultâneas neste checkout; use apenas um worker.
Coordenação entre máquinas e filas distribuídas não fazem parte desta versão.

## Agendamento Windows

O script abaixo executa descoberta e atualização sequencialmente e grava logs em
`data/logs/AAAA-MM-DD.log`. Se a descoberta falhar, a atualização não começa.

```powershell
powershell -NoProfile -File .\scripts\run-collector.ps1
```

Após validar acesso e parser com dados reais, é possível registrar a execução diária:

```powershell
.\scripts\register-collector-task.ps1 -At '08:00'
```

Esse comando usa o Agendador de Tarefas do Windows, no fuso configurado no computador,
sob o usuário atual quando conectado, sem janela visível e com limite de 30 minutos.
Não substitui uma tarefa existente. O processo herda as variáveis do usuário da tarefa;
uma variável definida apenas no terminal atual pode não estar disponível ao agendador.
Sem variável persistente de conexão, será usado SQLite local.

Nenhuma tarefa foi registrada automaticamente. Para consultar ou remover uma tarefa
que você registrar:

```powershell
Get-ScheduledTask -TaskName 'Alugai-OLX-Collector'
Unregister-ScheduledTask -TaskName 'Alugai-OLX-Collector'
```

## Validações antes de alimentar a interface

1. Obter acesso permitido e amostras reais das páginas de busca e de detalhes.
2. Ajustar o adaptador aos campos observados; adicionar amostras anonimizadas aos testes.
3. Conferir manualmente preço, modalidade de aluguel, localização e taxas numa amostra.
4. Validar a persistência no PostgreSQL em execução.
5. Adaptar o contrato do frontend para valores ausentes, fonte/URL e idade da informação.
   Os tipos atuais de `lib/properties.ts` exigem valores que o coletor não deve inventar.

Playwright só deve ser considerado se a inspeção mostrar necessidade de executar
JavaScript. Um 403, sozinho, não demonstra essa necessidade. Jev não é dependência.
