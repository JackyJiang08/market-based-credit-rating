"use client";

/** The one-click requirement: ⌘K or `/`, type, arrows, enter → company view.
 *  Self-contained accessible combobox dialog (cmdk crashed under this React
 *  runtime; this is smaller and fully keyboard-driven). */
import { loadUniverse } from "@/lib/data";
import { fuzzyScore } from "@/lib/format";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";

export function CommandBar() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router = useRouter();
  const { data } = useQuery({ queryKey: ["universe"], queryFn: loadUniverse });

  useEffect(() => {
    const down = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && tag !== "INPUT")) {
        e.preventDefault();
        setOpen((o) => !o);
        setQ("");
        setSel(0);
      }
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", down);
    return () => document.removeEventListener("keydown", down);
  }, []);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 0);
  }, [open]);

  const hits = useMemo(() => {
    const rows = data?.rows ?? [];
    if (!q) return rows.slice(0, 10);
    return rows
      .map((r) => ({ r, s: Math.max(fuzzyScore(q, r.ticker), fuzzyScore(q, r.name ?? "")) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, 10)
      .map((x) => x.r);
  }, [data, q]);

  const go = (ticker: string) => {
    setOpen(false);
    router.push(`/company/${ticker}/`);
  };

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
      {open ? (
        <div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 pt-[15vh]"
          onClick={() => setOpen(false)}
          role="presentation"
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-label="Company search"
            className="w-full max-w-lg overflow-hidden rounded-lg border border-zinc-700 bg-zinc-900 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <input
              ref={inputRef}
              role="combobox"
              aria-expanded="true"
              aria-controls="cmdbar-list"
              aria-activedescendant={hits[sel] ? `opt-${hits[sel].ticker}` : undefined}
              placeholder="Type a ticker or company name…"
              className="w-full border-b border-zinc-700 bg-transparent px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setSel(0);
              }}
              onKeyDown={(e) => {
                if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, hits.length - 1)); }
                if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
                if (e.key === "Enter" && hits[sel]) go(hits[sel].ticker);
              }}
            />
            <ul id="cmdbar-list" role="listbox" aria-label="matches" className="max-h-80 overflow-y-auto py-1">
              {hits.length === 0 ? (
                <li className="px-4 py-3 text-sm text-zinc-400">No match in the 150-name universe.</li>
              ) : (
                hits.map((r, i) => (
                  <li key={r.ticker} id={`opt-${r.ticker}`} role="option" aria-selected={i === sel}>
                    <button
                      className={`flex w-full items-center gap-3 px-4 py-2 text-left text-sm ${
                        i === sel ? "bg-sky-500/15 text-zinc-100" : "text-zinc-300 hover:bg-zinc-800"
                      }`}
                      onMouseEnter={() => setSel(i)}
                      onClick={() => go(r.ticker)}
                    >
                      <span className="w-16 font-mono font-semibold">{r.ticker}</span>
                      <span className="flex-1 truncate text-zinc-400">{r.name}</span>
                      <span className="font-mono text-xs text-zinc-400">{r.determination ?? ""}</span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </div>
        </div>
      ) : null}
    </>
  );
}
