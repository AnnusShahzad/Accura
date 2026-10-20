"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api-client";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Eye, EyeOff, Check, X } from "lucide-react";

export default function ResetPasswordClient() {
  const params = useSearchParams();
  const token = params.get("token");

  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">(
    token ? "idle" : "error"
  );
  const [errorMessage, setErrorMessage] = useState(
    token ? "" : "This reset link is missing its token. Request a new one."
  );

  // SAME password validation checks as register page
  const passwordChecks = [
    { label: "Greater than 8 characters", met: password.length > 8 },
    { label: "1 uppercase letter", met: /[A-Z]/.test(password) },
    { label: "1 lowercase letter", met: /[a-z]/.test(password) },
    { label: "1 number", met: /[0-9]/.test(password) },
    {
      label: "1 special character",
      met: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(password),
    },
  ];

  const isPasswordValid = passwordChecks.every((check) => check.met);

  const handleSubmit = async () => {
    if (!token || !password || !isPasswordValid) {
      setErrorMessage(token ? "Password requirements not met" : "This reset link is missing its token.");
      setStatus("error");
      return;
    }

    try {
      setStatus("loading");
      await authApi.resetPassword(token, password);
      setStatus("success");
    } catch (e) {
      setErrorMessage(
        e instanceof Error ? e.message : "This reset link is invalid or has expired."
      );
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

            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                placeholder="Enter new password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 text-muted-foreground hover:text-foreground"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>

            {/* Password Strength Indicators */}
            {password.length > 0 && (
              <div className="mt-2 space-y-1">
                {passwordChecks.map((check) => (
                  <div
                    key={check.label}
                    className="flex items-center gap-2 text-xs"
                  >
                    {check.met ? (
                      <Check className="h-3 w-3 text-green-500" />
                    ) : (
                      <X className="h-3 w-3 text-muted-foreground" />
                    )}

                    <span
                      className={
                        check.met
                          ? "text-green-500"
                          : "text-muted-foreground"
                      }
                    >
                      {check.label}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <Button
              className="w-full"
              onClick={handleSubmit}
              disabled={!isPasswordValid || status === "loading"}
            >
              {status === "loading" ? "Resetting..." : "Reset Password"}
            </Button>

            {status === "error" && (
              <div className="space-y-1 text-center text-sm">
                <p className="text-destructive">{errorMessage}</p>
                <Link
                  href="/forgot-password"
                  className="inline-block py-1 text-primary underline-offset-4 hover:underline"
                >
                  Request a new reset link
                </Link>
              </div>
            )}
          </>
        ) : (
          <>
            <p className="text-green-800 dark:text-green-400 text-center font-semibold">
              Password reset successful
            </p>

            <Button className="w-full" asChild>
              <Link href="/login">Go to Login</Link>
            </Button>
          </>
        )}
      </div>
    </div>
  );
}