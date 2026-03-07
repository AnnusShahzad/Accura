"use client";

import { Button } from "@/components/ui/button";
import { Zap, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useAuthStore } from "@/stores/auth-store";

export function Hero() {
  const { isAuthenticated, isLoading } = useAuthStore();

  return (
    <section className="relative overflow-hidden py-24 sm:py-32">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <div className="mb-6 flex items-center justify-center gap-2">
            <Zap className="h-10 w-10 text-primary" />
            <span className="text-3xl font-bold">Accura</span>
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-6xl">
            AI Responses You Can
            <span className="text-primary"> Trust</span>
          </h1>
          <p className="mt-6 text-lg leading-8 text-muted-foreground">
            Accura uses multi-agent orchestration to generate, evaluate, and
            refine AI responses until they meet your quality threshold. Multiple
            models compete to give you the best answer.
          </p>
          <div className="mt-10 flex items-center justify-center gap-x-4">
            {!isLoading && isAuthenticated ? (
              <Button size="lg" asChild>
                <Link href="/chat">
                  Go to Dashboard
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            ) : (
              <>
                <Button size="lg" asChild>
                  <Link href="/register">
                    Get Started Free
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
                <Button variant="outline" size="lg" asChild>
                  <Link href="/login">Sign In</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
