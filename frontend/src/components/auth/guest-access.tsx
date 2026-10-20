"use client";

import { Loader2, UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/use-auth";
import { usePublicConfig } from "@/hooks/use-public-config";

/** "Continue as guest" button with what a guest session means. */
export function GuestAccess({ variant = "outline" }: { variant?: "outline" | "default" }) {
  const { data: config } = usePublicConfig();
  const { loginAsGuest, isStartingGuest } = useAuth();

  if (!config?.guest.enabled) return null;
  const hours = config.guest.ttl_hours;

  return (
    <div className="space-y-2">
      <Button
        type="button"
        variant={variant}
        className="w-full"
        disabled={isStartingGuest}
        onClick={() => loginAsGuest().catch(() => {})}
      >
        {isStartingGuest ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <UserRound className="mr-2 h-4 w-4" />
        )}
        Continue as guest
      </Button>
      <p className="text-center text-xs text-muted-foreground">
        No sign-up needed. A guest session and everything in it is deleted after{" "}
        {hours === 1 ? "1 hour" : `${hours} hours`}.
      </p>
    </div>
  );
}
