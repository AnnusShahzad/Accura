"use client";

import { useEffect, type ReactNode } from "react";
import { useAuthStore } from "@/stores/auth-store";
import { userApi, getAccessToken } from "@/lib/api-client";

export function AuthProvider({ children }: { children: ReactNode }) {
  const { setUser, clearUser, setLoading } = useAuthStore();

  useEffect(() => {
    async function loadUser() {
      const token = getAccessToken();
      if (!token) {
        clearUser();
        return;
      }

      try {
        const res = await userApi.getMe();
        setUser(res.data.user, res.data.profile);
      } catch {
        clearUser();
      }
    }

    setLoading(true);
    loadUser();
  }, [setUser, clearUser, setLoading]);

  return <>{children}</>;
}
