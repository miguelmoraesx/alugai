"use client"

import { useMemo, useState } from "react"
import { ArrowRight, CheckCircle2, MapPin, Search, ShieldCheck, SlidersHorizontal, Sparkles } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { PropertyCard } from "@/components/property-card"
import { properties, quickFilters } from "@/lib/properties"
import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
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
      <div className="min-h-screen bg-slate-50 text-slate-900">
        <SiteHeader />
        <main id="inicio">
          <section className="relative overflow-hidden border-b border-slate-200 bg-white">
            <div className="pointer-events-none absolute -right-24 -top-48 size-[520px] rounded-full bg-emerald-100/60 blur-3xl" />
            <div className="pointer-events-none absolute -left-44 bottom-0 size-80 rounded-full bg-teal-50 blur-3xl" />
            <div className="relative mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20 lg:px-8 lg:py-24">
              <div className="mx-auto max-w-4xl text-center">
                <Badge className="mb-5 gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 font-semibold text-emerald-700 shadow-none hover:bg-emerald-50"><Sparkles className="size-3.5" /> Feito para quem vive Manaus</Badge>
                <h1 className="text-balance text-4xl font-semibold leading-[1.08] tracking-[-0.045em] text-slate-950 sm:text-5xl lg:text-6xl">Encontre seu imóvel em Manaus <span className="text-emerald-600">sem burocracia</span> ou anúncios falsos.</h1>
                <p className="mx-auto mt-5 max-w-2xl text-pretty text-base leading-relaxed text-slate-600 sm:text-lg">Centralizamos as melhores ofertas verificadas de aluguel em um só lugar.</p>
                <div className="mx-auto mt-9 flex max-w-2xl items-center gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-xl shadow-slate-200/60 ring-4 ring-slate-100/70">
                  <MapPin className="ml-3 size-5 shrink-0 text-emerald-600" />
                  <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Busque por Parque 10, Flores, Ponta Negra..." aria-label="Buscar por bairro" className="h-12 border-0 bg-transparent px-2 text-base shadow-none focus-visible:ring-0" />
                  <Button className="size-11 shrink-0 rounded-xl bg-emerald-600 p-0 hover:bg-emerald-700 sm:h-12 sm:w-auto sm:px-5" aria-label="Buscar imóveis"><Search className="size-5" /><span className="hidden sm:inline">Buscar</span></Button>
                </div>
                <div className="mt-6 flex flex-wrap justify-center gap-2" aria-label="Filtros rápidos">
                  {quickFilters.map((filter) => (
                    <button key={filter.id} type="button" onClick={() => setActiveFilter((current) => current === filter.id ? null : filter.id)} aria-pressed={activeFilter === filter.id} className={cn("rounded-full border px-3.5 py-2 text-sm font-medium shadow-xs transition-all", activeFilter === filter.id ? "border-emerald-600 bg-emerald-600 text-white shadow-emerald-100" : "border-slate-200 bg-white text-slate-600 hover:-translate-y-0.5 hover:border-emerald-300 hover:text-emerald-700")}>
                      <span className="mr-1.5" aria-hidden="true">{filter.emoji}</span>{filter.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section className="mx-auto max-w-7xl px-4 py-10 sm:px-6 lg:px-8 lg:py-14" aria-labelledby="resultados">
            <div className="mb-7 flex flex-col justify-between gap-4 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:p-5">
              <div>
                <div className="flex items-center gap-2 text-sm font-semibold text-slate-900"><span className="flex size-8 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700"><SlidersHorizontal className="size-4" /></span><p id="resultados">Mostrando <span className="text-emerald-700">{filteredProperties.length} imóveis</span> disponíveis em Manaus</p></div>
                {(query || activeFilter) && <button type="button" onClick={resetFilters} className="ml-10 mt-1 text-xs font-medium text-slate-500 underline-offset-2 hover:text-emerald-700 hover:underline">Limpar filtros</button>}
              </div>
              <Toggle pressed={showTotal} onPressedChange={setShowTotal} variant="outline" className="h-auto min-h-11 justify-start rounded-xl border-slate-200 bg-slate-50 px-3 py-2.5 text-left text-xs text-slate-600 shadow-none hover:bg-slate-100 data-[state=on]:border-emerald-300 data-[state=on]:bg-emerald-50 data-[state=on]:text-emerald-800 sm:text-sm" aria-label="Exibir custo total mensal">
                <span className={cn("relative h-5 w-9 shrink-0 rounded-full bg-slate-300 transition-colors", showTotal && "bg-emerald-600")}><span className={cn("absolute left-0.5 top-0.5 size-4 rounded-full bg-white shadow-sm transition-transform", showTotal && "translate-x-4")} /></span>
                Exibir Custo Total Mensal <span className="hidden lg:inline">(Aluguel + Condomínio + IPTU)</span>
              </Toggle>
            </div>
            {filteredProperties.length > 0 ? (
              <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-3">{filteredProperties.map((property) => <PropertyCard key={property.id} property={property} showTotal={showTotal} />)}</div>
            ) : (
              <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-16 text-center"><span className="mx-auto flex size-12 items-center justify-center rounded-full bg-slate-100"><Search className="size-5 text-slate-500" /></span><h2 className="mt-4 text-lg font-semibold text-slate-900">Nenhum imóvel encontrado</h2><p className="mt-1 text-sm text-slate-500">Tente outro bairro ou remova o filtro selecionado.</p><Button variant="outline" onClick={resetFilters} className="mt-5 rounded-xl">Ver todos os imóveis</Button></div>
            )}
          </section>

          <section id="como-funciona" className="border-y border-slate-200 bg-white py-16 sm:py-20">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8"><div className="grid items-start gap-10 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
              <div><Badge variant="outline" className="rounded-full border-emerald-200 bg-emerald-50 text-emerald-700">Como funciona</Badge><h2 className="mt-4 text-3xl font-semibold tracking-[-0.035em] text-slate-950 sm:text-4xl">Menos tempo procurando. Mais segurança para decidir.</h2><p className="mt-4 leading-relaxed text-slate-600">O Alugaí reúne ofertas de diferentes fontes e organiza as informações que mais importam para quem busca um novo lar em Manaus.</p></div>
              <div className="grid gap-4 sm:grid-cols-3">{[["01", "Busque por região", "Filtre pelos bairros e polos que fazem parte da sua rotina."], ["02", "Compare o custo real", "Veja aluguel, condomínio e IPTU separados ou somados."], ["03", "Fale direto", "Abra o WhatsApp com o código e os dados do imóvel preenchidos."]].map(([number, title, description]) => <div key={number} className="rounded-2xl border border-slate-200 bg-slate-50 p-5"><span className="text-xs font-bold text-emerald-600">{number}</span><h3 className="mt-7 font-semibold text-slate-900">{title}</h3><p className="mt-2 text-sm leading-relaxed text-slate-600">{description}</p></div>)}</div>
            </div></div>
          </section>

          <section id="verificacao" className="mx-auto max-w-7xl px-4 py-16 sm:px-6 sm:py-20 lg:px-8">
            <div className="overflow-hidden rounded-3xl bg-slate-950 px-6 py-10 text-white sm:px-10 lg:flex lg:items-center lg:justify-between lg:px-14 lg:py-14">
              <div className="max-w-2xl"><span className="flex size-11 items-center justify-center rounded-xl bg-emerald-500/15 text-emerald-400"><ShieldCheck className="size-6" /></span><h2 className="mt-5 text-3xl font-semibold tracking-[-0.035em]">Procedência antes da visita.</h2><p className="mt-3 max-w-xl leading-relaxed text-slate-300">Identificamos a fonte do anúncio, conferimos os dados essenciais e destacamos profissionais com CRECI verificado.</p></div>
              <div className="mt-8 grid gap-3 text-sm text-slate-200 lg:mt-0">{["Origem do anúncio identificada", "Dados financeiros transparentes", "Contato rastreável por código"].map((item) => <div key={item} className="flex items-center gap-3"><CheckCircle2 className="size-5 text-emerald-400" />{item}</div>)}</div>
            </div>
          </section>
        </main>
        <footer className="border-t border-slate-200 bg-white"><div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-8 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8"><p><span className="font-bold text-slate-900">Alugaí</span> · Manaus / AM</p><a href="#inicio" className="flex items-center gap-1 font-medium text-slate-600 hover:text-emerald-700">Voltar ao topo <ArrowRight className="size-3.5 -rotate-45" /></a></div></footer>
      </div>
    </TooltipProvider>
  )
}
