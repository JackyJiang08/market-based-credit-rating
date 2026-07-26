import { CommandBar } from "@/components/command-bar";
import { UniverseTable } from "@/components/universe-table";

export default function Home() {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-zinc-50">
            creditrating <span className="text-sky-300">terminal</span>
          </h1>
          <p className="text-xs text-zinc-500">
            150-name universe · RiskScore first · press <kbd className="font-mono">⌘K</kbd>{" "}
            or <kbd className="font-mono">/</kbd> to jump to a company
          </p>
        </div>
        <CommandBar />
      </div>
      <UniverseTable />
    </div>
  );
}
