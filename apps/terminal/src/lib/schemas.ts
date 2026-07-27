/** Zod schemas: every loaded JSON is validated before use. */
import { z } from "zod";

export const Meta = z.object({
  git_sha: z.string(),
  generated_utc: z.string(),
  package_version: z.string(),
  data_vintage: z.string(),
  source: z.string(),
});

export const UniverseRow = z.object({
  ticker: z.string(),
  name: z.string().nullable(),
  sector: z.string().nullable(),
  risk_score: z.number().nullable(),
  risk_rank: z.number().nullable(),
  sigma_a: z.number().nullable(),
  mu: z.number().nullable(),
  ccm: z.number().nullable(),
  dd: z.number().nullable(),
  letter: z.string().nullable(),
  interval_low: z.string().nullable(),
  interval_high: z.string().nullable(),
  interval_notches: z.number().nullable(),
  basis: z.string().nullable(),
  determination: z.string().nullable(),
  firm_type: z.string().nullable(),
  applicability_reason: z.string().nullable(),
  drift_t: z.number().nullable(),
  weakly_identified: z.boolean().nullable(),
  taxonomy_category: z.string().nullable(),
  taxonomy_detail: z.string().nullable(),
  agency_sp: z.string().nullable(),
  agency_verified: z.string().nullable(),
  detail_available: z.boolean(),
});
export type UniverseRow = z.infer<typeof UniverseRow>;

export const Universe = z.object({
  meta: Meta,
  count: z.number(),
  rows: z.array(UniverseRow),
});
export type Universe = z.infer<typeof Universe>;

export const Flag = z.object({ code: z.string(), text: z.string() });

export const CompanyDetail = z.object({
  meta: Meta,
  ticker: z.string(),
  name: z.string().nullable(),
  sector: z.string().nullable(),
  industry: z.string().nullable(),
  firm_type: z.string().nullable(),
  as_of: z.string().nullable(),
  inputs: z.object({
    st_debt: z.number().nullable(),
    lt_debt: z.number().nullable(),
    default_point: z.number().nullable(),
    equity: z.number().nullable(),
    risk_free: z.number().nullable(),
  }),
  measures: z.object({
    risk_score: z.number().nullable(),
    sigma_a: z.number().nullable(),
    asset_value: z.number().nullable(),
    eta_a: z.number().nullable(),
    dd: z.number().nullable(),
    edf: z.number().nullable(),
    pit_pd: z.number().nullable(),
    ttc_pd: z.number().nullable(),
    ccm: z.number().nullable(),
    mu: z.number().nullable(),
    lambda: z.number().nullable(),
  }),
  rating: z.object({
    letter: z.string().nullable(),
    basis: z.string().nullable(),
    determination: z.string().nullable(),
    interval_low: z.string().nullable(),
    interval_high: z.string().nullable(),
    interval_notches: z.number().nullable(),
    outlook: z.number().nullable(),
    at_floor: z.boolean().nullable(),
    at_scale_top: z.boolean().nullable(),
  }),
  drift: z.object({
    regime: z.string().nullable(),
    t_stat: z.number().nullable(),
    se: z.number().nullable(),
    span_years: z.number().nullable(),
  }),
  applicability: z.object({
    model_applicable: z.boolean().nullable(),
    reason_code: z.string().nullable(),
    reason_text: z.string().nullable(),
  }),
  flags: z.array(Flag),
  provenance: z.object({
    statement_period_end: z.string().nullable(),
    statement_available_at: z.string().nullable(),
    availability_method: z.string().nullable(),
    st_debt_source: z.string().nullable(),
    lt_debt_source: z.string().nullable(),
    debt_source_contradictory: z.union([z.boolean(), z.number()]).nullable(),
    shares_method: z.string().nullable(),
    shares_reference_date: z.string().nullable(),
    cache_fetched_at: z.string().nullable(),
  }),
  bootstrap: z.object({
    sigma_p05: z.number().nullable(),
    sigma_p95: z.number().nullable(),
    defective_fraction: z.number().nullable(),
  }),
  em_path: z.array(z.object({ date: z.string(), asset_value: z.number() })),
  bootstrap_cloud: z.array(z.object({ mu: z.number(), ccm: z.number() })),
  amplification: z
    .object({
      sigma_a: z.number().nullable(),
      risk_score: z.number().nullable(),
      dd: z.number().nullable(),
      ttc_pd: z.number().nullable(),
      pit_pd: z.number().nullable(),
    })
    .nullable(),
});
export type CompanyDetail = z.infer<typeof CompanyDetail>;

export const Manifest = Meta.extend({
  files: z.object({
    "universe.json": z.object({ rows: z.number() }),
    "validation.json": z.object({ sections: z.array(z.string()) }),
    "companies/": z.object({ tickers: z.array(z.string()), count: z.number() }),
  }),
  licensing_note: z.string(),
});

export const ValidationData = z.object({
  meta: Meta,
  amplification_median: z
    .object({
      sigma_a: z.number().nullable(),
      risk_score: z.number().nullable(),
      dd: z.number().nullable(),
      ttc_pd: z.number().nullable(),
      pit_pd: z.number().nullable(),
    })
    .nullable()
    .optional(),
  notch_errors: z
    .array(z.object({ symbol: z.string(), notch_error: z.number() }).loose())
    .optional(),
  discrimination: z
    .array(z.object({ stratum: z.string(), n: z.number(), spearman: z.number() }).loose())
    .optional(),
});
export type ValidationData = z.infer<typeof ValidationData>;
