"use client";

/** Platform-aware label for the search shortcut: "⌘K" on Apple platforms,
 *  "Ctrl K" elsewhere. SSR renders the Apple form (the static HTML has to
 *  pick one); the effect corrects it after hydration, before the hint
 *  matters for interaction. */
import { useEffect, useState } from "react";

export function useShortcutHint(): string {
  const [hint, setHint] = useState("⌘K");
  useEffect(() => {
    const uaData = (navigator as { userAgentData?: { platform?: string } }).userAgentData;
    const apple = /Mac|iPhone|iPad|iPod/.test(
      uaData?.platform ?? navigator.platform ?? "",
    );
    if (!apple) setHint("Ctrl K");
  }, []);
  return hint;
}
