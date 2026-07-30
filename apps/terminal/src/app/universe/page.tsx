import { UniverseView } from "@/components/universe-view";
import fs from "node:fs";
import path from "node:path";
import type { Universe } from "@/lib/schemas";

export const metadata = { title: "Universe — Credit Rating Terminal" };

function universeAtBuildTime(): Universe {
  const p = path.join(process.cwd(), "public", "data", "universe.json");
  return JSON.parse(fs.readFileSync(p, "utf-8")) as Universe;
}

export default function UniversePage() {
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold text-zinc-50">The 150-name universe</h1>
        <p className="text-xs text-zinc-400">
          rated names first · names without estimates grouped at the bottom · every
          letter with its interval · documented convention (run of record)
        </p>
      </div>
      <UniverseView initial={universeAtBuildTime()} />
    </div>
  );
}
