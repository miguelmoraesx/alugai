# Validação de detalhes e integração do catálogo

## Estado do código

A branch `codex/olx-collector` incorpora a atualização `7d5ac7f` da `origin/main`,
que melhora mapa, cartões e diálogo de detalhes. O frontend ainda usa o array
demonstrativo de `lib/properties.ts`; a coleta fica em tabelas separadas.

## Primeiro detalhe conferido

Foi consultada pelo plugin Firecrawl a página do
[anúncio 2910061859 no Viva Real](https://www.vivareal.com.br/imovel/apartamento-3-quartos-sao-jorge-bairros-manaus-com-garagem-76m2-aluguel-RS5500-id-2910061859/).
A resposta HTTP 200 permitiu conferir aluguel mensal de R$ 5.500, área de 76 m²,
três quartos, três banheiros e duas vagas. O condomínio aparece como isento,
o IPTU como não informado e a página indica que aceita animais.

Há uma divergência: localização e título indicam São Jorge, enquanto a descrição
indica Dom Pedro. O registro precisa de revisão; nenhuma coordenada foi inferida.
O resumo da inspeção fica em `data/review/detail-validation-vivareal.json`, fora do Git.
Essa inspeção pontual não implementa um parser de detalhes nem comprova disponibilidade.
Os 52 registros da comparação continuam pendentes e não publicados.

## Adaptações necessárias antes de ligar o catálogo real

O tipo `Property` atual exige valores numéricos para condomínio, IPTU, latitude e
longitude, além de booleano para animais. As fontes frequentemente não informam
esses campos. A integração deve permitir valores desconhecidos e preservar:

- Fonte, ID externo, URL original, instante de coleta e escopo da observação.
- Diferença entre taxa isenta, incluída, desconhecida ou com valor suspeito.
- Periodicidade do IPTU; não apresentar total mensal se ela ou alguma taxa faltar.
- Estado desconhecido para aceitação de animais; ausência não significa proibição.
- Coordenadas ausentes; o anúncio pode entrar na lista sem marcador no mapa.
- Imagem ausente, com apresentação neutra em vez de fotos demonstrativas.
- Revisão e publicação separadas, sem promover registros apenas porque a página abriu.

O próximo incremento de código é um adaptador de detalhes com testes sintéticos,
seguido de um contrato de catálogo que represente essas ausências. A amostra de uma
página não permite afirmar que o adaptador funcionará em todos os anúncios.
