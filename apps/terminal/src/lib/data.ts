/** Data loading: fetch + Zod parse. A schema failure is an error state, never
 *  silently-partial UI. */
import { CompanyDetail, Universe } from "./schemas";

export async function loadUniverse(): Promise<Universe> {
  const r = await fetch("/data/universe.json");
  if (!r.ok) throw new Error(`universe.json: HTTP ${r.status}`);
  return Universe.parse(await r.json());
}

export async function loadCompany(ticker: string): Promise<CompanyDetail> {
  const r = await fetch(`/data/companies/${ticker.toUpperCase()}.json`);
  if (r.status === 404) throw new Error("NO_DETAIL");
  if (!r.ok) throw new Error(`company ${ticker}: HTTP ${r.status}`);
  return CompanyDetail.parse(await r.json());
}
