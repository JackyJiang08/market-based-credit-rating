"use client";

/** The 150-name universe: RiskScore and rank first; sortable; row → company. */
import { FlagChip } from "@/components/flag-chips";
import { RatingCell } from "@/components/rating-cell";
import { Skeleton } from "@/components/ui/skeleton";
import { loadUniverse } from "@/lib/data";
import { fmt } from "@/lib/format";
import type { UniverseRow } from "@/lib/schemas";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

const col = createColumnHelper<UniverseRow>();

const columns = [
  col.accessor("risk_rank", {
    header: "Rank",
    cell: (c) => <span className="text-zinc-400">{fmt(c.getValue(), 0)}</span>,
  }),
  col.accessor("ticker", {
    header: "Ticker",
    cell: (c) => <span className="font-semibold text-zinc-100">{c.getValue()}</span>,
  }),
  col.accessor("name", { header: "Company", cell: (c) => c.getValue() ?? "—" }),
  col.accessor("risk_score", {
    header: "RiskScore",
    cell: (c) => <span className="font-medium text-sky-300">{fmt(c.getValue(), 3)}</span>,
  }),
  col.accessor("sigma_a", { header: "σ_A", cell: (c) => fmt(c.getValue(), 3) }),
  col.accessor("dd", { header: "DD", cell: (c) => fmt(c.getValue(), 2) }),
  col.accessor("letter", {
    header: "Letter (interval)",
    cell: (c) => (
      <RatingCell
        letter={c.getValue()}
        lo={c.row.original.interval_low}
        hi={c.row.original.interval_high}
        notches={c.row.original.interval_notches}
        basis={c.row.original.basis}
        determination={c.row.original.determination}
      />
    ),
  }),
  col.accessor("determination", {
    header: "Determination",
    cell: (c) => <span className="text-xs text-zinc-400">{c.getValue() ?? "—"}</span>,
  }),
  col.display({
    id: "flags",
    header: "Flags",
    cell: (c) => (
      <span className="flex flex-wrap gap-1">
        {c.row.original.weakly_identified ? <FlagChip code="WEAKLY_IDENTIFIED" /> : null}
        {c.row.original.applicability_reason ? (
          <FlagChip code={c.row.original.applicability_reason} />
        ) : null}
      </span>
    ),
  }),
];

export function UniverseTable({ rows }: { rows?: UniverseRow[] }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["universe"],
    queryFn: loadUniverse,
    enabled: rows === undefined,
  });
  const [sorting, setSorting] = useState<SortingState>([{ id: "risk_rank", desc: false }]);
  const router = useRouter();

  const table = useReactTable({
    data: rows ?? data?.rows ?? [],
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (rows === undefined && isLoading)
    return (
      <div className="space-y-1.5" aria-busy="true" aria-label="loading universe">
        {Array.from({ length: 12 }).map((_, i) => (
          <Skeleton key={i} className="h-7 w-full bg-zinc-800" />
        ))}
      </div>
    );
  if (rows === undefined && error)
    return (
      <div role="alert" className="rounded border border-rose-700 bg-rose-950/40 p-4 text-sm">
        Failed to load or validate universe.json: {String(error)}
      </div>
    );
  if (!(rows ?? data?.rows ?? []).length)
    return (
      <div className="p-4 text-sm text-zinc-400">
        No rows match these filters — clear them to see the full universe.
      </div>
    );

  return (
    <table className="w-full border-collapse text-[13px]">
      <thead>
        {table.getHeaderGroups().map((hg) => (
          <tr key={hg.id} className="border-b border-zinc-700 text-left">
            {hg.headers.map((h) => (
              <th key={h.id} className="px-2 py-1.5 font-medium text-zinc-400">
                <button
                  className="hover:text-zinc-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-sky-400"
                  onClick={h.column.getToggleSortingHandler()}
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                  {{ asc: " ↑", desc: " ↓" }[h.column.getIsSorted() as string] ?? ""}
                </button>
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody>
        {table.getRowModel().rows.map((row) => (
          <tr
            key={row.id}
            tabIndex={0}
            className="cursor-pointer border-b border-zinc-800/70 hover:bg-zinc-800/50 focus:outline-none focus-visible:bg-zinc-800/70"
            onClick={() => router.push(`/company/${row.original.ticker}/`)}
            onKeyDown={(e) => {
              if (e.key === "Enter") router.push(`/company/${row.original.ticker}/`);
            }}
          >
            {row.getVisibleCells().map((cell) => (
              <td key={cell.id} className="px-2 py-1 font-mono tabular-nums">
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
