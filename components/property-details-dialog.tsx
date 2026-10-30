"use client"

import { useState } from "react"
import { BadgeCheck, Bath, BedDouble, CarFront, ChevronLeft, ChevronRight, MapPin, MessageCircle, PawPrint, Square, UserRound } from "lucide-react"
import type { Property } from "@/lib/properties"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 })

export function PropertyDetailsDialog({ property }: { property: Property }) {
  const [photo, setPhoto] = useState(0)
  const total = property.rent + property.condo + property.iptu
  const isOwner = property.advertiser === "owner"
  const isBroker = property.advertiser === "broker"
  const advertiserLabel = isOwner ? "Direto com proprietário" : isBroker ? "Anunciado por corretor" : "Anúncio agregado"
  const contactLabel = isOwner ? "Falar com proprietário" : isBroker ? "Falar com corretor" : "Pedir contato no WhatsApp"
  const whatsappText = `Olá! Vi o imóvel #${property.id} (${property.neighborhood}) no Alugaí e quero saber mais.`
  const whatsappUrl = `https://wa.me/5592999999999?text=${encodeURIComponent(whatsappText)}`
  const movePhoto = (direction: number) => setPhoto((current) => (current + direction + property.images.length) % property.images.length)

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" className="h-11 flex-1 rounded-full border-2 border-[#063f2e]/20 bg-transparent font-extrabold text-[#063f2e] shadow-none hover:border-[#063f2e] hover:bg-[#F4F0E4]">Ver detalhes</Button>
      </DialogTrigger>
      <DialogContent className="max-h-[92vh] gap-0 overflow-y-auto rounded-[28px] border-0 bg-[#FBF7EB] p-0 sm:max-w-4xl">
        <div className="grid lg:grid-cols-[1.08fr_.92fr]">
          <div className="bg-[#E8E4D8] p-3 sm:p-5">
            <div className="relative overflow-hidden rounded-[22px] bg-[#DAD5C7]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={property.images[photo]} alt={`${property.title} em ${property.neighborhood}, foto ampliada ${photo + 1}`} decoding="async" className="aspect-[4/3] size-full object-cover" />
              <button type="button" onClick={() => movePhoto(-1)} className="absolute left-3 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-[#FBF7EB]/95 text-[#063f2e] shadow-md" aria-label="Foto anterior"><ChevronLeft className="size-5" /></button>
              <button type="button" onClick={() => movePhoto(1)} className="absolute right-3 top-1/2 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-[#FBF7EB]/95 text-[#063f2e] shadow-md" aria-label="Próxima foto"><ChevronRight className="size-5" /></button>
              <span className="absolute bottom-3 right-3 rounded-full bg-[#063f2e]/80 px-3 py-1 text-xs font-bold text-white">{photo + 1} / {property.images.length}</span>
            </div>
            <div className="mt-3 grid grid-cols-3 gap-2">
              {property.images.map((image, index) => (
                <button key={image} type="button" onClick={() => setPhoto(index)} className={cn("overflow-hidden rounded-xl border-2", photo === index ? "border-[#FFB72B]" : "border-transparent opacity-70 hover:opacity-100")} aria-label={`Abrir foto ${index + 1}`}>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={image} alt="" loading="lazy" decoding="async" className="aspect-[16/10] size-full object-cover" />
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col p-6 sm:p-8">
            <DialogHeader className="text-left">
              <div className="mb-2 flex items-center gap-2 text-xs font-extrabold text-[#0F7352]">{isOwner ? <UserRound className="size-4" /> : <BadgeCheck className="size-4" />}{advertiserLabel}</div>
              <DialogTitle className="text-3xl font-black leading-tight tracking-[-0.045em] text-[#063f2e]">{property.title}</DialogTitle>
              <DialogDescription className="flex items-center gap-1.5 text-sm font-semibold text-[#60776e]"><MapPin className="size-4 text-[#C57C00]" /> {property.neighborhood}, Manaus</DialogDescription>
            </DialogHeader>

            <div className="my-6 grid grid-cols-2 gap-3 sm:grid-cols-5 lg:grid-cols-2">
              <Detail icon={BedDouble} label={`${property.bedrooms} ${property.bedrooms === 1 ? "quarto" : "quartos"}`} />
              <Detail icon={Bath} label={`${property.bathrooms} ${property.bathrooms === 1 ? "banheiro" : "banheiros"}`} />
              <Detail icon={CarFront} label={property.parkingSpaces === 0 ? "Sem garagem" : `${property.parkingSpaces} ${property.parkingSpaces === 1 ? "vaga" : "vagas"}`} />
              <Detail icon={Square} label={`${property.area} m²`} />
              <Detail icon={PawPrint} label={property.petFriendly ? "Aceita pet" : "Não aceita pet"} />
            </div>

            <div className="rounded-[22px] bg-white p-5 shadow-[0_5px_0_rgba(6,63,46,.05)]">
              <p className="text-[10px] font-black uppercase tracking-[.12em] text-[#C57C00]">Custo mensal estimado</p>
              <p className="mt-1 text-3xl font-black tracking-[-0.05em] text-[#063f2e]">{money.format(total)}</p>
              <div className="mt-4 grid gap-2 border-t border-dashed border-[#063f2e]/15 pt-4 text-xs text-[#60776e]">
                <span className="flex justify-between"><span>Aluguel</span><strong className="text-[#315a4c]">{money.format(property.rent)}</strong></span>
                <span className="flex justify-between"><span>Condomínio</span><strong className="text-[#315a4c]">{money.format(property.condo)}</strong></span>
                <span className="flex justify-between"><span>IPTU</span><strong className="text-[#315a4c]">{money.format(property.iptu)}</strong></span>
              </div>
            </div>

            <div className="mt-5 rounded-2xl border border-[#063f2e]/10 px-4 py-3 text-xs leading-relaxed text-[#60776e]">Fonte: <span className="font-bold text-[#315a4c]">{property.sourceLabel}</span>. Os dados vêm do anunciante ou da plataforma de origem.</div>
            <Button asChild className="mt-5 h-12 w-full rounded-full bg-[#063f2e] font-extrabold text-white hover:bg-[#0B513B]"><a href={whatsappUrl} target="_blank" rel="noreferrer"><MessageCircle className="size-5 text-[#FFB72B]" /> {contactLabel}</a></Button>
            <p className="mt-3 text-center text-[10px] text-[#789087]">Código do imóvel: {property.id}</p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function Detail({ icon: Icon, label }: { icon: typeof BedDouble; label: string }) {
  return <div className="flex items-center gap-2 rounded-2xl bg-white px-3 py-3 text-xs font-bold text-[#315a4c]"><Icon className="size-4 text-[#0F7352]" />{label}</div>
}
