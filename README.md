# Alugaí

Metabuscador regional de aluguel residencial em Manaus. O MVP reúne imóveis anunciados por proprietários, corretores e plataformas externas, permitindo comparar localização e custo mensal em uma única interface.

## Funcionalidades

- Busca por bairro, zona e pontos de interesse de Manaus
- Filtros rápidos para UFAM, UEA, Polo Industrial e regiões da cidade
- Mapa interativo com carregamento sob demanda
- Identificação da origem e do tipo de anunciante
- Comparação entre aluguel e custo mensal total
- Galeria de fotos e detalhes do imóvel
- Contato pelo WhatsApp com o código do anúncio
- Layout responsivo para celular e desktop

Os imóveis atuais são dados demonstrativos. Integrações com fontes externas e persistência de anúncios fazem parte das próximas etapas do produto.

## Tecnologias

- [Next.js](https://nextjs.org/) com App Router
- [React](https://react.dev/) e TypeScript
- [Tailwind CSS](https://tailwindcss.com/)
- Componentes baseados em [shadcn/ui](https://ui.shadcn.com/)
- [Leaflet](https://leafletjs.com/) e OpenStreetMap
- [Lucide](https://lucide.dev/) para ícones

## Executando localmente

Requisitos:

- Node.js 20.9 ou mais recente
- npm 10 ou mais recente

```bash
git clone https://github.com/miguelmoraesx/alugai.git
cd alugai
npm install
npm run dev
```

A aplicação ficará disponível em `http://localhost:3000`.

## Scripts

```bash
npm run dev      # ambiente de desenvolvimento
npm run build    # build de produção
npm run start    # executa o build de produção
npm run lint     # análise estática do código
```

## Estrutura principal

```text
app/                  rotas, layout e estilos globais
components/           componentes da interface
components/ui/        componentes reutilizáveis
hooks/                hooks compartilhados
lib/properties.ts     tipos e dados demonstrativos dos imóveis
lib/utils.ts          utilitários da aplicação
public/               arquivos estáticos
```

## Fluxo de colaboração

Para evitar conflitos na branch principal:

1. Atualize sua cópia local com `git pull`.
2. Crie uma branch a partir de `main`: `git switch -c feat/nome-da-tarefa`.
3. Faça commits pequenos e descritivos.
4. Envie a branch: `git push -u origin feat/nome-da-tarefa`.
5. Abra um Pull Request para revisão.

Sugestões de prefixos: `feat/`, `fix/`, `refactor/`, `docs/` e `chore/`.

## Deploy

O projeto é uma aplicação Next.js padrão e não depende de uma plataforma específica de hospedagem.

### Vercel

1. Importe este repositório na Vercel.
2. Mantenha o framework detectado como `Next.js`.
3. Use `npm run build` como comando de build.
4. Publique o projeto.

Não há variáveis de ambiente obrigatórias nesta versão do MVP.

### Outras plataformas

Qualquer serviço com suporte a Node.js pode executar:

```bash
npm install
npm run build
npm run start
```

Para hospedagem totalmente estática será necessário adaptar os recursos de servidor do Next.js ou configurar exportação estática quando a arquitetura do produto permitir.

## Próximos passos

- API e banco de dados para anúncios reais
- Cadastro e autenticação de anunciantes
- Moderação e prevenção de anúncios duplicados
- Geocodificação dos endereços
- Favoritos persistentes
- Paginação e ordenação dos resultados
- Testes automatizados

## Licença

Este projeto ainda não possui uma licença de uso definida.
