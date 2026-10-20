"use client";

import { useQuery } from "@tanstack/react-query";
import { apiKeysApi } from "@/lib/api-client";
import { AI_MODELS } from "@/lib/constants";
import { usePublicConfig } from "@/hooks/use-public-config";

export interface ModelOption {
  value: string;
  label: string;
  provider: string;
  usable: boolean;
}

/**
 * Models the user can pick, flagged by whether a key exists for their
 * provider: the server's own keys (public config) or the user's BYOK keys.
 * The server's default models are always listed, even if they aren't in
 * the built-in list (e.g. an OpenRouter model via the "custom" provider).
 */
export function useModels(extra: (string | undefined)[] = []) {
  const { data: config, isLoading: configLoading } = usePublicConfig();
  const { data: keys, isLoading: keysLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: async () => (await apiKeysApi.list()).data,
  });

  const usableProviders = new Set<string>([
    ...(config?.ai.available_providers ?? []),
    ...(keys ?? []).filter((k) => k.is_active).map((k) => k.provider),
  ]);
  const defaults = config?.ai;

  const providerOf = (model: string | undefined): string => {
    if (!model) return defaults?.default_provider ?? "openai";
    const known = AI_MODELS.find((m) => m.value === model);
    if (known) return known.provider;
    // Unknown ids are the server's defaults or a user's custom model
    return defaults?.default_provider ?? "openai";
  };

  // Until we know, don't flag anything as unusable
  const ready = !configLoading && !keysLoading && !!config;
  const isUsable = (model: string | undefined) => !ready || usableProviders.has(providerOf(model));

  const listed = new Set<string>(AI_MODELS.map((m) => m.value));
  const additions = [defaults?.default_generator_model, defaults?.default_evaluator_model, ...extra]
    .filter((m): m is string => !!m && !listed.has(m))
    .filter((m, i, arr) => arr.indexOf(m) === i);

  const models: ModelOption[] = [
    ...additions.map((m) => ({ value: m, label: m, provider: providerOf(m) })),
    ...AI_MODELS.map((m) => ({ value: m.value, label: m.label, provider: m.provider })),
  ].map((m) => ({ ...m, usable: isUsable(m.value) }));

  /** The user's preference if it can run here, else the server default. */
  const pick = (preferred: string | undefined, fallback: string | undefined) =>
    preferred && isUsable(preferred) ? preferred : fallback || preferred;

  return {
    models,
    ready,
    providerOf,
    isUsable,
    pick,
    defaults,
    searchAvailable: config?.search_enabled ?? true,
    anyUsable: !ready || models.some((m) => m.usable),
  };
}
