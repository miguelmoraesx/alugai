export type Property = {
  id: string
  title: string
  neighborhood: string
  rent: number
  condo: number
  iptu: number
  bedrooms: number
  bathrooms: number
  parkingSpaces: number
  area: number
  petFriendly: boolean
  source: string
  sourceLabel: string
  advertiser: "owner" | "broker" | "aggregated"
  latitude: number
  longitude: number
  zones: string[]
  images: string[]
}

const image = (id: string) =>
  `https://images.unsplash.com/${id}?auto=format&fit=crop&w=1200&q=82`

export const properties: Property[] = [
  {
    id: "ALG-1042", title: "Apê 1 Quarto", neighborhood: "Parque 10 de Novembro",
    rent: 1800, condo: 300, iptu: 80, bedrooms: 1, bathrooms: 1, parkingSpaces: 1, area: 46, petFriendly: true,
    source: "OLX", sourceLabel: "Agregado via OLX Manaus", advertiser: "broker", latitude: -3.0839, longitude: -59.9923, zones: ["region-centro-sul", "uea"],
    images: [image("photo-1600566753190-17f0baa2a6c3"), image("photo-1600607687920-4e2a09cf159d"), image("photo-1600210492486-724fe5c67fb0")],
  },
  {
    id: "ALG-2087", title: "Kitnet Mobiliada", neighborhood: "Coroado",
    rent: 950, condo: 0, iptu: 0, bedrooms: 1, bathrooms: 1, parkingSpaces: 0, area: 28, petFriendly: false,
    source: "Alugaí", sourceLabel: "Direto com a proprietária", advertiser: "owner", latitude: -3.1172, longitude: -59.9748, zones: ["region-leste", "ufam"],
    images: [image("photo-1600573472550-8090b5e0745e"), image("photo-1600566753051-f0b89df2dd90"), image("photo-1600566753086-00f18fb6b3ea")],
  },
  {
    id: "ALG-3184", title: "Apê 2 Quartos", neighborhood: "Flores",
    rent: 2200, condo: 450, iptu: 100, bedrooms: 2, bathrooms: 2, parkingSpaces: 1, area: 68, petFriendly: true,
    source: "Loft", sourceLabel: "Agregado via Loft", advertiser: "broker", latitude: -3.0525, longitude: -60.013, zones: ["region-norte", "uea"],
    images: [image("photo-1600607687939-ce8a6c25118c"), image("photo-1600585152915-d208bec867a1"), image("photo-1600566753190-17f0baa2a6c3")],
  },
  {
    id: "ALG-4231", title: "Apê Compacto", neighborhood: "Japiim",
    rent: 1200, condo: 150, iptu: 50, bedrooms: 1, bathrooms: 1, parkingSpaces: 0, area: 38, petFriendly: true,
    source: "Alugaí", sourceLabel: "Direto com o proprietário", advertiser: "owner", latitude: -3.1285, longitude: -59.993, zones: ["region-sul", "ufam", "pim"],
    images: [image("photo-1600566753086-00f18fb6b3ea"), image("photo-1600210492486-724fe5c67fb0"), image("photo-1600573472550-8090b5e0745e")],
  },
  {
    id: "ALG-5019", title: "Casa em Condomínio", neighborhood: "Ponta Negra",
    rent: 4500, condo: 800, iptu: 250, bedrooms: 4, bathrooms: 4, parkingSpaces: 2, area: 210, petFriendly: true,
    source: "Alugaí", sourceLabel: "Direto com o proprietário", advertiser: "owner", latitude: -3.075, longitude: -60.105, zones: ["region-oeste"],
    images: [image("photo-1600585154340-be6161a56a0c"), image("photo-1600607687920-4e2a09cf159d"), image("photo-1600585152915-d208bec867a1")],
  },
  {
    id: "ALG-6126", title: "Studio Executivo", neighborhood: "Centro",
    rent: 1600, condo: 250, iptu: 60, bedrooms: 1, bathrooms: 1, parkingSpaces: 1, area: 34, petFriendly: false,
    source: "OLX", sourceLabel: "Agregado via OLX Manaus", advertiser: "broker", latitude: -3.134, longitude: -60.024, zones: ["region-sul"],
    images: [image("photo-1600566753051-f0b89df2dd90"), image("photo-1600573472550-8090b5e0745e"), image("photo-1600607687939-ce8a6c25118c")],
  },
  {
    id: "ALG-7340", title: "Apê 2 Quartos", neighborhood: "Novo Aleixo",
    rent: 1400, condo: 200, iptu: 50, bedrooms: 2, bathrooms: 1, parkingSpaces: 1, area: 57, petFriendly: true,
    source: "Imóvelweb", sourceLabel: "Agregado via Imóvelweb", advertiser: "aggregated", latitude: -3.055, longitude: -59.962, zones: ["region-norte"],
    images: [image("photo-1600210492486-724fe5c67fb0"), image("photo-1600566753190-17f0baa2a6c3"), image("photo-1600566753086-00f18fb6b3ea")],
  },
  {
    id: "ALG-8465", title: "Apê 1 Quarto", neighborhood: "Santo Antônio",
    rent: 1100, condo: 100, iptu: 40, bedrooms: 1, bathrooms: 1, parkingSpaces: 0, area: 40, petFriendly: false,
    source: "Alugaí", sourceLabel: "Direto com o proprietário", advertiser: "owner", latitude: -3.123, longitude: -60.048, zones: ["region-oeste"],
    images: [image("photo-1600585152915-d208bec867a1"), image("photo-1600607687920-4e2a09cf159d"), image("photo-1600566753051-f0b89df2dd90")],
  },
]

export const quickFilters = [
  { id: "region-norte", label: "Zona Norte", emoji: "🧭" },
  { id: "region-sul", label: "Zona Sul", emoji: "🌇" },
  { id: "region-leste", label: "Zona Leste", emoji: "🌅" },
  { id: "region-centro-sul", label: "Centro-Sul", emoji: "📍" },
  { id: "region-oeste", label: "Zona Oeste", emoji: "🌊" },
  { id: "ufam", label: "Perto da UFAM", emoji: "🎓" },
  { id: "uea", label: "Perto da UEA", emoji: "🏛️" },
  { id: "pim", label: "Polo Industrial / PIM", emoji: "🏭" },
  { id: "owner", label: "Direto com proprietário", emoji: "🔑" },
]
