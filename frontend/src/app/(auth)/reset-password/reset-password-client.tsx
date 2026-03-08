"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api-client";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function ResetPasswordClient() {
  const params = useSearchParams();
  const token = params.get("token");

  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">(
    "idle"
  );

  const handleSubmit = async () => {
    if (!token || !password) {
      setStatus("error");
      return;
    }

    try {
      setStatus("loading");

      await authApi.resetPassword(token, password);

      setStatus("success");
    } catch {
      setStatus("error");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="space-y-4 w-[350px]">
        {status !== "success" ? (
          <>
            <h2 className="text-xl font-semibold text-center">
              Reset Password
            </h2>

            <Input
              type="password"
              placeholder="Enter new password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />

            <Button className="w-full" onClick={handleSubmit}>
              {status === "loading" ? "Resetting..." : "Reset Password"}
            </Button>

            {status === "error" && (
              <p className="text-red-500 text-sm text-center">
                Invalid or expired token
              </p>
            )}
          </>
        ) : (
          <>
            <p className="text-green-600 text-center font-semibold">
              Password reset successful
            </p>

            <Button
              className="w-full"
              onClick={() => (window.location.href = "/login")}
            >
              Go to Login
            </Button>
          </>
        )}
      </div>
    </div>
  );
}