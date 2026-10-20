"use client";

import { ThemeToggle } from "@/components/layout/theme-toggle";
import { UserNav } from "@/components/layout/user-nav";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/hooks/use-auth";
import { notificationsApi } from "@/lib/api-client";

export function Header() {
  const { user, profile } = useAuth();
  const displayName =
    [profile?.first_name, profile?.last_name].filter(Boolean).join(" ") || user?.username;

  const { data: unread } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: async () => (await notificationsApi.unreadCount()).data.count,
    refetchInterval: 30_000,
    enabled: !!user,
  });

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-background px-4 lg:px-6">
      <SidebarTrigger />
      <Separator orientation="vertical" className="h-6" />

      <div className="flex-1 min-w-0">
        <h1 className="truncate font-semibold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
          {displayName ? `Welcome back, ${displayName}!` : "Welcome back!"}
        </h1>
      </div>
      <Button variant="ghost" size="icon" className="relative" asChild>
        <Link href="/notifications" aria-label={unread ? `Notifications (${unread} unread)` : "Notifications"}>
          <Bell className="h-4 w-4" />
          {!!unread && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-medium text-primary-foreground">
              {unread > 99 ? "99+" : unread}
            </span>
          )}
        </Link>
      </Button>

      <ThemeToggle />
      <UserNav />
    </header>
  );
}
