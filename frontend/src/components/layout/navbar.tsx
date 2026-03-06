"use client";

import { Zap } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/hooks/use-auth";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { UserNav } from "@/components/layout/user-nav";

export function Navbar() {
  const { user } = useAuth();

  return (
    <nav className="sticky top-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-md">
      <div className="mx-auto relative flex max-w-7xl items-center justify-between px-6 h-16">

        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group z-10">
          <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
            <Zap className="h-4 w-4 text-primary" />
          </div>
          <span className="text-base font-semibold tracking-tight">Accura</span>
        </Link>

        {/* Center Nav Links — absolutely centered */}
        <div className="hidden md:flex items-center gap-1 absolute left-1/2 -translate-x-1/2">
          {[
            { href: "#features", label: "Features" },
            { href: "#pricing", label: "Pricing" },
            { href: "#contact", label: "Contact" },
          ].map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="px-3 py-1.5 text-sm text-muted-foreground rounded-md hover:text-foreground hover:bg-accent transition-all duration-150"
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Right: Theme + Auth */}
        <div className="flex items-center gap-2 z-10">
          <ThemeToggle />
          <div className="pl-2 border-l border-border flex items-center gap-2">
            {!user ? (
              <>
                <Link
                  href="/login"
                  className="px-3 py-1.5 text-sm text-muted-foreground rounded-md hover:text-foreground hover:bg-accent transition-all duration-150"
                >
                  Sign In
                </Link>
                <Link
                  href="/register"
                  className="px-4 py-1.5 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
                >
                  Get Started
                </Link>
              </>
            ) : (
              <UserNav />
            )}
          </div>
        </div>

      </div>
    </nav>
  );
}