"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Info } from "lucide-react";

const MESSAGES: Record<string, string> = {
  "session-ended": "Your session ended. Please sign in again, or start a new guest session.",
};

function Notice() {
  const reason = useSearchParams().get("reason");
  const message = reason ? MESSAGES[reason] : undefined;
  if (!message) return null;
  return (
    <div className="flex items-start gap-2 rounded-md border bg-muted/50 px-3 py-2 text-sm">
      <Info className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
      <p>{message}</p>
    </div>
  );
}

/** Explains why the user landed on the login page, if we know. */
export function SessionNotice() {
  return (
    <Suspense fallback={null}>
      <Notice />
    </Suspense>
  );
}
