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
export const AI_MODELS = [
  { value: "gpt-5.2", label: "GPT 5.2", provider: "openai" },
  { value: "gpt-5.1", label: "GPT 5.1", provider: "openai" },
  { value: "deepseek-v3", label: "DeepSeek V3", provider: "deepseek" },
  { value: "deepseek-ai/deepseek-v3.2", label: "DeepSeek V3.2", provider: "deepseek" },
  { value: "minimaxai/minimax-m2.5", label: "Minimax M2.5", provider: "minimax" },
  { value: "openai/gpt-oss-120b", label: "ChatGPT 120B OSS", provider: "openai" }
] as const;

// ─── AI Providers ───
export const AI_PROVIDERS = [
  { value: "openai", label: "OpenAI" },
  { value: "deepseek", label: "DeepSeek" },
  { value: "anthropic", label: "Anthropic" },
  { value: "custom", label: "Custom" },
] as const;

// ─── MCP Transport Options ───
export const MCP_TRANSPORTS = [
  { value: "sse", label: "SSE (Server-Sent Events)" },
  { value: "stdio", label: "Stdio" },
  { value: "http", label: "HTTP" },
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
  active: "Active",
  completed: "Completed",
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
