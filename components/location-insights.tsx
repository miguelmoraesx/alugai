"use client"

import { useMemo, useState, type FormEvent } from "react"
import { Bike, CarFront, Footprints, Gauge, GraduationCap, HeartPulse, MapPin, Navigation, ShoppingBasket, Sparkles, Trees } from "lucide-react"
import type { Property } from "@/lib/properties"
import {
  categoryLabels,
  estimateTravel,
  rankNearbyPlaces,
  supportedCities,
  usefulPlaces,
  validateDestination,
  type PlaceCategory,
  type TravelMode,
} from "@/lib/location"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

const categoryIcons = {
  health: HeartPulse,
  education: GraduationCap,
  grocery: ShoppingBasket,
  leisure: Trees,
  transport: Navigation,
} satisfies Record<PlaceCategory, typeof MapPin>

const modeLabels: Record<TravelMode, string> = {
  walking: "A pé",
  cycling: "Bicicleta",
  motorcycle: "Moto",
  driving: "Carro",
}

export function LocationInsights({ property }: { property: Property }) {
  const origin = useMemo(() => ({ latitude: property.latitude, longitude: property.longitude }), [property.latitude, property.longitude])
  const [preferredCategory, setPreferredCategory] = useState<PlaceCategory | "all">("all")
  const [destinationId, setDestinationId] = useState(usefulPlaces[0].id)
  const [mode, setMode] = useState<TravelMode>("driving")
  const [custom, setCustom] = useState(false)
  const [customDestination, setCustomDestination] = useState({ name: "", city: "Manaus", latitude: "", longitude: "" })
  const [customResult, setCustomResult] = useState<{ name: string; latitude: number; longitude: number } | null>(null)
  const [error, setError] = useState("")
  const nearby = useMemo(() => rankNearbyPlaces(origin, preferredCategory === "all" ? [] : [preferredCategory], 4), [origin, preferredCategory])
  const selectedPlace = usefulPlaces.find((place) => place.id === destinationId) ?? usefulPlaces[0]
  const destination = custom && customResult ? customResult : selectedPlace
  const travel = estimateTravel(origin, destination, mode)

  const updateCustomDestination = (field: keyof typeof customDestination, value: string) => {
    setCustomDestination((current) => ({ ...current, [field]: value }))
    setCustomResult(null)
    setError("")
  }

  const calculateCustomDestination = (event: FormEvent) => {
    event.preventDefault()
    const latitude = Number(customDestination.latitude.replace(",", "."))
    const longitude = Number(customDestination.longitude.replace(",", "."))
    const validation = validateDestination({ latitude, longitude, city: customDestination.city })
    if (!customDestination.name.trim()) {
      setCustomResult(null)
      setError("Dê um nome ao destino, como Trabalho ou Escola.")
      return
    }
    if (!validation.valid) {
      setCustomResult(null)
      setError(validation.error)
      return
    }
    setCustomResult({ name: customDestination.name.trim(), latitude, longitude })
    setError("")
  }

  return (
    <section className="mt-5 rounded-[22px] border border-[#063f2e]/10 bg-[#F4F0E4] p-4" aria-labelledby={`location-title-${property.id}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="flex items-center gap-1.5 text-[10px] font-black uppercase tracking-[.12em] text-[#C57C00]"><Sparkles className="size-3.5" /> Vida ao redor</p>
          <h3 id={`location-title-${property.id}`} className="mt-1 font-black text-[#063f2e]">O que fica perto deste imóvel</h3>
        </div>
        <Select value={preferredCategory} onValueChange={(value) => setPreferredCategory(value as PlaceCategory | "all")}>
          <SelectTrigger className="h-9 w-[135px] rounded-xl bg-white text-xs font-bold"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tudo</SelectItem>
            {Object.entries(categoryLabels).map(([value, label]) => <SelectItem key={value} value={value}>{label}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      <div className="mt-3 grid gap-2 sm:grid-cols-2">
        {nearby.map((place) => {
          const Icon = categoryIcons[place.category]
          return <div key={place.id} className="rounded-2xl bg-white px-3 py-2.5"><div className="flex items-start gap-2"><span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-full bg-[#FFB72B]/25"><Icon className="size-3.5 text-[#0F7352]" /></span><div className="min-w-0"><p className="truncate text-xs font-extrabold text-[#315a4c]" title={place.name}>{place.name}</p><p className="mt-0.5 text-[10px] text-[#71837c]">{place.distanceKm.toFixed(1).replace(".", ",")} km em linha reta · {place.reason}</p></div></div></div>
        })}
      </div>

      <details className="mt-4 border-t border-dashed border-[#063f2e]/15 pt-3">
        <summary className="cursor-pointer text-xs font-extrabold text-[#0F7352]">Calcular até trabalho, faculdade ou escola</summary>
        <div className="mt-3">
          <div className="flex gap-2">
            <Button type="button" size="sm" variant={!custom ? "default" : "outline"} onClick={() => { setCustom(false); setError("") }} className="h-8 rounded-full text-xs">Lugar conhecido</Button>
            <Button type="button" size="sm" variant={custom ? "default" : "outline"} onClick={() => { setCustom(true); setError("") }} className="h-8 rounded-full text-xs">Meu ponto</Button>
          </div>

          {!custom ? (
            <Select value={destinationId} onValueChange={setDestinationId}>
              <SelectTrigger className="mt-3 h-10 w-full rounded-xl bg-white text-xs font-bold"><SelectValue /></SelectTrigger>
              <SelectContent>{usefulPlaces.map((place) => <SelectItem key={place.id} value={place.id}>{place.name}</SelectItem>)}</SelectContent>
            </Select>
          ) : (
            <form onSubmit={calculateCustomDestination} className="mt-3 grid gap-2 sm:grid-cols-2">
              <Input value={customDestination.name} onChange={(event) => updateCustomDestination("name", event.target.value)} placeholder="Nome: Trabalho" aria-label="Nome do destino" className="h-10 rounded-xl bg-white text-xs" />
              <Select value={customDestination.city} onValueChange={(city) => updateCustomDestination("city", city)}>
                <SelectTrigger className="h-10 w-full rounded-xl bg-white text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>{supportedCities.map((city) => <SelectItem key={city} value={city}>{city}</SelectItem>)}</SelectContent>
              </Select>
              <Input value={customDestination.latitude} onChange={(event) => updateCustomDestination("latitude", event.target.value)} inputMode="decimal" placeholder="Latitude: -3,10" aria-label="Latitude do destino" className="h-10 rounded-xl bg-white text-xs" />
              <Input value={customDestination.longitude} onChange={(event) => updateCustomDestination("longitude", event.target.value)} inputMode="decimal" placeholder="Longitude: -60,02" aria-label="Longitude do destino" className="h-10 rounded-xl bg-white text-xs" />
              <Button type="submit" className="h-9 rounded-full text-xs sm:col-span-2">Calcular meu trajeto</Button>
            </form>
          )}
          {error && <p role="alert" className="mt-2 text-xs font-bold text-red-700">{error}</p>}

          <div className="mt-3 flex flex-wrap gap-1.5" aria-label="Meio de transporte">
            {(["walking", "cycling", "motorcycle", "driving"] as TravelMode[]).map((travelMode) => {
              const Icon = travelMode === "walking" ? Footprints : travelMode === "cycling" ? Bike : travelMode === "motorcycle" ? Gauge : CarFront
              return <button key={travelMode} type="button" onClick={() => setMode(travelMode)} aria-pressed={mode === travelMode} className={`flex items-center gap-1 rounded-full px-2.5 py-1.5 text-[10px] font-bold ${mode === travelMode ? "bg-[#063f2e] text-white" : "bg-white text-[#526d63]"}`}><Icon className="size-3" />{modeLabels[travelMode]}</button>
            })}
          </div>

          {(!custom || customResult) && <div className="mt-3 rounded-2xl bg-[#063f2e] p-3 text-white">
            <p className="truncate text-xs font-extrabold" title={destination.name}>{property.neighborhood} → {destination.name}</p>
            <p className="mt-1 text-xl font-black text-[#FFB72B]">cerca de {travel.minutes} min</p>
            <p className="mt-1 text-[10px] text-white/70">{travel.directDistanceKm.toFixed(1).replace(".", ",")} km em linha reta · estimativa por velocidade média, sem trânsito ou rota viária</p>
          </div>}
        </div>
      </details>
    </section>
  )
}
