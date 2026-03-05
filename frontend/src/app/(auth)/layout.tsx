import { Zap } from "lucide-react";
import Link from "next/link";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      {/* Left branding panel */}
      <div className="hidden w-1/2 flex-col justify-between bg-primary p-10 text-primary-foreground lg:flex">
        <Link href="/" className="flex items-center gap-2">
          <Zap className="h-8 w-8" />
          <span className="text-2xl font-bold">Accura</span>
        </Link>
        <div className="space-y-4">
          <h1 className="text-4xl font-bold leading-tight">
            Intelligent Multi-Agent
            <br />
            Response Platform
          </h1>
          <p className="text-lg text-primary-foreground/80">
            Generate, evaluate, and refine AI responses using multi-agent
            orchestration with customizable quality thresholds.
          </p>
        </div>
        <p className="text-sm text-primary-foreground/60">
          &copy; {new Date().getFullYear()} Accura AI. All rights reserved.
        </p>
      </div>

      {/* Right form panel */}
      <div className="flex w-full items-center justify-center px-4 lg:w-1/2">
        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
