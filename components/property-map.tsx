"use client"

import { useEffect, useRef, useState } from "react"
import type { Map as MapLibreMap, Marker as MapLibreMarker } from "maplibre-gl"
import { MapPin, Navigation } from "lucide-react"
import type { Property } from "@/lib/properties"
import { Button } from "@/components/ui/button"

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })

export function PropertyMap({ properties }: { properties: Property[] }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const libraryRef = useRef<typeof import("maplibre-gl") | null>(null)
  const markersRef = useRef<MapLibreMarker[]>([])
  const [mapReady, setMapReady] = useState(false)
  const [selected, setSelected] = useState<Property | null>(properties[0] ?? null)
  const activeProperty = properties.find((property) => property.id === selected?.id) ?? properties[0] ?? null

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    let cancelled = false

    async function createMap() {
      const maplibregl = await import("maplibre-gl")
      if (cancelled || !containerRef.current) return
      libraryRef.current = maplibregl

      const map = new maplibregl.Map({
        container: containerRef.current,
        center: [-60.01, -3.095],
        zoom: 11.25,
        minZoom: 9,
        maxZoom: 17,
        attributionControl: false,
        style: {
          version: 8,
          sources: {
            osm: {
              type: "raster",
              tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
              tileSize: 256,
              attribution: "© OpenStreetMap contributors",
            },
          },
          layers: [{ id: "osm", type: "raster", source: "osm" }],
        },
      })

      map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right")
      map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right")

      const ufam = document.createElement("div")
      ufam.className = "alugai-landmark"
      ufam.innerHTML = "<span>🎓</span><strong>UFAM</strong>"
      new maplibregl.Marker({ element: ufam, anchor: "bottom" }).setLngLat([-59.9797, -3.1021]).addTo(map)

      mapRef.current = map
      setMapReady(true)
    }

    createMap()
    return () => {
      cancelled = true
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!mapReady || !mapRef.current || !libraryRef.current) return
    const maplibregl = libraryRef.current
    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current = []

    properties.forEach((property) => {
      const marker = document.createElement("button")
      marker.type = "button"
      marker.className = `alugai-map-marker alugai-map-marker--${property.advertiser}`
      marker.setAttribute("aria-label", `Ver ${property.title} em ${property.neighborhood}`)
      marker.innerHTML = `<span>${money.format(property.rent).replace("R$ ", "R$ ")}</span>`
      marker.addEventListener("click", () => {
        setSelected(property)
        mapRef.current?.flyTo({ center: [property.longitude, property.latitude], zoom: 14, essential: true })
      })

      markersRef.current.push(
        new maplibregl.Marker({ element: marker, anchor: "bottom" })
          .setLngLat([property.longitude, property.latitude])
          .addTo(mapRef.current!),
      )
    })

    if (properties.length > 0) {
      const bounds = new maplibregl.LngLatBounds()
      properties.forEach((property) => bounds.extend([property.longitude, property.latitude]))
      mapRef.current.fitBounds(bounds, { padding: 70, maxZoom: 13, duration: 700 })
    }
  }, [mapReady, properties])

  return (
    <div className="sticky top-[98px] overflow-hidden rounded-[30px] border-2 border-[#063f2e]/15 bg-[#FBF7EB] shadow-[0_10px_0_rgba(6,63,46,.06)]">
      <div className="flex items-center justify-between gap-3 border-b border-[#063f2e]/10 px-5 py-4">
        <div><p className="flex items-center gap-2 text-sm font-black text-[#063f2e]"><Navigation className="size-4 fill-[#FFB72B]" /> Explore pelo mapa</p><p className="mt-0.5 text-[11px] text-[#60776e]">Arraste, aproxime e toque nos valores.</p></div>
        <div className="hidden gap-3 text-[9px] font-bold text-[#526d63] sm:flex"><Legend color="#FFB72B" label="Proprietário" /><Legend color="#0F7352" label="Corretor" /><Legend color="#6C7B76" label="Agregado" /></div>
      </div>
      <div className="relative">
        <div ref={containerRef} className="h-[470px] w-full bg-[#E8E4D8] xl:h-[650px]" aria-label="Mapa de imóveis disponíveis em Manaus" />
        {activeProperty && (
          <div className="absolute inset-x-3 bottom-3 rounded-[22px] border border-white/70 bg-[#FFFDF7]/95 p-4 shadow-xl backdrop-blur-md">
            <div className="flex items-start justify-between gap-3">
              <div><p className="text-[10px] font-black uppercase tracking-[.12em] text-[#C57C00]">{activeProperty.neighborhood}</p><p className="mt-1 font-black text-[#063f2e]">{activeProperty.title}</p><p className="mt-1 text-xs text-[#60776e]">{activeProperty.advertiser === "owner" ? "Direto com o proprietário" : activeProperty.advertiser === "broker" ? "Corretor com CRECI verificado" : activeProperty.sourceLabel}</p></div>
              <div className="text-right"><p className="text-lg font-black text-[#063f2e]">{money.format(activeProperty.rent)}</p><p className="text-[10px] text-[#60776e]">aluguel / mês</p></div>
            </div>
            <Button asChild className="mt-3 h-9 w-full rounded-full bg-[#063f2e] text-xs font-extrabold hover:bg-[#0B513B]"><a href={`#${activeProperty.id}`}>Ver detalhes deste imóvel</a></Button>
          </div>
        )}
        {!mapReady && <div className="absolute inset-0 flex items-center justify-center bg-[#E8E4D8]"><div className="flex items-center gap-2 text-sm font-bold text-[#315a4c]"><MapPin className="size-5 animate-bounce fill-[#FFB72B]" /> Abrindo o mapa de Manaus…</div></div>}
      </div>
    </div>
  )
}

function Legend({ color, label }: { color: string; label: string }) {
  return <span className="flex items-center gap-1"><span className="size-2 rounded-full" style={{ backgroundColor: color }} />{label}</span>
}
