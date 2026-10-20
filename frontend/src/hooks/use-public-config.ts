"use client";

import { useQuery } from "@tanstack/react-query";
import { publicApi } from "@/lib/api-client";

/** Server capabilities (registration, guests, providers). Rarely changes. */
export function usePublicConfig() {
  return useQuery({
    queryKey: ["public-config"],
    queryFn: async () => (await publicApi.getConfig()).data,
    staleTime: 5 * 60 * 1000,
    retry: 3,
    retryDelay: (attempt) => Math.min(2000 * 2 ** attempt, 15000),
  });
}
