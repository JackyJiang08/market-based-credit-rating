import { PlaneView } from "@/components/plane-view";
import fs from "node:fs";
import path from "node:path";
import type { Universe } from "@/lib/schemas";

export default function PlanePage() {
  const universe = JSON.parse(
    fs.readFileSync(path.join(process.cwd(), "public", "data", "universe.json"), "utf-8"),
  ) as Universe;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-50">µ–CCM plane</h1>
          <p className="text-xs text-zinc-400">
            iso-rating lines with slope Q = 0.6259 (published Table-8 scale)
          </p>
        </div>
      </div>
      <PlaneView initial={universe} />
    </div>
  );
}
