/** Formatting: tabular numerics, the interval-attached letter, badges. */

export function fmt(x: number | null | undefined, digits = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return x.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function pct(x: number | null | undefined, digits = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  return `${(100 * x).toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })}%`;
}

export function big(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "—";
  const abs = Math.abs(x);
  if (abs >= 1e12) return `$${(x / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `$${(x / 1e9).toFixed(1)}B`;
  if (abs >= 1e6) return `$${(x / 1e6).toFixed(1)}M`;
  return `$${fmt(x, 0)}`;
}

/** The presentation rule: a letter never renders without its interval. */
export function letterWithInterval(
  letter: string | null,
  lo: string | null,
  hi: string | null,
): string {
  if (!letter) return "—";
  if (lo && hi) return `${letter} (${lo}..${hi})`;
  return `${letter} (interval unavailable)`;
}

export function fuzzyScore(query: string, target: string): number {
  const q = query.toLowerCase();
  const t = target.toLowerCase();
  if (t.startsWith(q)) return 100 - t.length * 0.01;
  if (t.includes(q)) return 60 - t.indexOf(q);
  let qi = 0;
  for (const ch of t) if (ch === q[qi]) qi += 1;
  return qi === q.length ? 30 - t.length * 0.05 : -1;
}
