import { CommandBar } from "@/components/command-bar";
import { UniverseView } from "@/components/universe-view";
import Link from "next/link";
import { Suspense } from "react";

export default function Home() {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-50">
            creditrating <span className="text-sky-300">terminal</span>
          </h1>
          <p className="text-xs text-zinc-500">
            150-name universe · RiskScore first · <kbd className="font-mono">⌘K</kbd> or{" "}
            <kbd className="font-mono">/</kbd> to jump ·{" "}
            <Link href="/plane/" className="underline underline-offset-2 hover:text-zinc-300">
              µ–CCM plane
            </Link>
          </p>
        </div>
        <CommandBar />
      </div>
      <Suspense>
        <UniverseView />
      </Suspense>
    </div>
  );
}
