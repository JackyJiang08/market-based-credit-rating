import { CommandBar } from "@/components/command-bar";
import { CompanyView } from "@/components/company-view";
import fs from "node:fs";
import path from "node:path";
import Link from "next/link";

/** Static export: one page per universe ticker, params from the exported JSON. */
export function generateStaticParams() {
  const p = path.join(process.cwd(), "public", "data", "universe.json");
  const universe = JSON.parse(fs.readFileSync(p, "utf-8"));
  return universe.rows.map((r: { ticker: string }) => ({ ticker: r.ticker }));
}

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <Link
          href="/"
          className="text-sm text-zinc-400 underline-offset-2 hover:text-zinc-200 hover:underline"
        >
          ← universe
        </Link>
        <CommandBar />
      </div>
      <CompanyView ticker={ticker} />
    </div>
  );
}
