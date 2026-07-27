/** Flags are chips: humanized label, tone colour + label (never colour
 *  alone), tooltip with the definition AND the machine constant. Rows cap
 *  visible chips and overflow into "+n". */
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { TONE_CLASSES, enumLabel } from "@/lib/labels";

export function FlagChip({ code, extra }: { code: string; extra?: string }) {
  const e = enumLabel(code);
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Badge
            variant="outline"
            className={`whitespace-nowrap text-[11px] ${TONE_CLASSES[e.tone]}`}
            tabIndex={0}
            aria-label={`${e.label}: ${e.definition}`}
          />
        }
      >
        {e.label}
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">
        {extra ?? e.definition}
        <span className="mt-1 block font-mono text-[10px] text-zinc-400">{e.code}</span>
      </TooltipContent>
    </Tooltip>
  );
}

export function ChipRow({ codes, max = 2 }: { codes: string[]; max?: number }) {
  const shown = codes.slice(0, max);
  const rest = codes.slice(max);
  return (
    <span className="inline-flex flex-wrap items-center gap-1.5">
      {shown.map((c) => (
        <FlagChip key={c} code={c} />
      ))}
      {rest.length ? (
        <Tooltip>
          <TooltipTrigger
            render={
              <Badge
                variant="outline"
                className="border-zinc-600 bg-zinc-800/70 text-[11px] text-zinc-300"
                tabIndex={0}
                aria-label={`${rest.length} more flags`}
              />
            }
          >
            +{rest.length}
          </TooltipTrigger>
          <TooltipContent className="max-w-xs text-xs">
            {rest.map((c) => (
              <div key={c}>
                {enumLabel(c).label}
                <span className="ml-1 font-mono text-[10px] text-zinc-400">{c}</span>
              </div>
            ))}
          </TooltipContent>
        </Tooltip>
      ) : null}
    </span>
  );
}
