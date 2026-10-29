"use client"

import { Building2, Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/90 backdrop-blur-xl">
      <div className="mx-auto flex h-18 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <a href="#inicio" className="group flex items-center gap-3" aria-label="Alugaí — início">
          <span className="flex size-9 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm shadow-emerald-200"><Building2 className="size-4.5" /></span>
          <span className="relative text-xl font-bold tracking-[-0.04em] text-slate-950">Alugaí<span className="absolute -right-0.5 top-0 size-1.5 rounded-full bg-emerald-500" /></span>
          <Badge variant="outline" className="hidden rounded-full border-slate-200 bg-slate-50 px-2.5 py-1 font-medium text-slate-500 sm:inline-flex">Manaus / AM</Badge>
        </a>
        <nav className="hidden items-center gap-8 text-sm font-medium text-slate-600 md:flex" aria-label="Navegação principal">
          <a className="transition-colors hover:text-emerald-700" href="#como-funciona">Como funciona</a>
          <a className="transition-colors hover:text-emerald-700" href="#verificacao">Sobre a verificação</a>
        </nav>
        <div className="flex items-center gap-2">
          <Dialog>
            <DialogTrigger asChild><Button variant="outline" className="rounded-xl border-slate-300 bg-white font-semibold text-slate-800 shadow-xs hover:border-emerald-300 hover:bg-emerald-50 hover:text-emerald-800"><span className="hidden sm:inline">Anunciar imóvel</span><span className="sm:hidden">Anunciar</span></Button></DialogTrigger>
            <DialogContent className="rounded-2xl border-slate-200 bg-white p-0 sm:max-w-md">
              <div className="rounded-t-2xl bg-emerald-50 px-6 py-5">
                <span className="mb-4 flex size-10 items-center justify-center rounded-xl bg-emerald-600 text-white"><Building2 className="size-5" /></span>
                <DialogHeader><DialogTitle className="text-xl text-slate-950">Anuncie com segurança</DialogTitle><DialogDescription className="text-slate-600">Deixe seus dados e nosso time fará a checagem do imóvel antes da publicação.</DialogDescription></DialogHeader>
              </div>
              <form className="grid gap-3 px-6 pb-6" onSubmit={(event) => event.preventDefault()}>
                <Input aria-label="Seu nome" placeholder="Seu nome" className="h-11 rounded-xl border-slate-200" />
                <Input aria-label="WhatsApp" placeholder="WhatsApp com DDD" className="h-11 rounded-xl border-slate-200" />
                <Input aria-label="Bairro do imóvel" placeholder="Bairro do imóvel" className="h-11 rounded-xl border-slate-200" />
                <Button className="mt-1 h-11 rounded-xl bg-emerald-600 font-semibold hover:bg-emerald-700">Quero anunciar</Button>
                <p className="text-center text-xs text-slate-500">Sem custo para enviar. A publicação depende da verificação.</p>
              </form>
            </DialogContent>
          </Dialog>
          <Button variant="ghost" size="icon" className="md:hidden" aria-label="Abrir menu"><Menu className="size-5" /></Button>
        </div>
      </div>
    </header>
  )
}
