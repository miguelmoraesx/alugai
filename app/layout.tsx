import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Alugaí | Aluguel residencial em Manaus",
  description: "Encontre imóveis verificados para alugar em Manaus e compare o custo total mensal.",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR">
      <body className="antialiased">{children}</body>
    </html>
  );
}
