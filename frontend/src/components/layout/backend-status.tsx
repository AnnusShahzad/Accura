"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, RefreshCw, ServerCrash } from "lucide-react";
import { publicApi } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

// Free hosting tiers put the API to sleep when idle; the first request then
// takes up to a minute. Only show anything if the API is actually slow.
const SHOW_AFTER_MS = 2500;
const RETRY_EVERY_MS = 3000;
const GIVE_UP_AFTER_MS = 120_000;

export const API_UNREACHABLE_EVENT = "accura:api-unreachable";

type Status = "ok" | "waking" | "down";

export function BackendStatus() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<Status>("ok");
  const checking = useRef(false);

  const check = useCallback(async () => {
    if (checking.current) return;
    checking.current = true;
    const started = Date.now();
    const banner = setTimeout(() => setStatus("waking"), SHOW_AFTER_MS);

    try {
      while (Date.now() - started < GIVE_UP_AFTER_MS) {
        try {
          const res = await publicApi.health();
          if (res.ok) {
            clearTimeout(banner);
            setStatus("ok");
            // Anything that failed while the server slept can load now
            if (Date.now() - started > SHOW_AFTER_MS) {
              queryClient.invalidateQueries();
            }
            return;
          }
        } catch {
          // network error: the server isn't up yet
        }
        setStatus("waking");
        await new Promise((r) => setTimeout(r, RETRY_EVERY_MS));
      }
      clearTimeout(banner);
      setStatus("down");
    } finally {
      checking.current = false;
    }
  }, [queryClient]);

  useEffect(() => {
    // Defer so the check isn't a synchronous state update in the effect
    const t = setTimeout(check, 0);
    const onUnreachable = () => check();
    window.addEventListener(API_UNREACHABLE_EVENT, onUnreachable);
    return () => {
      clearTimeout(t);
      window.removeEventListener(API_UNREACHABLE_EVENT, onUnreachable);
    };
  }, [check]);

  if (status === "ok") return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-x-0 top-0 z-[60] flex justify-center px-4 pt-3 pointer-events-none"
    >
      <div className="pointer-events-auto flex max-w-xl items-center gap-3 rounded-lg border bg-background/95 px-4 py-3 text-sm shadow-lg backdrop-blur">
        {status === "waking" ? (
          <>
            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" />
            <p>
              <span className="font-medium">Starting the server…</span>{" "}
              <span className="text-muted-foreground">
                It sleeps when idle on free hosting and can take up to a minute to wake.
              </span>
            </p>
          </>
        ) : (
          <>
            <ServerCrash className="h-4 w-4 shrink-0 text-destructive" />
            <p className="text-muted-foreground">
              <span className="font-medium text-foreground">Can&apos;t reach the server.</span>{" "}
              Check your connection or try again shortly.
            </p>
            <Button size="sm" variant="outline" className="shrink-0" onClick={() => check()}>
              <RefreshCw className="mr-1 h-3 w-3" />
              Retry
            </Button>
          </>
        )}
      </div>
    </div>
  );
}
