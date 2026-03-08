"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { authApi } from "@/lib/api-client";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Eye, EyeOff, Check, X } from "lucide-react";

export default function ResetPasswordClient() {
  const params = useSearchParams();
  const token = params.get("token");

  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [status, setStatus] = useState<"idle" | "loading" | "success" | "error">(
    "idle"
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

            <div className="relative">
              <Input
                type={showPassword ? "text" : "password"}
                placeholder="Enter new password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />

              <button
                type="button"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                onClick={() => setShowPassword(!showPassword)}
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
              <p className="text-red-500 text-sm text-center">
                Invalid token or password requirements not met
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