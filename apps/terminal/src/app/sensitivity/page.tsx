import { Sensitivity } from "@/components/sensitivity";

export const metadata = { title: "Sensitivity — Credit Rating Terminal" };

export default function SensitivityPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-50">Sensitivity playground</h1>
          <p className="text-xs text-zinc-400">
            published formulas, computed in your browser · the trace draws on the µ–CCM
            plane
          </p>
        </div>
      </div>
      <Sensitivity />
    </div>
  );
}
