"use client"

import { ArrowUpRight, Building2, UserRound } from "lucide-react"
import { BrandLogo } from "@/components/brand-logo"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-[#063f2e]/10 bg-[#FBF7EB]/95 backdrop-blur-md">
      <div className="mx-auto flex h-[82px] max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <a href="#inicio" aria-label="Alugaí — início"><BrandLogo /></a>
        <nav className="hidden items-center gap-7 text-[13px] font-bold text-[#315a4c] md:flex" aria-label="Navegação principal">
          <a className="border-b-2 border-transparent py-2 transition-colors hover:border-[#FFB72B] hover:text-[#063f2e]" href="#imoveis">Imóveis</a>
          <a className="border-b-2 border-transparent py-2 transition-colors hover:border-[#FFB72B] hover:text-[#063f2e]" href="#como-funciona">Como funciona</a>
          <a className="border-b-2 border-transparent py-2 transition-colors hover:border-[#FFB72B] hover:text-[#063f2e]" href="#verificacao">Nossa checagem</a>
        </nav>
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline" className="h-11 rounded-full border-2 border-[#063f2e] bg-transparent px-4 font-extrabold text-[#063f2e] shadow-none hover:bg-[#063f2e] hover:text-[#FBF7EB] sm:px-5">
              <span className="hidden sm:inline">Anunciar meu imóvel</span><span className="sm:hidden">Anunciar</span><ArrowUpRight className="size-4" />
            </Button>
          </DialogTrigger>
          <DialogContent className="overflow-hidden rounded-[28px] border-0 bg-[#FBF7EB] p-0 sm:max-w-md">
            <div className="bg-[#FFB72B] px-6 py-6 text-[#063f2e]">
              <span className="mb-4 flex size-11 items-center justify-center rounded-2xl bg-[#063f2e] text-[#FBF7EB]"><Building2 className="size-5" /></span>
              <DialogHeader><DialogTitle className="text-2xl font-black tracking-[-0.04em]">Tem um imóvel pra alugar?</DialogTitle><DialogDescription className="text-[#164c3a]">Você não precisa ser corretor. Proprietários também podem anunciar direto e sem complicação.</DialogDescription></DialogHeader>
            </div>
            <form className="grid gap-3 px-6 pb-6" onSubmit={(event) => event.preventDefault()}>
              <fieldset><legend className="mb-2 text-xs font-bold text-[#60776e]">Você anuncia como:</legend><div className="grid grid-cols-2 gap-2"><label className="flex cursor-pointer items-center gap-2 rounded-2xl border-2 border-[#063f2e] bg-white px-3 py-3 text-xs font-extrabold text-[#063f2e]"><input type="radio" name="advertiser" defaultChecked className="accent-[#063f2e]" /><UserRound className="size-4" /> Proprietário</label><label className="flex cursor-pointer items-center gap-2 rounded-2xl border border-[#063f2e]/15 bg-white px-3 py-3 text-xs font-bold text-[#315a4c]"><input type="radio" name="advertiser" className="accent-[#063f2e]" /><Building2 className="size-4" /> Corretor</label></div></fieldset>
              <Input aria-label="Seu nome" placeholder="Como podemos te chamar?" className="h-12 rounded-2xl border-[#063f2e]/15 bg-white" />
              <Input aria-label="WhatsApp" placeholder="WhatsApp com DDD" className="h-12 rounded-2xl border-[#063f2e]/15 bg-white" />
              <Input aria-label="Bairro do imóvel" placeholder="Em qual bairro fica?" className="h-12 rounded-2xl border-[#063f2e]/15 bg-white" />
              <Button className="mt-1 h-12 rounded-full bg-[#063f2e] font-extrabold text-white hover:bg-[#0B513B]">Enviar para checagem</Button>
              <p className="text-center text-xs text-[#60776e]">Sem custo e sem compromisso.</p>
            </form>
          </DialogContent>
        </Dialog>
      </div>
    </header>
  )
}
