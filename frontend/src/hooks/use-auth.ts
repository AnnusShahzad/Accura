"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { authApi, userApi } from "@/lib/api-client";
import type { LoginRequest, RegisterRequest } from "@/types";
import { toast } from "sonner";

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, profile, isAuthenticated, isLoading, setUser, clearUser } =
    useAuthStore();

  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) => authApi.login(data),
    onSuccess: async () => {
      const res = await userApi.getMe();
      setUser(res.data.user, res.data.profile);
      queryClient.invalidateQueries();
      toast.success("Welcome back!");
      router.push("/chat");
    },
    onError: (error: Error, variables) => {
      const message = error.message || "Failed to log in";
      toast.error(message);

      // If the error is about email verification, redirect to OTP page
      if (message.toLowerCase().includes("verify your email") || message.toLowerCase().includes("unverified")) {
        router.push(`/verify-otp?email=${encodeURIComponent(variables.email)}`);
      }
    },
  });

  const registerMutation = useMutation({

    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: (res, variables) => {
      if (res.data.already_exists_unverified) {
        toast.error(
          "Account already exists but is not verified. A new verification code has been sent to your email."
        );
      } else {
        toast.success(
          "Account created! Please check your email for the verification code."
        );
      }
      router.push(`/verify-otp?email=${encodeURIComponent(variables.email)}`);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to create account");
    },
  });

  const forgotPasswordMutation = useMutation({
    mutationFn: (email: string) => authApi.forgotPassword(email),
    onSuccess: () => {
      toast.success("If the email exists, a reset link has been sent.");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to send reset email");
    },
  });

  const resetPasswordMutation = useMutation({
    mutationFn: ({
      token,
      new_password,
    }: {
      token: string;
      new_password: string;
    }) => authApi.resetPassword(token, new_password),
    onSuccess: () => {
      toast.success("Password reset successful");
      router.push("/login");
    }
  });

  const guestMutation = useMutation({
    mutationFn: () => authApi.guest(),
    onSuccess: async () => {
      const res = await userApi.getMe();
      setUser(res.data.user, res.data.profile);
      queryClient.invalidateQueries();
      toast.success("Guest session started");
      router.push("/chat");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Could not start a guest session");
    },
  });

  const logout = () => {
    // A guest has no password: once the tokens are gone, so is the account
    if (
      user?.is_guest &&
      typeof window !== "undefined" &&
      !window.confirm("Log out of this guest session? You won't be able to come back to it.")
    ) {
      return;
    }
    authApi.logout();
    clearUser();
    queryClient.clear();
    router.push("/login");
  };

  return {
    user,
    profile,
    isAuthenticated,
    isLoading,
    login: loginMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    logout,
    isLoggingIn: loginMutation.isPending,
    isRegistering: registerMutation.isPending,
    loginAsGuest: guestMutation.mutateAsync,
    isStartingGuest: guestMutation.isPending,
    forgotPassword: forgotPasswordMutation.mutateAsync,
    resetPassword: resetPasswordMutation.mutateAsync,
    isRequestingPasswordReset: forgotPasswordMutation.isPending,
    isResettingPassword: resetPasswordMutation.isPending,
  };
}
