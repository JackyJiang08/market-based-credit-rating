import { CommandBar } from "@/components/command-bar";
import { PlaneView } from "@/components/plane-view";
import Link from "next/link";
import { Suspense } from "react";

export default function PlanePage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-50">µ–CCM plane</h1>
          <p className="text-xs text-zinc-500">
            iso-rating lines with slope Q = 0.6259 (published Table-8 scale) ·{" "}
            <Link href="/" className="underline underline-offset-2 hover:text-zinc-300">
              ← universe
            </Link>
          </p>
        </div>
        <CommandBar />
      </div>
      <Suspense>
        <PlaneView />
      </Suspense>
    </div>
  );
}
