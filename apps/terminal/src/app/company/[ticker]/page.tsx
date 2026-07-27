import { CompanyView } from "@/components/company-view";
import fs from "node:fs";
import path from "node:path";
import type { CompanyDetail } from "@/lib/schemas";

/** Static export: one page per universe ticker, params from the exported JSON.
 *  The detail fixture is baked in at build time so the company view renders
 *  in the static HTML (no fetch needed for first paint). */
export function generateStaticParams() {
  const p = path.join(process.cwd(), "public", "data", "universe.json");
  const universe = JSON.parse(fs.readFileSync(p, "utf-8"));
  return universe.rows.map((r: { ticker: string }) => ({ ticker: r.ticker }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  return { title: `${ticker.toUpperCase()} — Credit Rating Terminal` };
}

export default async function CompanyPage({
  params,
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = await params;
  const detailPath = path.join(
    process.cwd(), "public", "data", "companies", `${ticker.toUpperCase()}.json`,
  );
  const initial = fs.existsSync(detailPath)
    ? (JSON.parse(fs.readFileSync(detailPath, "utf-8")) as CompanyDetail)
    : undefined;
  return <CompanyView ticker={ticker} initial={initial} />;
}
