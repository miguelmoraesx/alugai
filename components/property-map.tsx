"use client"

import { memo, useEffect, useRef, useState } from "react"
import type { Map as LeafletMap, Marker as LeafletMarker } from "leaflet"
import { MapPin, Navigation } from "lucide-react"
import type { Property } from "@/lib/properties"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })

export const PropertyMap = memo(function PropertyMap({ properties }: { properties: Property[] }) {
  const shellRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<LeafletMap | null>(null)
  const libraryRef = useRef<typeof import("leaflet") | null>(null)
  const markersRef = useRef<LeafletMarker[]>([])
  const [shouldLoad, setShouldLoad] = useState(false)
  const [mapReady, setMapReady] = useState(false)
  const [viewportReady, setViewportReady] = useState(false)
  const [isCompactViewport, setIsCompactViewport] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [selected, setSelected] = useState<Property | null>(properties[0] ?? null)
  const activeProperty = properties.find((property) => property.id === selected?.id) ?? properties[0] ?? null

  useEffect(() => {
    const media = window.matchMedia("(max-width: 1279px)")
    const updateViewport = () => {
      setIsCompactViewport(media.matches)
      setViewportReady(true)
    }
    updateViewport()
    media.addEventListener("change", updateViewport)
    return () => media.removeEventListener("change", updateViewport)
  }, [])

  useEffect(() => {
    if (!viewportReady || (isCompactViewport && !expanded)) return
    const shell = shellRef.current
    if (!shell) return
    if (!("IntersectionObserver" in window)) {
      queueMicrotask(() => setShouldLoad(true))
      return
    }

    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) {
        setShouldLoad(true)
        observer.disconnect()
      }
    }, { rootMargin: "80px" })
    observer.observe(shell)
    return () => observer.disconnect()
  }, [expanded, isCompactViewport, viewportReady])

  useEffect(() => {
    if (!shouldLoad || !containerRef.current || mapRef.current) return
    let cancelled = false

    async function createMap() {
      const L = await import("leaflet")
      if (cancelled || !containerRef.current) return
      libraryRef.current = L

      const map = L.map(containerRef.current, {
        center: [-3.095, -60.01],
        zoom: 11,
        minZoom: 9,
        maxZoom: 17,
        maxBounds: [[-3.35, -60.35], [-2.75, -59.65]],
        maxBoundsViscosity: 0.8,
        preferCanvas: true,
        zoomAnimation: false,
        fadeAnimation: false,
        markerZoomAnimation: false,
      })

      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
        maxZoom: 17,
        crossOrigin: true,
        detectRetina: false,
        updateWhenZooming: false,
        updateWhenIdle: false,
        updateInterval: 100,
        keepBuffer: 3,
      }).addTo(map)

      const ufamLabel = document.createElement("div")
      ufamLabel.className = "alugai-landmark"
      ufamLabel.innerHTML = "<span>🎓</span><strong>UFAM</strong>"
      const ufamIcon = L.divIcon({ className: "alugai-leaflet-marker-wrapper", html: ufamLabel, iconSize: [62, 28], iconAnchor: [31, 28] })
      L.marker([-3.1021, -59.9797], { icon: ufamIcon, title: "Universidade Federal do Amazonas" }).addTo(map)

      mapRef.current = map
      requestAnimationFrame(() => map.invalidateSize({ animate: false, pan: false }))
      setMapReady(true)
    }

    createMap()
    return () => {
      cancelled = true
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [shouldLoad])

  useEffect(() => {
    if (!mapReady || !expanded) return
    requestAnimationFrame(() => mapRef.current?.invalidateSize({ animate: false, pan: false }))
  }, [expanded, mapReady])

  useEffect(() => {
    const container = containerRef.current
    if (!mapReady || !container || !("ResizeObserver" in window)) return
    let animationFrame = 0
    const observer = new ResizeObserver(() => {
      cancelAnimationFrame(animationFrame)
      animationFrame = requestAnimationFrame(() => {
        mapRef.current?.invalidateSize({ animate: false, pan: false, debounceMoveend: true })
      })
    })
    observer.observe(container)
    return () => {
      cancelAnimationFrame(animationFrame)
      observer.disconnect()
    }
  }, [mapReady])

  useEffect(() => {
    if (!mapReady || !mapRef.current || !libraryRef.current) return
    const L = libraryRef.current
    markersRef.current.forEach((marker) => marker.remove())
    markersRef.current = []

    properties.forEach((property) => {
      const markerButton = document.createElement("button")
      markerButton.type = "button"
      markerButton.className = `alugai-map-marker alugai-map-marker--${property.advertiser}`
      markerButton.textContent = money.format(property.rent).replace("R$ ", "R$ ")
      const icon = L.divIcon({ className: "alugai-leaflet-marker-wrapper", html: markerButton, iconSize: [78, 36], iconAnchor: [39, 36] })
      const marker = L.marker([property.latitude, property.longitude], {
        icon,
        title: `Ver ${property.title} em ${property.neighborhood}`,
        keyboard: true,
      }).on("click", () => {
        setSelected(property)
        mapRef.current?.setView([property.latitude, property.longitude], 14, { animate: false })
      }).addTo(mapRef.current!)
      markersRef.current.push(marker)
    })

    if (properties.length > 0) {
      const bounds = L.latLngBounds(properties.map((property) => [property.latitude, property.longitude]))
      mapRef.current.fitBounds(bounds, { padding: [55, 55], maxZoom: 13, animate: false })
    }
  }, [mapReady, properties])

  return (
    <div ref={shellRef} className="overflow-hidden rounded-[30px] border-2 border-[#063f2e]/15 bg-[#FBF7EB] shadow-[0_10px_0_rgba(6,63,46,.06)] xl:sticky xl:top-[98px]">
      <div className="flex items-center justify-between gap-3 border-b border-[#063f2e]/10 px-5 py-4">
        <div><p className="flex items-center gap-2 text-sm font-black text-[#063f2e]"><Navigation className="size-4 fill-[#FFB72B]" /> Explore pelo mapa</p><p className="mt-0.5 text-[11px] text-[#60776e]">Arraste, aproxime e toque nos valores.</p></div>
        <div className="hidden gap-3 text-[9px] font-bold text-[#526d63] sm:flex"><Legend color="#FFB72B" label="Proprietário" /><Legend color="#0F7352" label="Corretor" /><Legend color="#6C7B76" label="Agregado" /></div>
      </div>
      <div className="relative">
        <div ref={containerRef} className={cn("w-full bg-[#E8E4D8] transition-[height] duration-300 xl:h-[650px]", expanded ? "h-[470px]" : "h-[170px]")} aria-label="Mapa de imóveis disponíveis em Manaus" />
        {activeProperty && mapReady && (!isCompactViewport || expanded) && (
          <div className="absolute inset-x-3 bottom-3 z-[500] rounded-[22px] border border-white/70 bg-[#FFFDF7]/95 p-4 shadow-xl backdrop-blur-md">
            <div className="flex items-start justify-between gap-3">
              <div><p className="text-[10px] font-black uppercase tracking-[.12em] text-[#C57C00]">{activeProperty.neighborhood}</p><p className="mt-1 font-black text-[#063f2e]">{activeProperty.title}</p><p className="mt-1 text-xs text-[#60776e]">{activeProperty.advertiser === "owner" ? "Direto com o proprietário" : activeProperty.advertiser === "broker" ? "Anunciado por corretor" : activeProperty.sourceLabel}</p></div>
              <div className="text-right"><p className="text-lg font-black text-[#063f2e]">{money.format(activeProperty.rent)}</p><p className="text-[10px] text-[#60776e]">aluguel / mês</p></div>
            </div>
            <Button asChild className="mt-3 h-9 w-full rounded-full bg-[#063f2e] text-xs font-extrabold hover:bg-[#0B513B]"><a href={`#${activeProperty.id}`}>Ver detalhes deste imóvel</a></Button>
          </div>
        )}
        {!mapReady && <div className="absolute inset-0 flex flex-col items-center justify-center overflow-hidden bg-[#E8E4D8] px-4 text-center"><div className="pointer-events-none absolute inset-0 opacity-35 [background-image:linear-gradient(25deg,transparent_48%,#0F7352_49%,#0F7352_51%,transparent_52%),linear-gradient(-35deg,transparent_48%,#FFB72B_49%,#FFB72B_51%,transparent_52%)] [background-size:90px_72px]" /><span className={cn("relative flex items-center justify-center rounded-full bg-[#FFB72B] shadow-lg", expanded ? "size-12" : "size-9")}><MapPin className={cn("fill-[#063f2e] text-[#063f2e]", expanded ? "size-6" : "size-4.5")} /></span><p className={cn("relative text-sm font-black text-[#063f2e]", expanded ? "mt-4" : "mt-2")}>{shouldLoad ? "Abrindo o mapa leve…" : isCompactViewport ? "Abra o mapa quando precisar" : "O mapa carrega só quando você chega aqui"}</p>{expanded && <p className="relative mt-1 text-xs text-[#60776e]">Isso deixa a busca inicial mais rápida.</p>}{!shouldLoad && <Button type="button" onClick={() => { setExpanded(true); setShouldLoad(true) }} className="relative mt-3 h-8 rounded-full bg-[#063f2e] px-4 text-xs font-extrabold">Abrir mapa</Button>}</div>}
      </div>
    </div>
  )
})

function Legend({ color, label }: { color: string; label: string }) {
  return <span className="flex items-center gap-1"><span className="size-2 rounded-full" style={{ backgroundColor: color }} />{label}</span>
}
