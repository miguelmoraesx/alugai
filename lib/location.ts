export type Coordinates = {
  latitude: number
  longitude: number
}

export type PlaceCategory = "health" | "education" | "grocery" | "leisure" | "transport"

export type UsefulPlace = Coordinates & {
  id: string
  name: string
  city: SupportedCity
  category: PlaceCategory
}

export type TravelMode = "walking" | "cycling" | "motorcycle" | "driving"

export type SupportedCity =
  | "Manaus"
  | "Iranduba"
  | "Manacapuru"
  | "Careiro da Várzea"
  | "Rio Preto da Eva"
  | "Presidente Figueiredo"

export type RankedPlace = UsefulPlace & {
  distanceKm: number
  score: number
  reason: string
}

export const categoryLabels: Record<PlaceCategory, string> = {
  health: "Saúde",
  education: "Educação",
  grocery: "Compras",
  leisure: "Lazer",
  transport: "Transporte",
}

export const supportedCities: SupportedCity[] = [
  "Manaus",
  "Iranduba",
  "Manacapuru",
  "Careiro da Várzea",
  "Rio Preto da Eva",
  "Presidente Figueiredo",
]

// Coordenadas consultadas no OpenStreetMap/Nominatim em 05/11/2026.
// Este catálogo é demonstrativo e deve ser substituído por dados persistidos e revisados.
export const usefulPlaces: UsefulPlace[] = [
  { id: "hps-28-agosto", name: "Hospital e Pronto-Socorro 28 de Agosto", city: "Manaus", category: "health", latitude: -3.1018136, longitude: -60.0141253 },
  { id: "huggv", name: "Hospital Universitário Getúlio Vargas", city: "Manaus", category: "health", latitude: -3.1164416, longitude: -60.018887 },
  { id: "ufam", name: "Universidade Federal do Amazonas", city: "Manaus", category: "education", latitude: -3.1010014, longitude: -59.9828251 },
  { id: "uea-est", name: "Escola Superior de Tecnologia — UEA", city: "Manaus", category: "education", latitude: -3.0919189, longitude: -60.0179361 },
  { id: "ifam-centro", name: "Instituto Federal do Amazonas — Centro", city: "Manaus", category: "education", latitude: -3.1338238, longitude: -60.0127666 },
  { id: "db-ponta-negra", name: "Supermercado DB Ponta Negra", city: "Manaus", category: "grocery", latitude: -3.0896116, longitude: -60.0564503 },
  { id: "mercado-adolpho-lisboa", name: "Mercado Municipal Adolpho Lisboa", city: "Manaus", category: "grocery", latitude: -3.1399498, longitude: -60.02355 },
  { id: "parque-mindu", name: "Parque Municipal do Mindú", city: "Manaus", category: "leisure", latitude: -3.0810263, longitude: -60.0033728 },
  { id: "aeroporto-eduardo-gomes", name: "Aeroporto Internacional de Manaus", city: "Manaus", category: "transport", latitude: -3.0356561, longitude: -60.0459675 },
]

const MANAUS_CENTER: Coordinates = { latitude: -3.119, longitude: -60.0217 }
const MAX_SERVICE_RADIUS_KM = 150
const EARTH_RADIUS_KM = 6371.0088

const travelSettings: Record<TravelMode, { speedKmH: number; routeFactor: number }> = {
  walking: { speedKmH: 4.8, routeFactor: 1.2 },
  cycling: { speedKmH: 14, routeFactor: 1.25 },
  motorcycle: { speedKmH: 28, routeFactor: 1.3 },
  driving: { speedKmH: 24, routeFactor: 1.35 },
}

function toRadians(value: number) {
  return value * Math.PI / 180
}

export function distanceKm(from: Coordinates, to: Coordinates) {
  const latitudeDelta = toRadians(to.latitude - from.latitude)
  const longitudeDelta = toRadians(to.longitude - from.longitude)
  const fromLatitude = toRadians(from.latitude)
  const toLatitude = toRadians(to.latitude)
  const haversine = Math.sin(latitudeDelta / 2) ** 2
    + Math.cos(fromLatitude) * Math.cos(toLatitude) * Math.sin(longitudeDelta / 2) ** 2

  return 2 * EARTH_RADIUS_KM * Math.asin(Math.sqrt(haversine))
}

export function estimateTravel(from: Coordinates, to: Coordinates, mode: TravelMode) {
  const directDistanceKm = distanceKm(from, to)
  const settings = travelSettings[mode]
  const estimatedRouteKm = directDistanceKm * settings.routeFactor
  const minutes = Math.max(1, Math.round(estimatedRouteKm / settings.speedKmH * 60))

  return { directDistanceKm, estimatedRouteKm, minutes }
}

export function validateDestination(destination: Coordinates & { city: string }) {
  if (!Number.isFinite(destination.latitude) || destination.latitude < -90 || destination.latitude > 90) {
    return { valid: false, error: "Latitude inválida." } as const
  }
  if (!Number.isFinite(destination.longitude) || destination.longitude < -180 || destination.longitude > 180) {
    return { valid: false, error: "Longitude inválida." } as const
  }
  if (!supportedCities.includes(destination.city as SupportedCity)) {
    return { valid: false, error: "Escolha Manaus ou um município próximo atendido." } as const
  }
  if (distanceKm(MANAUS_CENTER, destination) > MAX_SERVICE_RADIUS_KM) {
    return { valid: false, error: "O ponto informado fica fora da região atendida." } as const
  }
  return { valid: true } as const
}

export function rankNearbyPlaces(
  origin: Coordinates,
  preferredCategories: PlaceCategory[] = [],
  limit = 5,
  maxDistanceKm = 25,
): RankedPlace[] {
  return usefulPlaces
    .map((place) => {
      const placeDistanceKm = distanceKm(origin, place)
      const preferred = preferredCategories.includes(place.category)
      const score = Math.max(0, 100 - placeDistanceKm * 7) + (preferred ? 25 : 0)
      return {
        ...place,
        distanceKm: placeDistanceKm,
        score,
        reason: preferred ? `${categoryLabels[place.category]} é prioridade para você` : `${categoryLabels[place.category]} perto do imóvel`,
      }
    })
    .filter((place) => place.distanceKm <= maxDistanceKm)
    .sort((left, right) => right.score - left.score || left.distanceKm - right.distanceKm)
    .slice(0, Math.max(0, limit))
}
