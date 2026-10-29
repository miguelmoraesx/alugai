export type Property = {
  id: string
  title: string
  neighborhood: string
  rent: number
  condo: number
  iptu: number
  bedrooms: number
  bathrooms: number
  area: number
  petFriendly: boolean
  source: string
  sourceLabel: string
  zones: string[]
  images: string[]
}

const image = (id: string) =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=1200&q=82`

export const properties: Property[] = [
  {
    id: "ALG-1042", title: "Apê 1 Quarto", neighborhood: "Parque 10 de Novembro",
    rent: 1800, condo: 300, iptu: 80, bedrooms: 1, bathrooms: 1, area: 46, petFriendly: true,
    source: "OLX", sourceLabel: "Agregado via OLX Manaus", zones: ["uea", "parque-10"],
    images: [image("photo-1600566753190-17f0baa2a6c3"), image("photo-1600607687920-4e2a09cf159d"), image("photo-1600210492486-724fe5c67fb0")],
  },
  {
    id: "ALG-2087", title: "Kitnet Mobiliada", neighborhood: "Coroado",
    rent: 950, condo: 0, iptu: 0, bedrooms: 1, bathrooms: 1, area: 28, petFriendly: false,
    source: "Imóvelweb", sourceLabel: "Agregado via Imóvelweb", zones: ["ufam"],
    images: [image("photo-1600573472550-8090b5e0745e"), image("photo-1600566753051-f0b89df2dd90"), image("photo-1600566753086-00f18fb6b3ea")],
  },
  {
    id: "ALG-3184", title: "Apê 2 Quartos", neighborhood: "Flores",
    rent: 2200, condo: 450, iptu: 100, bedrooms: 2, bathrooms: 2, area: 68, petFriendly: true,
    source: "Loft", sourceLabel: "Agregado via Loft", zones: ["uea"],
    images: [image("photo-1600607687939-ce8a6c25118c"), image("photo-1600585152915-d208bec867a1"), image("photo-1600566753190-17f0baa2a6c3")],
  },
  {
    id: "ALG-4231", title: "Apê Compacto", neighborhood: "Japiim",
    rent: 1200, condo: 150, iptu: 50, bedrooms: 1, bathrooms: 1, area: 38, petFriendly: true,
    source: "OLX", sourceLabel: "Agregado via OLX Manaus", zones: ["ufam", "pim"],
    images: [image("photo-1600566753086-00f18fb6b3ea"), image("photo-1600210492486-724fe5c67fb0"), image("photo-1600573472550-8090b5e0745e")],
  },
  {
    id: "ALG-5019", title: "Casa em Condomínio", neighborhood: "Ponta Negra",
    rent: 4500, condo: 800, iptu: 250, bedrooms: 4, bathrooms: 4, area: 210, petFriendly: true,
    source: "Alugaí", sourceLabel: "Direto no Alugaí", zones: ["ponta-negra"],
    images: [image("photo-1600585154340-be6161a56a0c"), image("photo-1600607687920-4e2a09cf159d"), image("photo-1600585152915-d208bec867a1")],
  },
  {
    id: "ALG-6126", title: "Studio Executivo", neighborhood: "Centro",
    rent: 1600, condo: 250, iptu: 60, bedrooms: 1, bathrooms: 1, area: 34, petFriendly: false,
    source: "OLX", sourceLabel: "Agregado via OLX Manaus", zones: [],
    images: [image("photo-1600566753051-f0b89df2dd90"), image("photo-1600573472550-8090b5e0745e"), image("photo-1600607687939-ce8a6c25118c")],
  },
  {
    id: "ALG-7340", title: "Apê 2 Quartos", neighborhood: "Novo Aleixo",
    rent: 1400, condo: 200, iptu: 50, bedrooms: 2, bathrooms: 1, area: 57, petFriendly: true,
    source: "Imóvelweb", sourceLabel: "Agregado via Imóvelweb", zones: ["ufam"],
    images: [image("photo-1600210492486-724fe5c67fb0"), image("photo-1600566753190-17f0baa2a6c3"), image("photo-1600566753086-00f18fb6b3ea")],
  },
  {
    id: "ALG-8465", title: "Apê 1 Quarto", neighborhood: "Santo Antônio",
    rent: 1100, condo: 100, iptu: 40, bedrooms: 1, bathrooms: 1, area: 40, petFriendly: false,
    source: "OLX", sourceLabel: "Agregado via OLX Manaus", zones: [],
    images: [image("photo-1600585152915-d208bec867a1"), image("photo-1600607687920-4e2a09cf159d"), image("photo-1600566753051-f0b89df2dd90")],
  },
]

export const quickFilters = [
  { id: "ufam", label: "Perto da UFAM", emoji: "🎓" },
  { id: "uea", label: "Perto da UEA", emoji: "🏛️" },
  { id: "pim", label: "Polo Industrial / PIM", emoji: "🏭" },
  { id: "parque-10", label: "Parque 10", emoji: "📍" },
  { id: "ponta-negra", label: "Ponta Negra", emoji: "🌊" },
]
