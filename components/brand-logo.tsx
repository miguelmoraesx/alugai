import { cn } from "@/lib/utils"

export function BrandLogo({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5 text-[#063f2e]", className)} aria-label="Alugaí">
      <svg viewBox="0 0 66 58" className="h-[42px] w-[48px] shrink-0" aria-hidden="true">
        <path d="M7 27.4 30.6 7.3a5 5 0 0 1 6.5 0l8.2 7V8.8c0-2 1.6-3.6 3.6-3.6h6.3c2 0 3.6 1.6 3.6 3.6v17.1l2.2 1.9c2.2 1.9 2.5 5.2.6 7.4-1.9 2.2-5.2 2.5-7.4.6L33.8 18.4 13.7 35.5a5.2 5.2 0 0 1-7.4-.6 5.2 5.2 0 0 1 .7-7.5Z" fill="currentColor"/>
        <path d="M17.2 35.6 33.8 21.5l16.7 14.2v17.1a4.2 4.2 0 0 1-4.2 4.2H21.4a4.2 4.2 0 0 1-4.2-4.2V35.6Z" fill="currentColor"/>
        <path d="M34 27.4c-7.3 0-13.2 5.9-13.2 13.2 0 9.5 13.2 20.3 13.2 20.3s13.2-10.8 13.2-20.3c0-7.3-5.9-13.2-13.2-13.2Z" fill="#FFB72B" stroke="#FBF7EB" strokeWidth="3"/>
        <circle cx="34" cy="40.5" r="4.4" fill="#FBF7EB"/>
      </svg>
      {!compact && (
        <span className="brand-wordmark relative text-[2rem] font-black leading-none tracking-[-0.07em]">
          Alugaí
          <span className="absolute right-[1px] top-[-7px] h-2.5 w-3.5 -rotate-45 rounded-full bg-[#FFB72B]" />
        </span>
      )}
    </span>
  )
}
