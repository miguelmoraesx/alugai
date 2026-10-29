"use client"

import { useState } from "react"
import { Bath, BedDouble, Building2, Check, ChevronLeft, ChevronRight, Heart, Layers3, MessageCircle, PawPrint, Square, UserRound } from "lucide-react"
import type { Property } from "@/lib/properties"
import { PropertyDetailsDialog } from "@/components/property-details-dialog"
import { cn } from "@/lib/utils"
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
  const isOwner = property.advertiser === "owner"
  const isBroker = property.advertiser === "broker"

  return (
    <Card id={property.id} className="group scroll-mt-28 gap-0 overflow-hidden rounded-[26px] border-[#063f2e]/12 bg-[#FFFDF7] py-0 shadow-[0_6px_0_rgba(6,63,46,0.04)] transition duration-300 hover:-translate-y-1 hover:border-[#063f2e]/25 hover:shadow-[0_12px_0_rgba(6,63,46,0.07)]">
      <div className="relative aspect-[4/3] overflow-hidden bg-[#E8E4D8]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={property.images[imageIndex]} alt={`${property.title} em ${property.neighborhood} — foto ${imageIndex + 1}`} className="size-full object-cover transition-transform duration-700 group-hover:scale-[1.025]" />
        <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-[#032b20]/45 to-transparent" />
        {isOwner ? (
          <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-[#FFB72B] px-3 py-1.5 text-[10px] font-extrabold text-[#063f2e] shadow-sm"><UserRound className="size-3.5" /> Direto com proprietário</div>
        ) : isBroker ? (
          <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-[#0F7352] px-3 py-1.5 text-[10px] font-extrabold text-white shadow-sm"><Building2 className="size-3.5 text-[#FFB72B]" /> Anunciado por corretor</div>
        ) : (
          <div className="absolute left-3 top-3 flex items-center gap-1.5 rounded-full bg-[#596B64] px-3 py-1.5 text-[10px] font-extrabold text-white shadow-sm"><Layers3 className="size-3.5 text-[#FFB72B]" /> Anúncio agregado</div>
        )}
        <button type="button" onClick={() => setFavorite((value) => !value)} className="absolute right-3 top-3 flex size-9 items-center justify-center rounded-full bg-[#FBF7EB] text-[#063f2e] shadow-sm transition hover:scale-105" aria-label={favorite ? "Remover dos favoritos" : "Adicionar aos favoritos"}><Heart className={cn("size-[17px]", favorite && "fill-[#FFB72B] text-[#FFB72B]")} /></button>
        <button type="button" onClick={() => moveImage(-1)} className="absolute left-3 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-[#FBF7EB]/95 text-[#063f2e] opacity-0 transition group-hover:opacity-100 focus:opacity-100" aria-label="Foto anterior"><ChevronLeft className="size-4" /></button>
        <button type="button" onClick={() => moveImage(1)} className="absolute right-3 top-1/2 flex size-8 -translate-y-1/2 items-center justify-center rounded-full bg-[#FBF7EB]/95 text-[#063f2e] opacity-0 transition group-hover:opacity-100 focus:opacity-100" aria-label="Próxima foto"><ChevronRight className="size-4" /></button>
        <div className="absolute bottom-3 left-1/2 flex -translate-x-1/2 gap-1.5 rounded-full bg-[#063f2e]/50 px-2 py-1.5 backdrop-blur-sm">{property.images.map((_, index) => <button key={index} type="button" onClick={() => setImageIndex(index)} className={cn("size-1.5 rounded-full bg-white/60 transition-all", imageIndex === index && "w-4 bg-[#FFB72B]")} aria-label={`Ver foto ${index + 1}`} />)}</div>
      </div>

      <CardContent className="flex flex-1 flex-col p-5">
        <div className="mb-3 flex items-start justify-between gap-3">
          <div><p className="mb-1 text-xs font-bold text-[#C57C00]">{property.neighborhood} · Manaus</p><h2 className="text-xl font-black leading-tight tracking-[-0.035em] text-[#063f2e]">{property.title}</h2></div>
          <span className="shrink-0 rounded-full border border-[#063f2e]/10 bg-[#F4F0E4] px-2.5 py-1 text-[10px] font-bold text-[#526d63]">#{property.id.replace("ALG-", "")}</span>
        </div>

        <div className="mb-4 flex flex-wrap gap-x-3 gap-y-2 text-[#526d63]">
          <Spec icon={BedDouble} value={`${property.bedrooms} ${property.bedrooms === 1 ? "quarto" : "quartos"}`} />
          <Spec icon={Bath} value={`${property.bathrooms} ${property.bathrooms === 1 ? "banheiro" : "banheiros"}`} />
          <Spec icon={Square} value={`${property.area} m²`} />
          <Spec icon={PawPrint} value={property.petFriendly ? "Aceita pet" : "Pet? consulte"} />
        </div>

        <div className="mt-auto border-t border-dashed border-[#063f2e]/18 pt-4">
          <div className="flex items-end justify-between gap-3">
            <div><p className="text-[10px] font-extrabold uppercase tracking-[0.1em] text-[#6b7f77]">{showTotal ? "Tudo incluso por mês" : "Aluguel por mês"}</p><p className="mt-0.5 text-[27px] font-black leading-none tracking-[-0.05em] text-[#063f2e]">{money.format(showTotal ? total : property.rent)}</p></div>
            {showTotal && <span className="flex size-7 items-center justify-center rounded-full bg-[#FFB72B] text-[#063f2e]"><Check className="size-4 stroke-[3]" /></span>}
          </div>
          <p className="mt-2 text-[10px] leading-relaxed text-[#71837c]">Aluguel {money.format(property.rent)} · Cond. {money.format(property.condo)} · IPTU {money.format(property.iptu)}</p>
        </div>

        <div className="my-4 flex items-center justify-between gap-3 text-[10px] text-[#71837c]"><span>Fonte: <strong className="text-[#315a4c]">{property.sourceLabel}</strong></span><span className="shrink-0 font-bold text-[#0F7352]">Disponível hoje</span></div>
        <div className="grid grid-cols-[1.15fr_.85fr] gap-2"><PropertyDetailsDialog property={property} /><Button asChild className="h-11 rounded-full bg-[#063f2e] font-extrabold text-white shadow-none transition hover:bg-[#0B513B]"><a href={whatsappUrl} target="_blank" rel="noreferrer"><MessageCircle className="size-4.5 text-[#FFB72B]" /> WhatsApp</a></Button></div>
      </CardContent>
    </Card>
  )
}

function Spec({ icon: Icon, value }: { icon: typeof BedDouble; value: string }) {
  return <Tooltip><TooltipTrigger asChild><span className="inline-flex items-center gap-1 text-[11px] font-semibold"><Icon className="size-3.5 text-[#0F7352]" />{value}</span></TooltipTrigger><TooltipContent>{value}</TooltipContent></Tooltip>
}
