"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api-client";
import { Button } from "@/components/ui/button";

export default function EmailChangeClient() {
  const params = useSearchParams();
  const token = params.get("token");

  const [status, setStatus] = useState<"loading" | "success" | "error">(
    "loading"
  );

  useEffect(() => {

    console.log("TOKEN:", token)
    if (!token) {
      setStatus("error");
      return;
    }

    async function verify() {
      try {
        await authApi.verifyEmailChange(token as string);
        setStatus("success");
      } catch {
        setStatus("error");
      }
    }

    verify();
  }, [token]);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="space-y-4 text-center">
        {status === "loading" && (
          <p className="text-muted-foreground">Verifying your new email...</p>
        )}

        {status === "success" && (
          <>
            <p className="text-green-600 font-semibold">
              Email updated successfully
            </p>
            <Button onClick={() => (window.location.href = "/settings/profile")}>
              Go to Profile
            </Button>
          </>
        )}

        {status === "error" && (
          <p className="text-red-600 font-semibold">
            Invalid or expired verification link
          </p>
        )}
      </div>
    </div>
  );
}