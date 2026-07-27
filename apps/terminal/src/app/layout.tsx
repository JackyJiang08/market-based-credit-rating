import { Nav } from "@/components/nav";
import { Providers } from "@/components/providers";
import { TooltipProvider } from "@/components/ui/tooltip";
import type { Metadata } from "next";
import Link from "next/link";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";

const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

const base = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

export const metadata: Metadata = {
  metadataBase: new URL("https://jackyjiang08.github.io"),
  title: "creditrating terminal",
  description:
    "Market-based credit ratings (KMV/Merton + TiC): a 150-name universe, " +
    "uncertainty-honest letters, and an agency validation study — computed " +
    "offline, rendered live.",
  icons: { icon: `${base}/favicon.svg` },
  openGraph: {
    title: "creditrating terminal",
    description:
      "RiskScore first; the letter never without its interval. The µ–CCM " +
      "plane, the ×4,073 amplification, and a sourced agency validation.",
    images: [`${base}/og.png`],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <head>
        <link
          rel="preload"
          href={`${base}/data/universe.json`}
          as="fetch"
          crossOrigin="anonymous"
        />
      </head>
      <body
        className={`${mono.variable} min-h-screen bg-zinc-950 font-sans text-zinc-200 antialiased`}
      >
        <Providers>
          <TooltipProvider delay={150}>
            <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4">
              <Nav />
              <main className="flex-1 py-4">{children}</main>
              <footer className="border-t border-zinc-800 py-3 text-[11px] leading-relaxed text-zinc-400">
                <span className="font-medium text-zinc-400">Fixture-backed demo</span> — all
                numbers computed offline from committed data (vintage: prices through{" "}
                <span className="font-mono">2026-07-24</span>). Not investment advice.
                Independent implementation of the Time-Consistent (TiC) credit-rating
                methodology (Y. Yang) —{" "}
                <Link
                  className="underline decoration-zinc-600 underline-offset-2 hover:text-zinc-300"
                  href="https://github.com/JackyJiang08/market-based-credit-rating#methodology--acknowledgements"
                >
                  methodology &amp; acknowledgements
                </Link>
                . A letter rating is a derived, wide-interval conversion and is never shown
                without its interval.
              </footer>
            </div>
          </TooltipProvider>
        </Providers>
      </body>
    </html>
  );
}
