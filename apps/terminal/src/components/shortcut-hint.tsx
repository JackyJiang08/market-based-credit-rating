"use client";

import { useShortcutHint } from "@/lib/use-shortcut-hint";

/** Inline <kbd> with the platform-correct search shortcut. */
export function ShortcutHint({ className }: { className?: string }) {
  return <kbd className={className}>{useShortcutHint()}</kbd>;
}
