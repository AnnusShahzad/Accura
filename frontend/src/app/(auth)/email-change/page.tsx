import { Suspense } from "react";
import EmailChangeClient from "./email-change-client";

export default function Page() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <p className="text-muted-foreground">Loading...</p>
        </div>
      }
    >
      <EmailChangeClient />
    </Suspense>
  );
}