"use client"

import { useMemo, useState } from "react"
import { ArrowUpRight, Check, MapPin, Search, ShieldCheck, SlidersHorizontal } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { BrandLogo } from "@/components/brand-logo"
import { PropertyCard } from "@/components/property-card"
import { properties, quickFilters } from "@/lib/properties"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Toggle } from "@/components/ui/toggle"
import { TooltipProvider } from "@/components/ui/tooltip"

function normalize(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
}

export default function Home() {
  const [query, setQuery] = useState("")
  const [activeFilter, setActiveFilter] = useState<string | null>(null)
  const [showTotal, setShowTotal] = useState(false)

  const filteredProperties = useMemo(() => {
    const search = normalize(query.trim())
    return properties.filter((property) => {
      const matchesSearch = !search || normalize(`${property.title} ${property.neighborhood}`).includes(search)
      const matchesZone = !activeFilter || property.zones.includes(activeFilter)
      return matchesSearch && matchesZone
    })
  }, [query, activeFilter])

  const resetFilters = () => { setQuery(""); setActiveFilter(null) }

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#F4F0E4] text-[#063f2e]">
        <SiteHeader />
        <main id="inicio">
          <section className="overflow-hidden bg-[#FBF7EB]">
            <div className="mx-auto grid max-w-7xl items-center gap-12 px-4 py-12 sm:px-6 sm:py-16 lg:grid-cols-[1.05fr_.95fr] lg:gap-20 lg:px-8 lg:py-20">
              <div>
                <p className="mb-5 inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-[#0F7352]"><span className="h-2 w-8 rounded-full bg-[#FFB72B]" /> Feito em Manaus, pra Manaus</p>
                <h1 className="max-w-2xl text-[3.25rem] font-black leading-[.94] tracking-[-0.065em] text-[#063f2e] sm:text-6xl lg:text-[4.9rem]">Um lugar em Manaus pra chamar de <span className="relative whitespace-nowrap">seu.<svg className="absolute -bottom-2 left-0 h-3 w-full text-[#FFB72B]" viewBox="0 0 220 14" preserveAspectRatio="none" aria-hidden="true"><path d="M3 10c46-8 133-8 214-4" fill="none" stroke="currentColor" strokeWidth="7" strokeLinecap="round" /></svg></span></h1>
                <p className="mt-7 max-w-xl text-lg leading-relaxed text-[#48685c]">A gente junta os aluguéis da cidade, confere a procedência e mostra o custo de verdade. Você só escolhe onde quer morar.</p>

                <div className="mt-8 flex max-w-xl items-center gap-2 rounded-[20px] border-2 border-[#063f2e] bg-white p-1.5 shadow-[5px_5px_0_#FFB72B]">
                  <MapPin className="ml-3 size-5 shrink-0 fill-[#FFB72B] text-[#063f2e]" />
                  <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Qual bairro você procura?" aria-label="Buscar por bairro" className="h-12 border-0 bg-transparent px-2 text-base text-[#063f2e] shadow-none placeholder:text-[#789087] focus-visible:ring-0" />
                  <Button className="size-11 shrink-0 rounded-2xl bg-[#063f2e] p-0 text-white hover:bg-[#0B513B] sm:h-12 sm:w-auto sm:px-5" aria-label="Buscar imóveis"><Search className="size-5" /><span className="hidden font-extrabold sm:inline">Buscar</span></Button>
                </div>

                <div className="mt-6 flex max-w-2xl flex-wrap gap-2" aria-label="Filtros rápidos">
                  {quickFilters.map((filter) => (
                    <button key={filter.id} type="button" onClick={() => setActiveFilter((current) => current === filter.id ? null : filter.id)} aria-pressed={activeFilter === filter.id} className={cn("rounded-full border px-3.5 py-2 text-xs font-bold transition", activeFilter === filter.id ? "border-[#063f2e] bg-[#063f2e] text-white" : "border-[#063f2e]/15 bg-white/60 text-[#315a4c] hover:border-[#FFB72B] hover:bg-[#FFB72B]/15")}><span className="mr-1.5" aria-hidden="true">{filter.emoji}</span>{filter.label}</button>
                  ))}
                </div>
              </div>

              <div className="relative mx-auto w-full max-w-[540px] lg:mx-0">
                <div className="absolute -left-6 -top-5 size-20 rounded-[24px] bg-[#FFB72B] sm:-left-9 sm:size-28" />
                <div className="absolute -bottom-7 -right-8 size-32 rounded-full border-[18px] border-[#0F7352]/12" />
                <div className="relative overflow-hidden rounded-[48px_48px_48px_12px] border-[6px] border-white bg-white shadow-[0_20px_50px_rgba(6,63,46,.16)]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={properties[4].images[0]} alt="Casa para alugar na Ponta Negra, em Manaus" className="aspect-[4/4.35] w-full object-cover" />
                  <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#032b20] via-[#032b20]/75 to-transparent px-6 pb-6 pt-24 text-white sm:px-8 sm:pb-8">
                    <p className="text-xs font-bold text-[#FFCA57]">Ponta Negra · Manaus</p><p className="mt-1 text-2xl font-black tracking-[-0.04em]">Casa em condomínio</p><p className="mt-2 text-sm text-white/75">4 quartos · 210 m² · aceita pet</p>
                  </div>
                </div>
                <div className="absolute -bottom-5 -left-4 rotate-[-3deg] rounded-[18px] bg-[#FFB72B] px-5 py-4 text-[#063f2e] shadow-lg sm:-left-10">
                  <p className="text-[10px] font-black uppercase tracking-[0.12em]">Custo sem surpresa</p><p className="mt-0.5 text-xl font-black">R$ 5.550 <span className="text-xs">/ mês</span></p>
                </div>
              </div>
            </div>
          </section>

          <section id="imoveis" className="mx-auto max-w-7xl px-4 py-14 sm:px-6 sm:py-20 lg:px-8">
            <div className="mb-8 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
              <div>
                <p className="mb-2 flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-[#C57C00]"><SlidersHorizontal className="size-4" /> Achados de agora</p>
                <h2 className="text-3xl font-black tracking-[-0.045em] text-[#063f2e] sm:text-4xl">{filteredProperties.length === 1 ? "1 cantinho encontrado" : `${filteredProperties.length} cantinhos encontrados`}</h2>
                <p className="mt-2 text-sm text-[#60776e]">Atualizados para quem está procurando em Manaus.</p>
                {(query || activeFilter) && <button type="button" onClick={resetFilters} className="mt-2 text-xs font-bold text-[#0F7352] underline decoration-[#FFB72B] decoration-2 underline-offset-4">Limpar busca e ver tudo</button>}
              </div>
              <Toggle pressed={showTotal} onPressedChange={setShowTotal} variant="outline" className="h-auto min-h-12 justify-start rounded-full border-2 border-[#063f2e]/15 bg-[#FBF7EB] px-4 py-2.5 text-left text-xs font-bold text-[#315a4c] shadow-none hover:bg-white data-[state=on]:border-[#063f2e] data-[state=on]:bg-[#063f2e] data-[state=on]:text-white sm:text-sm" aria-label="Exibir custo total mensal">
                <span className={cn("relative h-6 w-10 shrink-0 rounded-full bg-[#C9C4B6] transition-colors", showTotal && "bg-[#FFB72B]")}><span className={cn("absolute left-1 top-1 size-4 rounded-full bg-white shadow-sm transition-transform", showTotal && "translate-x-4 bg-[#063f2e]")} /></span>
                Somar aluguel + condomínio + IPTU
              </Toggle>
            </div>

            {filteredProperties.length > 0 ? <div className="grid gap-7 md:grid-cols-2 xl:grid-cols-3">{filteredProperties.map((property) => <PropertyCard key={property.id} property={property} showTotal={showTotal} />)}</div> : (
              <div className="rounded-[32px] border-2 border-dashed border-[#063f2e]/20 bg-[#FBF7EB] px-6 py-16 text-center"><span className="mx-auto flex size-12 items-center justify-center rounded-full bg-[#FFB72B]"><Search className="size-5" /></span><h2 className="mt-4 text-xl font-black">Esse cantinho ainda não apareceu.</h2><p className="mt-1 text-sm text-[#60776e]">Tente outro bairro ou volte para todos os imóveis.</p><Button onClick={resetFilters} className="mt-5 rounded-full bg-[#063f2e] font-bold">Ver todos</Button></div>
            )}
          </section>

          <section id="como-funciona" className="bg-[#063f2e] py-16 text-[#FBF7EB] sm:py-20">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <div className="grid gap-12 lg:grid-cols-[.75fr_1.25fr] lg:gap-24">
                <div><p className="text-xs font-black uppercase tracking-[0.16em] text-[#FFB72B]">Do seu jeito</p><h2 className="mt-4 text-4xl font-black leading-tight tracking-[-0.05em] sm:text-5xl">A busca fica mais leve quando a informação é clara.</h2><p className="mt-5 max-w-md leading-relaxed text-[#B9CEC6]">Sem dez abas abertas, anúncio repetido ou taxa escondida no fim.</p></div>
                <div className="divide-y divide-white/15 border-y border-white/15">
                  {["Diga o bairro ou a região que faz sentido pra sua rotina.", "Compare o aluguel sozinho ou o custo completo do mês.", "Gostou? O WhatsApp já abre com o imóvel identificado."].map((text, index) => (
                    <div key={text} className="grid grid-cols-[54px_1fr_auto] items-center gap-3 py-6 sm:py-7"><span className="text-sm font-black text-[#FFB72B]">0{index + 1}</span><p className="text-lg font-bold leading-snug sm:text-xl">{text}</p><ArrowUpRight className="size-5 text-[#FFB72B]" /></div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section id="verificacao" className="bg-[#FBF7EB] py-16 sm:py-20">
            <div className="mx-auto grid max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-2 lg:items-center lg:gap-20 lg:px-8">
              <div className="relative rounded-[36px] bg-[#FFB72B] p-8 text-[#063f2e] sm:p-10">
                <ShieldCheck className="size-14" strokeWidth={1.8} /><p className="mt-8 text-3xl font-black leading-tight tracking-[-0.045em] sm:text-4xl">Anúncio bom começa com origem conhecida.</p><div className="absolute -right-3 -top-3 size-10 rounded-full border-[8px] border-[#0F7352]" />
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-[#0F7352]">Nossa checagem</p><h2 className="mt-3 text-3xl font-black tracking-[-0.045em] text-[#063f2e]">Antes de você chamar, a gente olha.</h2><p className="mt-4 leading-relaxed text-[#60776e]">Cada card deixa claro de onde o anúncio veio. Também conferimos dados essenciais e destacamos profissionais com CRECI verificado.</p>
                <div className="mt-7 grid gap-4">{["A fonte aparece sem letrinha escondida", "Aluguel, condomínio e IPTU ficam separados", "Cada conversa leva o código certo do imóvel"].map((item) => <div key={item} className="flex items-center gap-3 font-bold text-[#315a4c]"><span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-[#FFB72B]"><Check className="size-4 stroke-[3]" /></span>{item}</div>)}</div>
              </div>
            </div>
          </section>
        </main>

        <footer className="border-t border-[#063f2e]/10 bg-[#FBF7EB]">
          <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8"><BrandLogo className="scale-90 origin-left" /><div className="flex items-center gap-2 text-xs font-bold text-[#60776e]"><MapPin className="size-4 fill-[#FFB72B] text-[#063f2e]" /> Manaus, Amazonas <span className="mx-2 text-[#D3CCBA]">•</span> Aluguel sem enrolação</div></div>
        </footer>
      </div>
    </TooltipProvider>
  )
}
