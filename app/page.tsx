"use client"

import { useMemo, useState, type FormEvent, type ReactNode } from "react"
import { ArrowUpRight, Bath, BedDouble, CarFront, Check, CircleDollarSign, MapPin, Megaphone, PawPrint, Search, SlidersHorizontal, X } from "lucide-react"
import { SiteHeader } from "@/components/site-header"
import { BrandLogo } from "@/components/brand-logo"
import { PropertyCard } from "@/components/property-card"
import { PropertyMap } from "@/components/property-map"
import { properties, quickFilters } from "@/lib/properties"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Toggle } from "@/components/ui/toggle"
import { TooltipProvider } from "@/components/ui/tooltip"

function normalize(value: string) {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
}

function matchesQuickFilter(property: (typeof properties)[number], filterId: string) {
  return filterId === "owner" ? property.advertiser === "owner" : property.zones.includes(filterId)
}

const locationGroups = quickFilters
  .filter((filter) => filter.id.startsWith("region-"))
  .map((region) => ({
    ...region,
    neighborhoods: [...new Set(properties.filter((property) => property.zones.includes(region.id)).map((property) => property.neighborhood))].sort((a, b) => a.localeCompare(b, "pt-BR")),
  }))

export default function Home() {
  const [searchInput, setSearchInput] = useState("")
  const [query, setQuery] = useState("")
  const [activeFilter, setActiveFilter] = useState<string | null>(null)
  const [showTotal, setShowTotal] = useState(false)
  const [searchError, setSearchError] = useState("")
  const [visibleCount, setVisibleCount] = useState(12)
  const [selectedRegion, setSelectedRegion] = useState("all")
  const [selectedNeighborhood, setSelectedNeighborhood] = useState("all")
  const [bedroomFilter, setBedroomFilter] = useState("any")
  const [bathroomFilter, setBathroomFilter] = useState("any")
  const [parkingFilter, setParkingFilter] = useState("any")
  const [petFilter, setPetFilter] = useState("any")
  const [priceFilter, setPriceFilter] = useState("any")

  const filteredProperties = useMemo(() => {
    const search = normalize(query.trim())
    return properties.filter((property) => {
      const matchesSearch = !search || normalize(`${property.title} ${property.neighborhood}`).includes(search)
      const matchesZone = !activeFilter || (activeFilter === "owner" ? property.advertiser === "owner" : property.zones.includes(activeFilter))
      const matchesBedrooms = bedroomFilter === "any" || (bedroomFilter === "3+" ? property.bedrooms >= 3 : property.bedrooms === Number(bedroomFilter))
      const matchesBathrooms = bathroomFilter === "any" || (bathroomFilter === "2+" ? property.bathrooms >= 2 : property.bathrooms === Number(bathroomFilter))
      const matchesParking = parkingFilter === "any" || (parkingFilter === "2+" ? property.parkingSpaces >= 2 : property.parkingSpaces >= Number(parkingFilter))
      const matchesPet = petFilter === "any" || (petFilter === "yes" ? property.petFriendly : !property.petFriendly)
      const matchesPrice = priceFilter === "any" || (priceFilter === "2500+" ? property.rent >= 2500 : property.rent <= Number(priceFilter))
      return matchesSearch && matchesZone && matchesBedrooms && matchesBathrooms && matchesParking && matchesPet && matchesPrice
    })
  }, [query, activeFilter, bedroomFilter, bathroomFilter, parkingFilter, petFilter, priceFilter])

  const visibleProperties = filteredProperties.slice(0, visibleCount)
  const availableNeighborhoods = locationGroups.find((region) => region.id === selectedRegion)?.neighborhoods ?? []
  const activePropertyFilterCount = [bedroomFilter, bathroomFilter, parkingFilter, petFilter, priceFilter].filter((value) => value !== "any").length
  const hasBasicFilters = activePropertyFilterCount > 0
  const scrollToResults = () => window.setTimeout(() => document.getElementById("imoveis")?.scrollIntoView({ behavior: "smooth", block: "start" }), 80)

  const resetFilters = () => {
    setSearchInput("")
    setQuery("")
    setActiveFilter(null)
    setSearchError("")
    setVisibleCount(12)
    setSelectedRegion("all")
    setSelectedNeighborhood("all")
    setBedroomFilter("any")
    setBathroomFilter("any")
    setParkingFilter("any")
    setPetFilter("any")
    setPriceFilter("any")
  }

  const clearBasicFilters = () => {
    setBedroomFilter("any")
    setBathroomFilter("any")
    setParkingFilter("any")
    setPetFilter("any")
    setPriceFilter("any")
    setVisibleCount(12)
  }

  const handleQuickFilter = (filterId: string) => {
    const nextFilter = activeFilter === filterId ? null : filterId
    setActiveFilter(nextFilter)
    setQuery("")
    setSearchInput("")
    setSearchError("")
    setVisibleCount(12)
    setSelectedRegion(nextFilter?.startsWith("region-") ? nextFilter : "all")
    setSelectedNeighborhood("all")
    const matchCount = nextFilter ? properties.filter((property) => matchesQuickFilter(property, nextFilter)).length : properties.length
    if (matchCount > 0) scrollToResults()
  }

  const handleLocationSearch = () => {
    const region = selectedRegion === "all" ? undefined : locationGroups.find((item) => item.id === selectedRegion)
    const neighborhood = selectedNeighborhood === "all" ? "" : selectedNeighborhood
    setActiveFilter(neighborhood ? null : region?.id ?? null)
    setQuery(neighborhood)
    setSearchInput(neighborhood || region?.label || "")
    setSearchError("")
    setVisibleCount(12)
    scrollToResults()
  }

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const term = searchInput.trim()
    setSelectedRegion("all")
    setSelectedNeighborhood("all")
    if (!term) {
      resetFilters()
      scrollToResults()
      return
    }

    const normalizedTerm = normalize(term)
    const matchingFilter = quickFilters.find((filter) => normalize(filter.label).includes(normalizedTerm))
    if (matchingFilter) {
      setActiveFilter(matchingFilter.id)
      setQuery("")
      setSearchError("")
      setVisibleCount(12)
      scrollToResults()
      return
    }

    const matches = properties.filter((property) => normalize(`${property.title} ${property.neighborhood}`).includes(normalizedTerm))
    setActiveFilter(null)
    setQuery(term)
    setVisibleCount(12)
    if (matches.length === 0) {
      setSearchError(`Não encontramos "${term}". Tente outro bairro ou use os filtros.`)
      return
    }
    setSearchError("")
    scrollToResults()
  }

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-[#F4F0E4] text-[#063f2e]">
        <SiteHeader />
        <main id="inicio">
          <section className="overflow-hidden bg-[#FBF7EB]">
            <div className="mx-auto grid max-w-7xl items-start gap-10 px-4 py-6 sm:px-6 sm:py-8 lg:grid-cols-[.95fr_1.05fr] lg:gap-12 lg:px-8 lg:pb-8 lg:pt-6">
              <div>
                <p className="mb-3 inline-flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-[#0F7352]"><span className="h-2 w-8 rounded-full bg-[#FFB72B]" /> Feito em Manaus, pra Manaus</p>
                <h1 className="max-w-2xl text-5xl font-black leading-[.94] tracking-[-0.065em] text-[#063f2e] sm:text-[3.6rem] lg:text-[4.25rem]">Um lugar em Manaus pra chamar de <span className="relative whitespace-nowrap">seu.<svg className="absolute -bottom-2 left-0 h-3 w-full text-[#FFB72B]" viewBox="0 0 220 14" preserveAspectRatio="none" aria-hidden="true"><path d="M3 10c46-8 133-8 214-4" fill="none" stroke="currentColor" strokeWidth="7" strokeLinecap="round" /></svg></span></h1>
                <p className="mt-5 max-w-xl text-lg leading-relaxed text-[#48685c]">Aqui cabe o anúncio da imobiliária e o da dona da kitnet no Coroado. A gente organiza, mostra quem anunciou e deixa o custo bem claro.</p>

                <form onSubmit={handleSearch} className="mt-6 flex max-w-xl items-center gap-2 rounded-[20px] border-2 border-[#063f2e] bg-white p-1.5 shadow-[5px_5px_0_#FFB72B]">
                  <MapPin className="ml-3 size-5 shrink-0 fill-[#FFB72B] text-[#063f2e]" />
                  <Input value={searchInput} onChange={(event) => { setSearchInput(event.target.value); if (searchError) setSearchError("") }} list="bairros-manaus" placeholder="Digite um bairro ou uma região" aria-label="Buscar por bairro ou região" aria-describedby={searchError ? "search-feedback" : undefined} className="h-12 border-0 bg-transparent px-2 text-base text-[#063f2e] shadow-none placeholder:text-[#789087] focus-visible:ring-0" />
                  <datalist id="bairros-manaus">{properties.map((property) => <option key={property.id} value={property.neighborhood} />)}</datalist>
                  <Button type="submit" className="size-11 shrink-0 rounded-2xl bg-[#063f2e] p-0 text-white hover:bg-[#0B513B] sm:h-12 sm:w-auto sm:px-5" aria-label="Buscar cantinhos"><Search className="size-5" /><span className="hidden font-extrabold sm:inline">Buscar</span></Button>
                </form>
                {searchError && <div id="search-feedback" aria-live="polite" className="max-w-xl pt-3"><p role="alert" className="flex items-start gap-2 rounded-2xl bg-[#FFF0CE] px-4 py-3 text-sm font-bold text-[#7A4A00]"><Search className="mt-0.5 size-4 shrink-0" />{searchError}</p></div>}

                <div className="mt-2 max-w-xl rounded-[20px] border border-[#063f2e]/12 bg-white/65 p-3">
                  <p className="mb-2 text-[11px] font-extrabold uppercase tracking-[0.1em] text-[#60776e]">Ou escolha pela lista</p>
                  <div className="grid gap-2 sm:grid-cols-[1fr_1.25fr_auto]">
                    <Select value={selectedRegion} onValueChange={(value) => { setSelectedRegion(value); setSelectedNeighborhood("all"); setSearchError("") }}>
                      <SelectTrigger className="h-10 w-full rounded-xl border-[#063f2e]/15 bg-white font-bold text-[#315a4c] shadow-none" aria-label="Escolher zona de Manaus"><SelectValue>{selectedRegion === "all" ? "Todas as zonas" : locationGroups.find((region) => region.id === selectedRegion)?.label}</SelectValue></SelectTrigger>
                      <SelectContent className="border-[#063f2e]/10 bg-[#FFFDF7]">
                        <SelectItem value="all">Todas as zonas</SelectItem>
                        {locationGroups.map((region) => <SelectItem key={region.id} value={region.id}>{region.emoji} {region.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Select value={selectedNeighborhood} onValueChange={(value) => { setSelectedNeighborhood(value); setSearchError("") }}>
                      <SelectTrigger className="h-10 w-full rounded-xl border-[#063f2e]/15 bg-white font-bold text-[#315a4c] shadow-none" aria-label="Escolher bairro"><SelectValue>{selectedRegion === "all" ? "Todos os bairros" : selectedNeighborhood === "all" ? "Todos os bairros da zona" : selectedNeighborhood}</SelectValue></SelectTrigger>
                      <SelectContent className="border-[#063f2e]/10 bg-[#FFFDF7]">
                        <SelectItem value="all">Todos os bairros da zona</SelectItem>
                        {availableNeighborhoods.map((neighborhood) => <SelectItem key={neighborhood} value={neighborhood}>{neighborhood}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Button type="button" onClick={handleLocationSearch} className="h-10 rounded-xl bg-[#FFB72B] px-4 font-extrabold text-[#063f2e] shadow-none hover:bg-[#FFC44D]" aria-label="Buscar na localização selecionada">Ver cantinhos</Button>
                  </div>
                </div>

                <div className="mt-4 flex max-w-2xl flex-wrap gap-2" aria-label="Filtros rápidos">
                  {quickFilters.map((filter) => (
                    <button key={filter.id} type="button" onClick={() => handleQuickFilter(filter.id)} aria-pressed={activeFilter === filter.id} className={cn("rounded-full border px-3.5 py-2 text-xs font-bold transition", activeFilter === filter.id ? "border-[#063f2e] bg-[#063f2e] text-white" : "border-[#063f2e]/15 bg-white/60 text-[#315a4c] hover:border-[#FFB72B] hover:bg-[#FFB72B]/15")}><span className="mr-1.5" aria-hidden="true">{filter.emoji}</span>{filter.label}</button>
                  ))}
                </div>
              </div>

              <div className="relative mx-auto w-full max-w-[700px] lg:mx-0 lg:mt-12 lg:translate-x-6">
                <div className="absolute -left-6 -top-5 size-20 rounded-[24px] bg-[#FFB72B] sm:-left-9 sm:size-28" />
                <div className="absolute -bottom-7 -right-8 size-32 rounded-full border-[18px] border-[#0F7352]/12" />
                <div className="relative aspect-[4/3] overflow-hidden rounded-[48px_48px_48px_12px] border-[6px] border-white bg-[#032b20] shadow-[0_20px_50px_rgba(6,63,46,.16)]">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={properties[4].images[0]} alt="" aria-hidden="true" className="absolute inset-0 size-full scale-110 object-cover opacity-45 blur-2xl" />
                  <div className="absolute inset-0 bg-[#032b20]/20" />
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={properties[4].images[0]} alt="Casa para alugar na Ponta Negra, em Manaus" className="relative z-10 size-full object-contain" />
                  <div className="absolute inset-x-0 bottom-0 z-20 bg-gradient-to-t from-[#032b20] via-[#032b20]/75 to-transparent px-6 pb-6 pt-24 text-white sm:px-8 sm:pb-8">
                    <p className="text-xs font-bold text-[#FFCA57]">Ponta Negra · Manaus</p><p className="mt-1 text-2xl font-black tracking-[-0.04em]">Casa em condomínio</p><p className="mt-2 text-sm text-white/75">4 quartos · 210 m² · aceita pet</p>
                  </div>
                </div>
                <div className="absolute -bottom-5 -left-4 z-30 rotate-[-3deg] rounded-[18px] bg-[#FFB72B] px-5 py-4 text-[#063f2e] shadow-lg sm:-left-10">
                  <p className="text-[10px] font-black uppercase tracking-[0.12em]">Aluguel + taxas</p><p className="mt-0.5 text-xl font-black">R$ 5.550 <span className="text-xs">/ mês</span></p>
                </div>
              </div>
            </div>
          </section>

          <section id="imoveis" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-14 sm:px-6 sm:py-20 lg:px-8">
            <div className="mb-8 flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
              <div>
                <p className="mb-2 flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em] text-[#C57C00]"><SlidersHorizontal className="size-4" /> Cantinhos disponíveis</p>
                <h2 className="text-3xl font-black tracking-[-0.045em] text-[#063f2e] sm:text-4xl">{filteredProperties.length === 1 ? "1 cantinho encontrado" : `${filteredProperties.length} cantinhos encontrados`}</h2>
                <p className="mt-2 text-sm text-[#60776e]">No mapa, as cores mostram quem publicou cada anúncio.</p>
                {(query || activeFilter || hasBasicFilters) && <button type="button" onClick={resetFilters} className="mt-2 text-xs font-bold text-[#0F7352] underline decoration-[#FFB72B] decoration-2 underline-offset-4">Limpar busca e ver tudo</button>}
              </div>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <Toggle pressed={showTotal} onPressedChange={setShowTotal} variant="outline" className="h-auto min-h-12 justify-start rounded-full border-2 border-[#063f2e]/15 bg-[#FBF7EB] px-4 py-2.5 text-left text-xs font-bold text-[#315a4c] shadow-none hover:bg-white data-[state=on]:border-[#063f2e] data-[state=on]:bg-[#063f2e] data-[state=on]:text-white sm:text-sm" aria-label="Exibir custo total mensal">
                  <span className={cn("relative h-6 w-10 shrink-0 rounded-full bg-[#C9C4B6] transition-colors", showTotal && "bg-[#FFB72B]")}><span className={cn("absolute left-1 top-1 size-4 rounded-full bg-white shadow-sm transition-transform", showTotal && "translate-x-4 bg-[#063f2e]")} /></span>
                  Somar aluguel + condomínio + IPTU
                </Toggle>
                <Dialog>
                  <DialogTrigger asChild>
                    <Button type="button" variant="outline" className="h-12 rounded-full border-2 border-[#063f2e] bg-[#FBF7EB] px-5 font-extrabold text-[#063f2e] shadow-none hover:bg-[#063f2e] hover:text-white"><SlidersHorizontal className="size-4" /> Filtros {activePropertyFilterCount > 0 && <span className="flex size-5 items-center justify-center rounded-full bg-[#FFB72B] text-[10px] text-[#063f2e]">{activePropertyFilterCount}</span>}</Button>
                  </DialogTrigger>
                  <DialogContent className="max-h-[90vh] overflow-y-auto rounded-[28px] border-0 bg-[#FBF7EB] p-6 sm:max-w-2xl sm:p-8">
                    <DialogHeader className="pr-8"><DialogTitle className="text-3xl font-black tracking-[-0.04em] text-[#063f2e]">Filtrar cantinhos</DialogTitle><DialogDescription className="text-[#60776e]">Escolha o que importa para sua busca. Os filtros funcionam junto com bairro e região.</DialogDescription></DialogHeader>
                    <div className="grid gap-4 py-2 sm:grid-cols-2">
                      <FilterField label="Quartos">
                        <Select value={bedroomFilter} onValueChange={(value) => { setBedroomFilter(value); setVisibleCount(12) }}>
                          <SelectTrigger className="h-11 w-full rounded-xl border-[#063f2e]/15 bg-white font-bold text-[#315a4c] shadow-none"><BedDouble className="size-4 text-[#0F7352]" /><SelectValue>{bedroomFilter === "any" ? "Qualquer" : bedroomFilter === "3+" ? "3 ou mais" : bedroomFilter}</SelectValue></SelectTrigger>
                          <SelectContent className="z-[70] border-[#063f2e]/10 bg-[#FFFDF7]"><SelectItem value="any">Qualquer</SelectItem><SelectItem value="1">1 quarto</SelectItem><SelectItem value="2">2 quartos</SelectItem><SelectItem value="3+">3 quartos ou mais</SelectItem></SelectContent>
                        </Select>
                      </FilterField>
                      <FilterField label="Banheiros">
                        <Select value={bathroomFilter} onValueChange={(value) => { setBathroomFilter(value); setVisibleCount(12) }}>
                          <SelectTrigger className="h-11 w-full rounded-xl border-[#063f2e]/15 bg-white font-bold text-[#315a4c] shadow-none"><Bath className="size-4 text-[#0F7352]" /><SelectValue>{bathroomFilter === "any" ? "Qualquer" : bathroomFilter === "2+" ? "2 ou mais" : bathroomFilter}</SelectValue></SelectTrigger>
                          <SelectContent className="z-[70] border-[#063f2e]/10 bg-[#FFFDF7]"><SelectItem value="any">Qualquer</SelectItem><SelectItem value="1">1 banheiro</SelectItem><SelectItem value="2+">2 banheiros ou mais</SelectItem></SelectContent>
                        </Select>
                      </FilterField>
                      <FilterField label="Garagem">
                        <Select value={parkingFilter} onValueChange={(value) => { setParkingFilter(value); setVisibleCount(12) }}>
                          <SelectTrigger className="h-11 w-full rounded-xl border-[#063f2e]/15 bg-white font-bold text-[#315a4c] shadow-none"><CarFront className="size-4 text-[#0F7352]" /><SelectValue>{parkingFilter === "any" ? "Qualquer" : parkingFilter === "2+" ? "2 vagas ou mais" : "1 vaga ou mais"}</SelectValue></SelectTrigger>
                          <SelectContent className="z-[70] border-[#063f2e]/10 bg-[#FFFDF7]"><SelectItem value="any">Qualquer</SelectItem><SelectItem value="1">1 vaga ou mais</SelectItem><SelectItem value="2+">2 vagas ou mais</SelectItem></SelectContent>
                        </Select>
                      </FilterField>
                      <FilterField label="Pet">
                        <Select value={petFilter} onValueChange={(value) => { setPetFilter(value); setVisibleCount(12) }}>
                          <SelectTrigger className="h-11 w-full rounded-xl border-[#063f2e]/15 bg-white font-bold text-[#315a4c] shadow-none"><PawPrint className="size-4 text-[#0F7352]" /><SelectValue>{petFilter === "any" ? "Qualquer" : petFilter === "yes" ? "Aceita pet: sim" : "Aceita pet: não"}</SelectValue></SelectTrigger>
                          <SelectContent className="z-[70] border-[#063f2e]/10 bg-[#FFFDF7]"><SelectItem value="any">Qualquer</SelectItem><SelectItem value="yes">Aceita pet: sim</SelectItem><SelectItem value="no">Aceita pet: não</SelectItem></SelectContent>
                        </Select>
                      </FilterField>
                      <FilterField label="Faixa de aluguel" className="sm:col-span-2">
                        <Select value={priceFilter} onValueChange={(value) => { setPriceFilter(value); setVisibleCount(12) }}>
                          <SelectTrigger className="h-11 w-full rounded-xl border-[#063f2e]/15 bg-white font-bold text-[#315a4c] shadow-none"><CircleDollarSign className="size-4 text-[#0F7352]" /><SelectValue>{priceFilter === "any" ? "Qualquer valor" : priceFilter === "2500+" ? "A partir de R$ 2.500" : `Até R$ ${Number(priceFilter).toLocaleString("pt-BR")}`}</SelectValue></SelectTrigger>
                          <SelectContent className="z-[70] border-[#063f2e]/10 bg-[#FFFDF7]"><SelectItem value="any">Qualquer valor</SelectItem><SelectItem value="1200">Até R$ 1.200</SelectItem><SelectItem value="1800">Até R$ 1.800</SelectItem><SelectItem value="2500">Até R$ 2.500</SelectItem><SelectItem value="2500+">A partir de R$ 2.500</SelectItem></SelectContent>
                        </Select>
                      </FilterField>
                    </div>
                    <DialogFooter className="border-t border-[#063f2e]/10 pt-4 sm:justify-between"><Button type="button" onClick={clearBasicFilters} variant="ghost" disabled={!hasBasicFilters} className="rounded-full font-bold text-[#60776e]"><X className="size-4" /> Limpar filtros</Button><DialogClose asChild><Button className="h-11 rounded-full bg-[#063f2e] px-6 font-extrabold text-white hover:bg-[#0B513B]">Ver {filteredProperties.length} {filteredProperties.length === 1 ? "cantinho" : "cantinhos"}</Button></DialogClose></DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </div>

            {filteredProperties.length > 0 ? <div className="grid items-start gap-7 xl:grid-cols-[minmax(0,.88fr)_minmax(0,1.12fr)]"><PropertyMap properties={filteredProperties} /><div><div className="grid gap-7 md:grid-cols-2">{visibleProperties.map((property) => <PropertyCard key={property.id} property={property} showTotal={showTotal} />)}</div>{visibleCount < filteredProperties.length && <Button type="button" onClick={() => setVisibleCount((count) => count + 12)} variant="outline" className="mt-7 h-11 w-full rounded-full border-2 border-[#063f2e]/20 bg-[#FBF7EB] font-extrabold text-[#063f2e]">Carregar mais cantinhos</Button>}</div></div> : (
              <div className="rounded-[32px] border-2 border-dashed border-[#063f2e]/20 bg-[#FBF7EB] px-6 py-16 text-center"><span className="mx-auto flex size-12 items-center justify-center rounded-full bg-[#FFB72B]"><Search className="size-5" /></span><h2 className="mt-4 text-xl font-black">{hasBasicFilters ? "Nenhum cantinho com esses filtros" : "Lugar não encontrado"}</h2><p className="mt-1 text-sm text-[#60776e]">{hasBasicFilters ? "Tente reduzir a quantidade de filtros para encontrar mais opções." : "Ainda não temos um cantinho nesse local. Tente outro bairro ou volte para todos."}</p><Button onClick={() => { resetFilters(); scrollToResults() }} className="mt-5 rounded-full bg-[#063f2e] font-bold">Ver todos</Button></div>
            )}
          </section>

          <section id="como-funciona" className="bg-[#063f2e] py-16 text-[#FBF7EB] sm:py-20">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <div className="grid gap-12 lg:grid-cols-[.75fr_1.25fr] lg:gap-24">
                <div><p className="text-xs font-black uppercase tracking-[0.16em] text-[#FFB72B]">Como funciona</p><h2 className="mt-4 text-4xl font-black leading-tight tracking-[-0.05em] sm:text-5xl">Veja preço, taxas e origem no mesmo lugar.</h2><p className="mt-5 max-w-md leading-relaxed text-[#B9CEC6]">Cada anúncio separa aluguel, condomínio e IPTU. Você também vê se quem publicou foi proprietário, corretor ou outra plataforma.</p></div>
                <div className="divide-y divide-white/15 border-y border-white/15">
                  {["Busque pelo bairro, pela zona ou por um ponto de referência.", "Confira fotos, vagas, taxas e quem publicou o anúncio.", "Abra o WhatsApp com o código do imóvel já preenchido."].map((text, index) => (
                    <div key={text} className="grid grid-cols-[54px_1fr_auto] items-center gap-3 py-6 sm:py-7"><span className="text-sm font-black text-[#FFB72B]">0{index + 1}</span><p className="text-lg font-bold leading-snug sm:text-xl">{text}</p><ArrowUpRight className="size-5 text-[#FFB72B]" /></div>
                  ))}
                </div>
              </div>
            </div>
          </section>

          <section id="para-quem-anuncia" className="bg-[#FBF7EB] py-16 sm:py-20">
            <div className="mx-auto grid max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-2 lg:items-center lg:gap-20 lg:px-8">
              <div className="relative rounded-[36px] bg-[#FFB72B] p-8 text-[#063f2e] sm:p-10">
                <Megaphone className="size-14" strokeWidth={1.8} /><p className="mt-8 text-3xl font-black leading-tight tracking-[-0.045em] sm:text-4xl">O imóvel que circula no boca a boca também pode aparecer aqui.</p><div className="absolute -right-3 -top-3 size-10 rounded-full border-[8px] border-[#0F7352]" />
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-[#0F7352]">Para quem anuncia</p><h2 className="mt-3 text-3xl font-black tracking-[-0.045em] text-[#063f2e]">Proprietário também pode anunciar.</h2><p className="mt-4 leading-relaxed text-[#60776e]">Perto da UFAM e em bairros como Coroado, muita oferta circula por indicação. O Alugaí coloca esses imóveis na busca sem exigir imobiliária ou corretor.</p>
                <div className="mt-7 grid gap-4">{["Proprietário informa bairro e WhatsApp", "Corretor aparece identificado no anúncio", "Anúncio agregado mantém a fonte original"].map((item) => <div key={item} className="flex items-center gap-3 font-bold text-[#315a4c]"><span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-[#FFB72B]"><Check className="size-4 stroke-[3]" /></span>{item}</div>)}</div>
              </div>
            </div>
          </section>
        </main>

        <footer className="border-t border-[#063f2e]/10 bg-[#FBF7EB]">
          <div className="mx-auto flex max-w-7xl flex-col gap-5 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:px-6 lg:px-8"><BrandLogo className="scale-90 origin-left" /><div className="flex items-center gap-2 text-xs font-bold text-[#60776e]"><MapPin className="size-4 fill-[#FFB72B] text-[#063f2e]" /> Cantinhos para alugar em Manaus</div></div>
        </footer>
      </div>
    </TooltipProvider>
  )
}

function FilterField({ label, children, className }: { label: string; children: ReactNode; className?: string }) {
  return <div className={cn("grid gap-2", className)}><p className="text-xs font-extrabold uppercase tracking-[0.08em] text-[#60776e]">{label}</p>{children}</div>
}
