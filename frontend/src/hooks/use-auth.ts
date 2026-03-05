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
    onError: (error: Error) => {
      toast.error(error.message || "Failed to log in");
    },
  });

  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) => authApi.register(data),
    onSuccess: () => {
      toast.success("Account created! Please check your email to verify.");
      router.push("/login");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to register");
    },
  });

  const logout = () => {
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
  };
}
