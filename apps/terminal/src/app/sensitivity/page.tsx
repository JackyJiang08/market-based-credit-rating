import { CommandBar } from "@/components/command-bar";
import { Sensitivity } from "@/components/sensitivity";
import Link from "next/link";
import { Suspense } from "react";

export const metadata = { title: "sensitivity — creditrating terminal" };

export default function SensitivityPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-50">Sensitivity playground</h1>
          <p className="text-xs text-zinc-400">
            published formulas, computed in your browser · the trace draws on the µ–CCM
            plane ·{" "}
            <Link href="/" className="underline underline-offset-2 hover:text-zinc-300">
              ← universe
            </Link>
          </p>
        </div>
        <CommandBar />
      </div>
      <Suspense>
        <Sensitivity />
      </Suspense>
    </div>
  );
}
