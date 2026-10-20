"use client";

import { Clock } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";

export function GuestBanner() {
  const { user } = useAuthStore();
  if (!user?.is_guest) return null;

  const expires = user.expires_at ? new Date(user.expires_at) : null;
  const when = expires
    ? expires.toLocaleString(undefined, {
        weekday: "short",
        hour: "numeric",
        minute: "2-digit",
      })
    : null;

  return (
    <div className="flex items-center gap-2 border-b bg-amber-50 px-4 py-2 text-sm text-amber-900 dark:bg-amber-950/40 dark:text-amber-200 lg:px-6">
      <Clock className="h-4 w-4 shrink-0" />
      <p>
        <span className="font-medium">Guest session.</span>{" "}
        {when
          ? `This account and everything in it will be deleted ${when}.`
          : "This account and everything in it will be deleted automatically."}
      </p>
    </div>
  );
}
