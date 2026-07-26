/** The letter, never bare: interval attached + derived-conversion badge. */
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { letterWithInterval } from "@/lib/format";

export function RatingCell({
  letter,
  lo,
  hi,
  notches,
  basis,
  determination,
  bootstrapNote,
}: {
  letter: string | null;
  lo: string | null;
  hi: string | null;
  notches?: number | null;
  basis?: string | null;
  determination?: string | null;
  bootstrapNote?: string;
}) {
  if (!letter) {
    return (
      <span className="text-zinc-500" aria-label="no letter">
        — <span className="text-[11px]">({determination ?? "NOT_RATED"})</span>
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <Tooltip>
        <TooltipTrigger
          render={
            <span
              tabIndex={0}
              className="font-mono tabular-nums font-semibold text-zinc-100"
              data-testid="letter-with-interval"
            />
          }
        >
          {letterWithInterval(letter, lo, hi)}
        </TooltipTrigger>
        <TooltipContent className="max-w-xs text-xs">
          5–95% bootstrap interval{notches ? ` spanning ${notches} notches` : ""}
          {bootstrapNote ? ` — ${bootstrapNote}` : ""}. Parameter uncertainty
          only: a lower bound on total uncertainty.
        </TooltipContent>
      </Tooltip>
      <Badge
        variant="outline"
        className="border-zinc-600 bg-zinc-800/80 text-[10px] uppercase tracking-wide text-zinc-400"
      >
        derived conversion{basis ? ` · ${basis}` : ""}
      </Badge>
    </span>
  );
}
