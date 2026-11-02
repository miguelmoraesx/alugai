# Experimento com Firecrawl

## O que foi implementado

`FirecrawlFetcher` usa `POST https://api.firecrawl.dev/v2/scrape` e entrega HTML ao
mesmo parser, validador e banco do coletor. Não exige SDK ou dependências adicionais.
O transporte HTTP original continua disponível e é o padrão.

O teste inicial sem chave, em 01/11/2026, recebeu **HTTP 403 da API Firecrawl** na
primeira chamada, destinada ao robots.txt. Nenhum anúncio foi obtido. Isso não é um
resultado de acesso à OLX e não demonstra que uma chave resolverá o bloqueio.
O relatório está em `data/firecrawl-probe-01.json` no ambiente local, fora do Git.

Os testes automatizados simulam respostas da API. Eles validam o contrato e o fluxo,
mas não certificam a compatibilidade com as páginas atuais da OLX.

Posteriormente, o plugin Firecrawl autenticado via OAuth conseguiu obter as páginas
de busca reais da OLX, Viva Real e Ponta Negra Imóveis. Os snapshots locais geraram
52 referências para revisão, com o parser de cartões conferido nessa amostra.
Veja a [comparação das fontes](comparacao-fontes.md). Essa conexão do plugin não
configura automaticamente a chave do script Python; a execução autenticada pela
API local e a extração de páginas de detalhes continuam pendentes de validação.

## Obter e configurar uma chave

