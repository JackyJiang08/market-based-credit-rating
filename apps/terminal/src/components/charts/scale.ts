/** Tiny scale helpers — enough that visx/recharts are not needed. */
export const logScale =
  (domain: [number, number], range: [number, number]) => (v: number) => {
    const [d0, d1] = domain.map(Math.log);
    const t = (Math.log(v) - d0) / (d1 - d0);
    return range[0] + t * (range[1] - range[0]);
  };

export const linScale =
  (domain: [number, number], range: [number, number]) => (v: number) => {
    const t = (v - domain[0]) / (domain[1] - domain[0] || 1);
    return range[0] + t * (range[1] - range[0]);
  };

export function logTicks([lo, hi]: [number, number]): number[] {
  const out: number[] = [];
  for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) {
    const v = 10 ** e;
    if (v >= lo && v <= hi) out.push(v);
  }
  return out;
}
