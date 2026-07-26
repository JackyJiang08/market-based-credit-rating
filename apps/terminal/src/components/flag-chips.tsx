/** Flags are first-class chips, never footnotes. */
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const TONE: Record<string, string> = {
  WEAKLY_IDENTIFIED: "border-amber-500/50 bg-amber-500/10 text-amber-300",
  DEFECTIVE_DRIFT: "border-rose-500/50 bg-rose-500/10 text-rose-300",
  AT_FLOOR: "border-sky-500/50 bg-sky-500/10 text-sky-300",
  AT_SCALE_TOP: "border-sky-500/50 bg-sky-500/10 text-sky-300",
};

export function FlagChip({ code, text }: { code: string; text?: string }) {
  const tone =
    TONE[code] ?? "border-fuchsia-500/50 bg-fuchsia-500/10 text-fuchsia-300";
  const badge = (
    <Badge
      variant="outline"
      className={`font-mono text-[11px] tracking-tight ${tone}`}
      tabIndex={0}
      aria-label={text ? `${code}: ${text}` : code}
    >
      {code}
    </Badge>
  );
  if (!text) return badge;
  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <Badge
            variant="outline"
            className={`font-mono text-[11px] tracking-tight ${tone}`}
            tabIndex={0}
            aria-label={`${code}: ${text}`}
          />
        }
      >
        {code}
      </TooltipTrigger>
      <TooltipContent className="max-w-xs text-xs">{text}</TooltipContent>
    </Tooltip>
  );
}