1. Acesse [o painel do Firecrawl](https://www.firecrawl.dev/app), crie uma conta ou entre.
2. Localize **API Keys** e copie uma chave da sua conta.
3. Na raiz deste repositório, salve um arquivo chamado `.env.collector` com:

```dotenv
FIRECRAWL_API_KEY=sua_chave_aqui
```

Use um editor local. Não cole a chave no chat, README ou comandos compartilhados.
O `.gitignore` já exclui `.env.collector`. Também é possível definir
`FIRECRAWL_API_KEY` no ambiente: a variável tem prioridade sobre o arquivo.
O leitor local aceita apenas essa chave; não executa comandos nem expande variáveis.
As demais configurações, incluindo `ALUGAI_DATABASE_URL`, continuam vindo do ambiente.

A documentação consultada descreve chamadas sem chave com limites menores. O CLI
permite esse modo quando não há credencial e registra `auth_mode: anonymous`.
Neste ambiente ele não funcionou; uma chamada autenticada pelo script Python ainda
precisa ser testada. O acesso autenticado pelo plugin já funcionou nas buscas.

## Rodar a primeira amostra

Na raiz do repositório, depois da instalação descrita em `coletor.md`:

```powershell
.\.venv\Scripts\python.exe -m alugai probe-firecrawl --limit 10 --max-api-calls 13 --output data/firecrawl-probe-02.json
```

O comando obtém uma página de busca, seleciona até dez anúncios e tenta buscar os
detalhes de cada um. O teto de 13 chamadas inclui consultas ao robots.txt. Com duas
origens (www.olx.com.br e am.olx.com.br), são até duas consultas de regras, uma busca
e dez detalhes. Outros subdomínios podem consumir o limite antes de completar a amostra.
Uma falha não dispara tentativas extras. O teto limita requisições à API, não garante
um valor de cobrança ou limita as requisições internas executadas pelo serviço.

O relatório não substitui outro arquivo existente. Use um nome novo a cada execução.
Os registros do experimento ficam na fonte **olx-probe**, separados dos dados
operacionais `olx`, e não aparecem na interface do site.

```powershell
.\.venv\Scripts\python.exe -m alugai export --source olx-probe --output data/firecrawl-sample.json
```

## Repetir a mesma amostra

Após uma primeira execução que tenha selecionado anúncios, execute em outro momento:

```powershell
.\.venv\Scripts\python.exe -m alugai probe-firecrawl --repeat-report data/firecrawl-probe-02.json --output data/firecrawl-probe-03.json
```

Esse modo usa as mesmas URLs, sem refazer a busca. O relatório traz
`changes_since_previous` para cada anúncio, comparando os campos com a execução
anterior. O histórico no banco também registra mudanças de aluguel e condomínio.
Um relatório bloqueado antes da seleção de URLs não pode ser usado para repetição.

## Conferir resultados e custo

O relatório contém:

- Status da execução e quantidade de detalhes válidos.
- URLs selecionadas, campos extraídos e falhas individuais.
- `manual_checks` para aluguel, condomínio, bairro e periodicidade. Valores `null`
  significam que **a precisão ainda não foi conferida por uma pessoa**.
- Número de chamadas, origem (robots/página), status da API, status da OLX quando
  fornecido e duração. Uma falha da API não vira anúncio removido.
- Estimativa de créditos básicos: uma unidade por resposta de scraping bem-sucedida.
  `actual_billed_credits` permanece `null`; a API de scrape não fornece uma fatura.
  Confira o consumo efetivo no painel Firecrawl. Zero na estimativa não prova cobrança zero.
- Estimativa de créditos básicos por anúncio com detalhes válidos, incluindo as
  consultas de regras e busca. Esse indicador é `null` quando nenhum anúncio foi validado.

Abra as URLs da amostra e confira os quatro campos antes de aceitar o experimento.
A precisão manual e a disponibilidade real ainda não foram medidas nesta implementação.

## Opções da API e limites

- `rawHtml`, `onlyMainContent: false`: preservam os scripts de dados usados pelo parser.
  Não usamos JSON gerado por LLM neste experimento, evitando uma camada adicional de
  extração e cobrança. Se os scripts não vierem no HTML, o parser falha explicitamente.
- `maxAge: 0`: solicita uma coleta nova, em vez do cache padrão de até dois dias.
- `storeInCache: false`: solicita que o resultado não seja armazenado no índice/cache
  do serviço; isso não equivale a uma política integral de retenção zero.
- `proxy: basic`: não seleciona o modo automático de escalada de proxies.
- TLS é verificado; timeout do serviço de 45 segundos e do cliente de 55 segundos.
- A chave é enviada somente no cabeçalho da chamada à API Firecrawl. Ela não é enviada
  no campo `headers` destinado à OLX, nem aparece nos relatórios.

O robots.txt de cada origem é obtido **pelo próprio Firecrawl** e interpretado localmente,
com as mesmas regras de espera e bloqueio do coletor. Se o serviço não entregar regras
legíveis, a coleta para. URLs desautorizadas não são enviadas para scraping de anúncios.
O identificador `AlugaiCollector/0.1` é solicitado nos cabeçalhos destinados ao site.

O serviço remoto controla a navegação interna. O coletor rejeita um destino divergente
quando informado nos metadados, mas não tem controle prévio de cada redirecionamento
que o Firecrawl já tenha seguido. Portanto, não se deve atribuir a esse transporte a
mesma garantia de verificação por salto do cliente HTTP direto.

HTTP 401/402/403/429 da API interrompe o trabalho. HTTP 404 da API é erro do provedor;
somente o status 404/410 identificado como resposta da origem pode indicar anúncio
indisponível. Na amostra, nenhuma falha apaga registros operacionais.

## Usar nos comandos regulares

Após validar acesso, regras e extração com a amostra:

```powershell
.\.venv\Scripts\python.exe -m alugai discover --provider firecrawl --limit 10 --max-pages 1 --max-api-calls 13
.\.venv\Scripts\python.exe -m alugai refresh --provider firecrawl --limit 10 --max-api-calls 13
```

Esses comandos escrevem na fonte operacional `olx`. O agendamento Windows existente
continua no transporte HTTP; não foi ativado nem alterado para consumir Firecrawl.
Nenhuma assinatura, compra de créditos ou chamada recorrente foi criada.

Referências consultadas:
[API de scrape](https://docs.firecrawl.dev/api-reference/endpoint/scrape),
[guia de scrape](https://docs.firecrawl.dev/features/scrape) e
[cobrança](https://docs.firecrawl.dev/billing).
