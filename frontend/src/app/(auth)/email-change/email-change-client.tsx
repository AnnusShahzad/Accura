"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { authApi, userApi } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function EmailChangeClient() {
  const params = useSearchParams();
  const token = params.get("token");
  const { isAuthenticated, setUser } = useAuthStore();
  const started = useRef(false);

  const [status, setStatus] = useState<"loading" | "success" | "error">(
    token ? "loading" : "error"
  );
  const [message, setMessage] = useState(
    token ? "" : "This link is missing its verification token."
  );
  const [newEmail, setNewEmail] = useState("");

  useEffect(() => {
    // The token is single-purpose; don't submit it twice in StrictMode
    if (!token || started.current) return;
    started.current = true;

    authApi
      .verifyEmailChange(token)
      .then(async (res) => {
        setNewEmail(res.data.email);
        setStatus("success");
        if (isAuthenticated) {
          const me = await userApi.getMe().catch(() => null);
          if (me) setUser(me.data.user, me.data.profile);
        }
      })
      .catch((e: Error) => {
        setMessage(e.message || "Invalid or expired verification link");
        setStatus("error");
      });
  }, [token, isAuthenticated, setUser]);

  return (
    <Card className="text-center">
      <CardHeader>
        <CardTitle className="text-2xl font-bold">Confirm New Email</CardTitle>
        <CardDescription>
          {status === "loading" && "Verifying your new email address..."}
          {status === "success" && "Your email address has been updated."}
          {status === "error" && "We couldn't update your email address."}
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4">
        {status === "loading" && (
          <Loader2 className="h-12 w-12 animate-spin text-muted-foreground" />
        )}
        {status === "success" && (
          <>
            <CheckCircle2 className="h-12 w-12 text-green-500" />
            {newEmail && (
              <p className="text-sm text-muted-foreground">
                You can now sign in with <strong className="text-foreground">{newEmail}</strong>.
              </p>
            )}
            <Button asChild>
              <Link href={isAuthenticated ? "/settings/profile" : "/login"}>
                {isAuthenticated ? "Go to Profile" : "Continue to Login"}
              </Link>
            </Button>
          </>
        )}
        {status === "error" && (
          <>
            <XCircle className="h-12 w-12 text-destructive" />
            <p className="text-sm text-muted-foreground">{message}</p>
            <Button asChild variant="outline">
              <Link href={isAuthenticated ? "/settings/profile" : "/login"}>
                {isAuthenticated ? "Back to Profile" : "Back to Login"}
              </Link>
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
