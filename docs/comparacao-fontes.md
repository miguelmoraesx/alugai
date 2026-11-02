# Amostra comparativa e base de revisão

Foram analisados cartões de uma página por fonte, obtidos pelo Firecrawl conectado
ao chat. O objetivo era até 20 anúncios por fonte. O resultado foi **52 referências**:

| Fonte | Extraídos | Preço/bairro/área/quartos presentes | Mensal explícito | Condomínio utilizável* | Valor de IPTU utilizável* |
| --- | ---: | ---: | ---: | ---: | ---: |
| OLX | 20 | 19 | 0 | 0 | 2 |
| Viva Real | 19 | 19 | 19 | 8 | 6 |
| Ponta Negra Imóveis | 13 | 13 | 0 | 10 | 7 |

\* Campo informado acima de R$ 1, ou isenção/inclusão explícita. Não significa valor
conferido com anunciante. Um IPTU informado sem periodicidade não é convertido em mensal.

**Recomendação:** priorizar Viva Real no próximo teste de detalhes, manter imobiliárias
locais para enriquecer taxas e buscar integração direta, e usar OLX como fonte complementar.
Essa conclusão vale para esta amostra de cartões, não é um ranking de todo o mercado.
Não foram medidos disponibilidade real, precisão contra o anunciante ou custo de
manutenção ao longo do tempo. O HTML completo pode conter mais informações do que o cartão.

## Limitações observadas

- Viva Real: 11 dos 30 cartões eram agrupamentos de vários anúncios, sem URL individual
  diretamente no cartão. Foram excluídos, resultando em 19. Não se seguiu paginação
  cujo link continha filtros vedados no robots.txt consultado.
- Imobiliária: 37 dos 50 cartões não tinham uma oferta rotulada como locação; foram
  excluídos. A classe CSS `rent-price` também era usada para valores de venda. O
  adaptador usa o rótulo explícito, não o nome da classe.
- OLX: a página contém cartões HTML com atributos semânticos; não é necessário
  interpretar ou executar o protocolo interno de scripts do Next.js para a busca.
- Dois anúncios do Viva Real traziam taxas de R$ 1: preservadas como evidência e
  sinalizadas, sem somá-las ao aluguel.
- A imobiliária apresentou um conflito entre título de venda e campo de locação,
  e outro entre preço principal e preço citado explicitamente na descrição.
- Três pares foram marcados como possíveis duplicações. Similaridade de bairro,
  quartos, área e preço não prova que sejam o mesmo imóvel; nenhum foi mesclado.
- Números como `5 ou mais` e intervalos como `61 - 62 m²` não viram quantidades exatas.

## Artefatos locais

- `data/review/index.html`: relatório com filtros por fonte e busca por bairro/ID/alerta.
- `data/review/comparison.json`: dados normalizados, evidências curtas, métricas e pares similares.
- `data/collector.db`, tabela `collector_review_items`: base de revisão, separada dos anúncios operacionais.
- `data/snapshots/*.html` e `*.metadata.json`: capturas locais e metadados de origem, fora do Git.

Todos os registros permanecem `review_status=pending` e `publication_status=not_published`.
Nenhuma foto, descrição completa ou contato foi publicado no frontend. As capturas brutas
contêm conteúdo de terceiros e devem permanecer locais; os testes usam exemplos sintéticos.

Para reconstruir a comparação sem gastar créditos nem acessar a rede:

```powershell
.\.venv\Scripts\python.exe -m alugai review-snapshots --limit 20
```

O comando usa os arquivos `olx.html`, `vivareal.html` e `ponta_negra.html` em
`data/snapshots/`. Se um estiver ausente, registra `missing_snapshot`. Reimportar
atualiza por fonte/ID, sem duplicar registros, e recoloca os itens em revisão.
O transporte e agendamento regulares ainda são específicos da OLX; os adaptadores
novos de Viva Real e Ponta Negra foram integrados ao fluxo de amostras salvas.
O parser de detalhes ainda requer uma etapa própria de validação.

## Fontes da amostra

- https://www.olx.com.br/imoveis/aluguel/estado-am/regiao-de-manaus/manaus
- https://www.vivareal.com.br/aluguel/amazonas/manaus/
- https://www.pontanegraimoveis.com.br/imobiliaria/imoveis/0/1

As regras robots dos sites foram consultadas antes desta coleta. Elas não substituem
as condições de reutilização comercial de anúncios e mídias. A fonte e o link original
são preservados em cada referência da base de revisão.
