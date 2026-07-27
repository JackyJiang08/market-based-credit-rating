/** The letter cell: letter + interval ONLY; the basis is a small icon-badge
 *  with a tooltip — never inline text jammed against the interval. */
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { enumLabel } from "@/lib/labels";
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
    const det = enumLabel(determination);
    return (
      <span className="text-zinc-400" aria-label="no letter">
        — <span className="text-[11px]">{det.label}</span>
      </span>
    );
  }
  const b = enumLabel(basis);
  return (
    <span className="inline-flex items-center gap-1.5">
      <Tooltip>
        <TooltipTrigger
          render={
            <span
              tabIndex={0}
              className="font-mono font-semibold tabular-nums text-zinc-100"
              data-testid="letter-with-interval"
            />
          }
        >
          {letterWithInterval(letter, lo, hi)}
        </TooltipTrigger>
        <TooltipContent className="max-w-xs text-xs">
          5–95% bootstrap interval{notches ? ` spanning ${notches} notches` : ""}
          {bootstrapNote ? ` — ${bootstrapNote}` : ""}. Parameter uncertainty only: a
          lower bound on total uncertainty.
        </TooltipContent>
      </Tooltip>
      {basis ? (
        <Tooltip>
          <TooltipTrigger
            render={
              <span
                tabIndex={0}
                aria-label={`derived conversion — basis: ${b.label}`}
                className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-zinc-600 text-[9px] font-semibold text-zinc-400"
              />
            }
          >
            ƒ
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-xs">
            Derived conversion — {b.label}. {b.definition}
            <span className="mt-1 block font-mono text-[10px] text-zinc-400">{b.code}</span>
          </TooltipContent>
        </Tooltip>
      ) : null}
    </span>
  );
}
