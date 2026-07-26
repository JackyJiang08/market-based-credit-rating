"use client";

/** The one-click requirement: ⌘K or `/`, type, enter → company view. */
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { loadUniverse } from "@/lib/data";
import { fuzzyScore } from "@/lib/format";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

export function CommandBar() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const router = useRouter();
  const { data } = useQuery({ queryKey: ["universe"], queryFn: loadUniverse });

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && tag !== "INPUT")) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  const hits = useMemo(() => {
    const rows = data?.rows ?? [];
    if (!q) return rows.slice(0, 12);
    return rows
      .map((r) => ({
        r,
        s: Math.max(fuzzyScore(q, r.ticker), fuzzyScore(q, r.name ?? "")),
      }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 12)
      .map((x) => x.r);
  }, [data, q]);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="flex w-64 items-center justify-between rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-left text-sm text-zinc-400 hover:border-zinc-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
        aria-label="Search companies (Command+K or /)"
      >
        <span>Search ticker or company…</span>
        <kbd className="rounded border border-zinc-600 bg-zinc-800 px-1.5 font-mono text-[10px] text-zinc-400">
          ⌘K
        </kbd>
      </button>
      <CommandDialog open={open} onOpenChange={setOpen} title="Company search">
        <CommandInput
          placeholder="Type a ticker or company name…"
          value={q}
          onValueChange={setQ}
        />
        <CommandList>
          <CommandEmpty>No match in the 150-name universe.</CommandEmpty>
          <CommandGroup heading="Universe">
            {hits.map((r) => (
              <CommandItem
                key={r.ticker}
                value={`${r.ticker} ${r.name ?? ""}`}
                onSelect={() => {
                  setOpen(false);
                  router.push(`/company/${r.ticker}/`);
                }}
              >
                <span className="w-16 font-mono font-semibold">{r.ticker}</span>
                <span className="flex-1 truncate text-zinc-400">{r.name}</span>
                <span className="font-mono text-xs text-zinc-500">
                  {r.determination ?? ""}
                </span>
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </CommandDialog>
    </>
  );
}
