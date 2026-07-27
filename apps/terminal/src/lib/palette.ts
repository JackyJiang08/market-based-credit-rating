/** The docs/figures palette, dark-mode steps (validated; see docs/figures). */
export const P = {
  surface: "#1a1a19",
  ink: "#ffffff",
  ink2: "#c3c2b7",
  muted: "#898781",
  grid: "#2c2c2a",
  base: "#383835",
  accent: "#3987e5", // categorical slot 1 (dark)
  orange: "#d95926", // categorical slot 2 (dark)
  aqua: "#199e70",
  rampLight: "#86b6ef",
} as const;

/** Published Table-8 scale (conversion.py constants — public in this repo). */
export const SP_SCALE: { letter: string; rs: number }[] = [
  { letter: "AAA", rs: 2.7 },
  { letter: "AA", rs: 3.5 },
  { letter: "A", rs: 5.2 },
  { letter: "BBB", rs: 9.9 },
  { letter: "BB", rs: 22.2 },
  { letter: "B", rs: 50.7 },
  { letter: "CCC", rs: 154.8 },
];
export const Q_SP = 0.625913;
/** Published grid axes bounds (documented in GAP_ANALYSIS). */
export const GRID_DOMAIN = { ccm: [0.1, 540], mu: [1, 160] } as const;
