// ─── Auth Types ───
export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  first_name?: string;
  last_name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface VerifyEmailRequest {
  token: string;
}

export interface ChangePasswordRequest {
  old_password: string;
  new_password: string;
}

// ─── User Types ───
export interface User {
  id: string;
  email: string;
  username: string;
  tier: "basic" | "pro" | "business";
  is_active: boolean;
  is_verified: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface UserProfile {
  id: string;
  user_id: string;
  first_name: string;
  last_name: string;
  avatar_url: string;
  phone: string;
  company: string;
  timezone: string;
}

export interface ProfileUpdateRequest {
  first_name?: string;
  last_name?: string;
  phone?: string;
  company?: string;
  timezone?: string;
  avatar_url?: string;
}

export interface UserWithProfile {
  user: User;
  profile: UserProfile;
}

// ─── Chat Types ─── 
export interface CreateConversationRequest {
  title?: string;
  prompt: string;
  generator_model?: string;
  generator_provider?: string;
  evaluator_model?: string;
  evaluator_provider?: string;
  search_enabled?: boolean;
  is_temporary?: boolean;
  threshold?: number;
  max_iterations?: number;
  timeout_seconds?: number;
}

export interface RenameConversationRequest {
  title: string;
}

export interface AddAgentRequest {
  provider: string;
  model: string;
  role?: string;
}

export interface ChatAgent {
  id: string;
  conversation_id: string;
  role: "generator" | "evaluator";
  provider: string;
  model: string;
  is_active: boolean;
  added_mid_chat: boolean;
  created_at: string;
}

export interface Iteration {
  id: string;
  iteration_number: number;
  agent_id: string;
  rephrased_prompt: string;
  response: string;
  score: number;
  evaluation_reasoning: string;
  tokens_input: number;
  tokens_output: number;
  timed_out: boolean;
  duration_ms: number;
  created_at: string;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system" | "evaluator";
  content: string;
  score?: number | null;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface FollowUpMessageRequest {
  prompt: string;
  search_enabled?: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  prompt: string;
  status: "active" | "completed" | "archived";
  best_response: string;
  best_score: number;
  tokens_input: number;
  tokens_output: number;
  search_enabled: boolean;
  is_temporary: boolean;
  threshold?: number | null;
  max_iterations?: number | null;
  timeout_seconds?: number | null;
  created_at: string;
  agents: ChatAgent[];
  iterations: Iteration[];
  messages: ChatMessage[];
  metadata?: {
    current_iteration?: number;
    current_best_score?: number;
    max_iterations?: number;
  };
}

export interface ConversationListItem {
  id: string;
  title: string;
  status: "active" | "completed" | "archived";
  best_score: number;
  created_at: string;
}

// ─── Settings Types ───
export interface UserSettings {
  id: string;
  user_id: string;
  global_threshold: number;
  max_iterations: number;
  timeout_seconds: number;
  hide_evaluator_scoring: boolean;
  preferred_generator_model: string;
  preferred_evaluator_model: string;
  preferred_critic_model: string;
  notifications_enabled: boolean;
  notify_in_app: boolean;
  notify_email: boolean;
  notify_slack: boolean;
  notify_teams: boolean;
  slack_webhook_url: string;
  teams_webhook_url: string;
  dark_mode: boolean;
  search_enabled: boolean;
}

export interface UpdateSettingsRequest {
  global_threshold?: number;
  max_iterations?: number;
  timeout_seconds?: number;
  hide_evaluator_scoring?: boolean;
  preferred_generator_model?: string;
  preferred_evaluator_model?: string;
  preferred_critic_model?: string;
  notifications_enabled?: boolean;
  notify_in_app?: boolean;
  notify_email?: boolean;
  notify_slack?: boolean;
  notify_teams?: boolean;
  slack_webhook_url?: string;
  teams_webhook_url?: string;
  dark_mode?: boolean;
  search_enabled?: boolean;
}

// ─── API Key Types ───
export interface APIKey {
  id: string;
  provider: string;
  label: string;
  base_url: string;
  is_active: boolean;
  key_preview: string;
  created_at: string;
}

export interface CreateAPIKeyRequest {
  provider: string;
  label: string;
  api_key: string;
  base_url: string;
}

export interface UpdateAPIKeyRequest {
  label?: string;
  api_key?: string;
  base_url?: string;
  is_active?: boolean;
}

// ─── MCP Server Types ───
export interface MCPServer {
  id: string;
  name: string;
  url: string;
  description: string;
  is_active: boolean;
  is_global: boolean;
  transport: "sse" | "stdio" | "http";
  headers: Record<string, string>;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface CreateMCPServerRequest {
  name: string;
  url: string;
  api_key?: string;
  description?: string;
  transport?: string;
  headers?: Record<string, string>;
  metadata?: Record<string, unknown>;
}

export interface UpdateMCPServerRequest {
  name?: string;
  url?: string;
  api_key?: string;
  description?: string;
  transport?: string;
  headers?: Record<string, string>;
  metadata?: Record<string, unknown>;
  is_active?: boolean;
}

// ─── Billing Types ───
export interface SubscriptionPlan {
  id: string;
  name: string;
  display_name: string;
  price_monthly: number;
  price_yearly: number;
  requests_per_minute: number;
  requests_per_day: number;
  max_tokens_per_request: number;
  features: string[];
}

export interface Subscription {
  id: string;
  plan_name: string;
  billing_cycle: "monthly" | "yearly";
  status: "active" | "cancelled" | "past_due";
  current_period_start: string;
  current_period_end: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  amount: number;
  currency: string;
  status: "pending" | "succeeded" | "failed" | "refunded";
  description: string;
  created_at: string;
}

export interface TokenUsage {
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  period_start: string;
  period_end: string;
  breakdown: TokenBreakdownItem[];
}

export interface TokenBreakdownItem {
  conversation_id: string;
  title: string;
  tokens_input: number;
  tokens_output: number;
  created_at: string;
}

export interface CreateSubscriptionRequest {
  plan_name: string;
  billing_cycle: "monthly" | "yearly";
  payment_method_id?: string;
}

// ─── Notification Types ───
export interface Notification {
  id: string;
  channel: "in_app" | "email" | "slack" | "teams";
  title: string;
  body: string;
  is_read: boolean;
  metadata: Record<string, unknown>;
  created_at: string;
}

// ─── Contact Types ───
export interface ContactRequest {
  name: string;
  email: string;
  company?: string;
  subject?: string;
  message: string;
  request_type: "general" | "business_upgrade" | "support";
}

// ─── Admin Types ───
export interface AdminDashboard {
  total_users: number;
  active_subscriptions: number;
  total_revenue: number;
  tokens_generated_month: number;
  tier_distribution: Record<string, number>;
  recent_transactions: Transaction[];
}

export interface AdminConfig {
  id: string;
  key: string;
  value: unknown;
  description: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}

export interface AdminConfigUpdateRequest {
  key: string;
  value: unknown;
  description?: string;
}

export interface AdminUserUpdateRequest {
  is_active?: boolean;
  is_verified?: boolean;
  is_admin?: boolean;
  tier?: "basic" | "pro" | "business";
}

export interface SystemPrompt {
  id: string;
  role: "generator" | "evaluator" | "reprompt";
  prompt: string;
  is_active: boolean;
  version: string;
  created_at: string;
  updated_at: string;
}

export interface SystemPromptUpdateRequest {
  role: "generator" | "evaluator" | "reprompt";
  prompt: string;
  version?: string;
}

export interface DomainRule {
  id: string;
  domain: string;
  rule_type: "whitelist" | "blacklist";
  created_at: string;
}

export interface DomainRuleRequest {
  domain: string;
  rule_type: "whitelist" | "blacklist";
}

export interface PlanUpdateRequest {
  display_name?: string;
  price_monthly?: number;
  price_yearly?: number;
  requests_per_minute?: number;
  requests_per_day?: number;
  max_tokens_per_request?: number;
  features?: string[];
  is_active?: boolean;
}

export interface ContactRequestItem {
  id: string;
  name: string;
  email: string;
  company: string;
  subject: string;
  message: string;
  request_type: string;
  is_resolved: boolean;
  resolved_by: string;
  created_at: string;
  updated_at: string;
}

// ─── API Response Wrappers ───
export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export type PaginatedResponse<T> = ApiResponse<PaginatedData<T>>;
