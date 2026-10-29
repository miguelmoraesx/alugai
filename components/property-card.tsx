"use client"

import { useState } from "react"
import { Bath, BedDouble, Check, ChevronLeft, ChevronRight, Heart, MessageCircle, PawPrint, ShieldCheck, Square } from "lucide-react"
import type { Property } from "@/lib/properties"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })

export function PropertyCard({ property, showTotal }: { property: Property; showTotal: boolean }) {
  const [imageIndex, setImageIndex] = useState(0)
  const [favorite, setFavorite] = useState(false)
  const total = property.rent + property.condo + property.iptu
  const whatsappText = `Olá! Vi o imóvel #${property.id} (${property.neighborhood}) no Alugaí e quero agendar uma visita.`
  const whatsappUrl = `https://wa.me/5592999999999?text=${encodeURIComponent(whatsappText)}`
  const moveImage = (direction: number) => setImageIndex((current) => (current + direction + property.images.length) % property.images.length)

  return (
    <Card className="group gap-0 overflow-hidden rounded-2xl border-slate-200 bg-white py-0 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-slate-200/70">
      <div className="relative aspect-[16/10] overflow-hidden bg-slate-100">
        <img src={property.images[imageIndex]} alt={`${property.title} em ${property.neighborhood} — foto ${imageIndex + 1}`} className="size-full object-cover transition-transform duration-700 group-hover:scale-[1.03]" />
        <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-slate-950/50 to-transparent" />
        <Badge className="absolute left-3 top-3 max-w-[72%] gap-1.5 rounded-full border border-white/15 bg-emerald-600/95 px-2.5 py-1 text-[10px] font-semibold text-white shadow-sm backdrop-blur sm:text-[11px]"><ShieldCheck className="size-3.5" /> Procedência checada <span className="hidden sm:inline">• CRECI verificado</span></Badge>
        <Badge className="absolute right-3 top-3 gap-1 rounded-full border border-white/40 bg-white/95 px-2.5 py-1 text-[10px] font-semibold text-slate-700 shadow-sm"><Check className="size-3 text-emerald-600" /> Hoje</Badge>

        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button" onClick={() => setFavorite((value) => !value)} className="absolute right-3 top-12 flex size-8 items-center justify-center rounded-full border border-white/40 bg-white/90 text-slate-600 shadow-sm transition hover:scale-105" aria-label={favorite ? "Remover dos favoritos" : "Adicionar aos favoritos"}>
              <Heart className={cn("size-4", favorite && "fill-rose-500 text-rose-500")} />
            </button>
          </TooltipTrigger>
          <TooltipContent>{favorite ? "Salvo nos favoritos" : "Salvar imóvel"}</TooltipContent>
        </Tooltip>

        <button type="button" onClick={() => moveImage(-1)} className="absolute left-3 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-slate-800 opacity-0 shadow-sm transition hover:bg-white group-hover:opacity-100 focus:opacity-100" aria-label="Foto anterior"><ChevronLeft className="size-4" /></button>
        <button type="button" onClick={() => moveImage(1)} className="absolute right-3 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-white/90 text-slate-800 opacity-0 shadow-sm transition hover:bg-white group-hover:opacity-100 focus:opacity-100" aria-label="Próxima foto"><ChevronRight className="size-4" /></button>
        <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5 rounded-full bg-slate-950/25 px-2 py-1.5 backdrop-blur-sm">
          {property.images.map((_, index) => <button key={index} type="button" onClick={() => setImageIndex(index)} className={cn("size-1.5 rounded-full bg-white/60 transition-all", imageIndex === index && "w-4 bg-white")} aria-label={`Ver foto ${index + 1}`} />)}
        </div>
      </div>

      <CardContent className="flex flex-1 flex-col p-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div><h2 className="text-[17px] font-semibold leading-tight tracking-[-0.02em] text-slate-950">{property.title}</h2><p className="mt-1 text-sm font-medium text-slate-500">{property.neighborhood}, Manaus</p></div>
          <Badge variant="secondary" className="shrink-0 rounded-md bg-slate-100 text-[10px] font-semibold text-slate-500">#{property.id.replace("ALG-", "")}</Badge>
        </div>
        <div className="grid grid-cols-4 gap-2 border-y border-slate-100 py-3 text-slate-600">
          <Spec icon={BedDouble} value={`${property.bedrooms} ${property.bedrooms === 1 ? "quarto" : "quartos"}`} />
          <Spec icon={Bath} value={`${property.bathrooms} ${property.bathrooms === 1 ? "banheiro" : "banheiros"}`} />
          <Spec icon={Square} value={`${property.area} m²`} />
          <Spec icon={PawPrint} value={property.petFriendly ? "Aceita pet" : "Consulte"} />
        </div>
        <div className="my-4 rounded-xl border border-emerald-100 bg-emerald-50/60 p-4">
          <div className="flex items-center justify-between gap-2">
            <div><p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-emerald-700">{showTotal ? "Custo total mensal" : "Aluguel mensal"}</p><p className="mt-1 text-2xl font-bold tracking-[-0.04em] text-slate-950">{money.format(showTotal ? total : property.rent)}<span className="ml-1 text-xs font-medium tracking-normal text-slate-500">/mês</span></p></div>
            {showTotal && <span className="rounded-full bg-emerald-600 p-1.5 text-white"><Check className="size-4" /></span>}
          </div>
          <p className="mt-2 text-[11px] leading-relaxed text-slate-500">Aluguel: {money.format(property.rent)} · Cond.: {money.format(property.condo)} · IPTU: {money.format(property.iptu)}</p>
        </div>
        <p className="mb-4 text-[11px] text-slate-500"><span className="font-semibold text-slate-600">Fonte:</span> {property.sourceLabel}</p>
        <Button asChild className="mt-auto h-11 w-full rounded-xl bg-emerald-600 font-semibold shadow-sm shadow-emerald-200 transition-all hover:bg-emerald-700 hover:shadow-md"><a href={whatsappUrl} target="_blank" rel="noreferrer"><MessageCircle className="size-4.5" /> Falar com corretor no WhatsApp</a></Button>
      </CardContent>
    </Card>
  )
}

function Spec({ icon: Icon, value }: { icon: typeof BedDouble; value: string }) {
  return (
    <Tooltip><TooltipTrigger asChild><div className="flex min-w-0 flex-col items-center gap-1.5 text-center"><Icon className="size-4 text-slate-400" /><span className="max-w-full truncate text-[10px] font-medium sm:text-[11px]">{value}</span></div></TooltipTrigger><TooltipContent>{value}</TooltipContent></Tooltip>
  )
}
