"use client";

import { CommandBar } from "@/components/command-bar";
import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/universe/", label: "Universe" },
  { href: "/plane/", label: "µ–CCM plane" },
  { href: "/sensitivity/", label: "Sensitivity" },
  { href: "/validation/", label: "Validation" },
  { href: "/about/", label: "About" },
];

export function Nav() {
  const path = usePathname();
  return (
    <nav
      aria-label="primary"
      className="sticky top-0 z-40 -mx-4 mb-2 flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-zinc-800 bg-zinc-950/95 px-4 py-2.5 backdrop-blur"
    >
      <Link href="/" className="font-semibold text-zinc-50">
        creditrating <span className="text-sky-300">terminal</span>
      </Link>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
        {LINKS.map((l) => (
          <Link
            key={l.href}
            href={l.href}
            aria-current={path?.startsWith(l.href) ? "page" : undefined}
            className={`rounded px-1.5 py-0.5 underline-offset-4 hover:text-zinc-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400 ${
              path?.startsWith(l.href) ? "text-sky-300" : "text-zinc-400"
            }`}
          >
            {l.label}
          </Link>
        ))}
        <a
          href="https://github.com/JackyJiang08/market-based-credit-rating"
          className="rounded px-1.5 py-0.5 text-zinc-400 underline-offset-4 hover:text-zinc-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        >
          GitHub
        </a>
      </div>
      <div className="ml-auto">
        <CommandBar />
      </div>
    </nav>
  );
}
