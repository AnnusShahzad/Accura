"use client";

import { ThemeToggle } from "@/components/layout/theme-toggle";
import { UserNav } from "@/components/layout/user-nav";
import { SidebarTrigger } from "@/components/ui/sidebar";
import { Separator } from "@/components/ui/separator";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";

export function Header() {
  const { profile } = useAuth();

  return (
    <header className="flex h-14 items-center gap-4 border-b bg-background px-4 lg:px-6">
      <SidebarTrigger />
      <Separator orientation="vertical" className="h-6" />

      <div className="flex-1">
        <h1 className="font-semibold bg-gradient-to-r from-primary to-primary/60 bg-clip-text text-transparent">
          Welcome Back, {profile?.first_name} {profile?.last_name}!
        </h1>
      </div>
      <Button variant="ghost" size="icon" asChild>
        <Link href="/notifications">
          <Bell className="h-4 w-4" />
        </Link>
      </Button>

      <ThemeToggle />
      <UserNav />
    </header>
  );
}
