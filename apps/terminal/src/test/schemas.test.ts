/** The exported JSON must satisfy the schemas the app loads it with. */
import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { CompanyDetail, Manifest, Universe } from "@/lib/schemas";

const DATA = path.join(__dirname, "..", "..", "public", "data");

describe("exported data validates against the runtime schemas", () => {
  it("manifest.json", () => {
    const m = Manifest.parse(JSON.parse(fs.readFileSync(path.join(DATA, "manifest.json"), "utf-8")));
    expect(m.files["companies/"].count).toBeGreaterThan(0);
    expect(m.git_sha).toBeTruthy();
    expect(m.data_vintage).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("universe.json has 150 rows and ORCL", () => {
    const u = Universe.parse(JSON.parse(fs.readFileSync(path.join(DATA, "universe.json"), "utf-8")));
    expect(u.rows).toHaveLength(150);
    const orcl = u.rows.find((r) => r.ticker === "ORCL");
    expect(orcl?.letter).toBe("BB");
    expect(orcl?.interval_low).toBe("BBB-");
    expect(orcl?.interval_high).toBe("BB-");
  });

  it("ORCL company detail parses, letter never bare", () => {
    const d = CompanyDetail.parse(
      JSON.parse(fs.readFileSync(path.join(DATA, "companies", "ORCL.json"), "utf-8")),
    );
    expect(d.rating.letter).toBe("BB");
    expect(d.rating.basis).toBeTruthy();
    expect(d.rating.determination).toBeTruthy();
    expect(d.em_path.length).toBeGreaterThan(50);
    expect(d.flags.map((f) => f.code)).toContain("WEAKLY_IDENTIFIED");
  });
});
