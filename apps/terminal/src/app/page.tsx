import { CommandBar } from "@/components/command-bar";
import { UniverseView } from "@/components/universe-view";
import fs from "node:fs";
import path from "node:path";
import Link from "next/link";
import type { Universe } from "@/lib/schemas";

/** The data is static: bake the universe into the HTML so the table is the
 *  initial paint, not a post-hydration fetch. */
function universeAtBuildTime(): Universe {
  const p = path.join(process.cwd(), "public", "data", "universe.json");
  return JSON.parse(fs.readFileSync(p, "utf-8")) as Universe;
}

export default function Home() {
  const universe = universeAtBuildTime();
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-50">
            creditrating <span className="text-sky-300">terminal</span>
          </h1>
          <p className="text-xs text-zinc-400">
            150-name universe · RiskScore first · <kbd className="font-mono">⌘K</kbd> or{" "}
            <kbd className="font-mono">/</kbd> to jump ·{" "}
            <Link href="/plane/" className="underline underline-offset-2 hover:text-zinc-300">
              µ–CCM plane
            </Link>
          </p>
        </div>
        <CommandBar />
      </div>
      <UniverseView initial={universe} />
    </div>
  );
}
