// ─── API Base ───
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// ─── Subscription Tiers ───
export const TIERS = {
  basic: "Basic",
  pro: "Pro",
  business: "Business",
} as const;

// ─── AI Models ───
// `provider` selects which API key is used (platform key or your own
// BYOK key for that provider). Any OpenAI-compatible model can also be
// used through the "custom" provider with your own base URL.
export const AI_MODELS = [
  { value: "gpt-5.2", label: "GPT-5.2", provider: "openai" },
  { value: "gpt-5.1", label: "GPT-5.1", provider: "openai" },
  { value: "gpt-5-mini", label: "GPT-5 mini", provider: "openai" },
  { value: "gpt-4o", label: "GPT-4o", provider: "openai" },
  { value: "deepseek-chat", label: "DeepSeek V3 (chat)", provider: "deepseek" },
  { value: "deepseek-reasoner", label: "DeepSeek R1 (reasoner)", provider: "deepseek" },
  { value: "claude-opus-5-5", label: "Claude Opus 5.5", provider: "anthropic" },
  { value: "claude-sonnet-5-5", label: "Claude Sonnet 5.5", provider: "anthropic" },
  { value: "claude-haiku-5-5", label: "Claude Haiku 5.5", provider: "anthropic" },
  { value: "gemini-2.5-pro", label: "Gemini 2.5 Pro", provider: "google" },
  { value: "gemini-2.5-flash", label: "Gemini 2.5 Flash", provider: "google" },
  { value: "openai/gpt-oss-120b", label: "GPT-OSS 120B (custom endpoint)", provider: "custom" },
  { value: "openai/gpt-oss-20b", label: "GPT-OSS 20B (custom endpoint)", provider: "custom" },
] as const;

export function providerForModel(model: string | undefined): string {
  return AI_MODELS.find((m) => m.value === model)?.provider ?? "openai";
}

// ─── AI Providers ───
export const AI_PROVIDERS = [
  { value: "openai", label: "OpenAI" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "anthropic", label: "Anthropic" },
  { value: "google", label: "Google AI" },
  { value: "custom", label: "Custom (OpenAI-compatible)" },
] as const;

// ─── MCP Transport Options ───
export const MCP_TRANSPORTS = [
  { value: "http", label: "Streamable HTTP" },
  { value: "sse", label: "SSE (legacy)" },
] as const;

// ─── Notification Channels ───
export const NOTIFICATION_CHANNELS = [
  { key: "notify_in_app", label: "In-App" },
  { key: "notify_email", label: "Email" },
  { key: "notify_slack", label: "Slack Webhook" },
  { key: "notify_teams", label: "Teams Webhook" },
] as const;

// ─── Billing Cycles ───
export const BILLING_CYCLES = [
  { value: "monthly", label: "Monthly" },
  { value: "yearly", label: "Yearly" },
] as const;

// ─── Conversation Statuses ───
export const CONVERSATION_STATUSES = {
  active: "Generating",
  completed: "Completed",
  failed: "Failed",
  archived: "Archived",
} as const;

// ─── System Prompt Roles ───
export const SYSTEM_PROMPT_ROLES = [
  { value: "generator", label: "Generator" },
  { value: "evaluator", label: "Evaluator" },
  { value: "reprompt", label: "Re-Prompt" },
] as const;

// ─── Domain Rule Types ───
export const DOMAIN_RULE_TYPES = [
  { value: "whitelist", label: "Whitelist" },
  { value: "blacklist", label: "Blacklist" },
] as const;

// ─── Defaults ───
export const DEFAULTS = {
  globalThreshold: 75,
  maxIterations: 5,
  timeoutSeconds: 120,
  preferredGeneratorModel: "gpt-5.2",
  preferredEvaluatorModel: "gpt-5.1",
  preferredCriticModel: "gpt-5.1",
} as const;
