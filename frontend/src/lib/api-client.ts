import { API_BASE_URL } from "./constants";
import type {
  ApiResponse,
  PaginatedResponse,
  TokenResponse,
  LoginRequest,
  RegisterRequest,
  RefreshRequest,
  VerifyEmailRequest,
  ChangePasswordRequest,
  UserWithProfile,
  ProfileUpdateRequest,
  CreateConversationRequest,
  ConversationListItem,
  Conversation,
  RenameConversationRequest,
  AddAgentRequest,
  Iteration,
  UserSettings,
  UpdateSettingsRequest,
  APIKey,
  CreateAPIKeyRequest,
  UpdateAPIKeyRequest,
  MCPServer,
  CreateMCPServerRequest,
  UpdateMCPServerRequest,
  SubscriptionPlan,
  Subscription,
  Transaction,
  TokenUsage,
  CreateSubscriptionRequest,
  Notification,
  ContactRequest,
  AdminDashboard,
  AdminConfig,
  AdminConfigUpdateRequest,
  AdminUserUpdateRequest,
  SystemPrompt,
  SystemPromptUpdateRequest,
  DomainRule,
  DomainRuleRequest,
  PlanUpdateRequest,
  User,
  ContactRequestItem,
} from "@/types";

// ─── Token Management ───
function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token");
}

function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("refresh_token");
}

function setTokens(access: string, refresh: string) {
  localStorage.setItem("access_token", access);
  localStorage.setItem("refresh_token", refresh);
}

function clearTokens() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

// ─── Base Fetch ───
async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  const token = getAccessToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    console.debug("apiFetch", url, options);
    res = await fetch(url, { ...options, headers });
  } catch (e: any) {
    // network error, e.g. backend not reachable
    console.error("apiFetch network error", url, e);
    throw new ApiError(e.message || "Failed to fetch", 0);
  }

  if (res.status === 401 && token) {
    // Attempt token refresh
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      headers["Authorization"] = `Bearer ${getAccessToken()}`;
      const retryRes = await fetch(url, { ...options, headers });
      if (!retryRes.ok) {
        const err = await retryRes.json().catch(() => ({}));
        throw new ApiError(
          err.message || retryRes.statusText,
          retryRes.status
        );
      }
      return retryRes.json();
    } else {
      clearTokens();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new ApiError("Session expired", 401);
    }
  }

  if (!res.ok) {
    console.error("apiFetch non-ok", url, res.status, res.statusText);
    const err = await res.json().catch(() => ({}));
    throw new ApiError(err.message || res.statusText, res.status);
  }

  return res.json();
}

async function tryRefreshToken(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) return false;

    const data: ApiResponse<TokenResponse> = await res.json();
    setTokens(data.data.access_token, data.data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

// ═══════════════════════════════════════════════════════
// AUTH
// ═══════════════════════════════════════════════════════
export const authApi = {
  register(data: RegisterRequest) {
    return apiFetch<ApiResponse<{ user_id: string }>>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  login(data: LoginRequest) {
    return apiFetch<ApiResponse<TokenResponse>>("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }).then((res) => {
      setTokens(res.data.access_token, res.data.refresh_token);
      return res;
    });
  },

  refresh(data: RefreshRequest) {
    return apiFetch<ApiResponse<TokenResponse>>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  verifyEmail(data: VerifyEmailRequest) {
    return apiFetch<ApiResponse<null>>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  changePassword(data: ChangePasswordRequest) {
    return apiFetch<ApiResponse<null>>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  forgotPassword(email: string) {
    return apiFetch<ApiResponse<null>>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },

  resetPassword(token: string, new_password: string) {
    return apiFetch<ApiResponse<null>>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
    });
  },

  logout() {
    clearTokens();
  },
};

// ═══════════════════════════════════════════════════════
// USER
// ═══════════════════════════════════════════════════════
export const userApi = {
  getMe() {
    return apiFetch<ApiResponse<UserWithProfile>>("/user/me");
  },

  updateProfile(data: ProfileUpdateRequest) {
    return apiFetch<ApiResponse<UserWithProfile>>("/user/profile", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },
};

// ═══════════════════════════════════════════════════════
// CHAT
// ═══════════════════════════════════════════════════════
export const chatApi = {
  create(data: CreateConversationRequest) {
    return apiFetch<ApiResponse<Conversation>>("/chat", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  list(page = 1, perPage = 20) {
    return apiFetch<PaginatedResponse<ConversationListItem>>(
      `/chat?page=${page}&per_page=${perPage}`
    );
  },

  get(id: string) {
    return apiFetch<ApiResponse<Conversation>>(`/chat/${id}`);
  },

  rename(id: string, data: RenameConversationRequest) {
    return apiFetch<ApiResponse<null>>(`/chat/${id}/rename`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  },

  addAgent(id: string, data: AddAgentRequest) {
    return apiFetch<ApiResponse<Conversation>>(`/chat/${id}/agent`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  delete(id: string) {
    return apiFetch<ApiResponse<null>>(`/chat/${id}`, {
      method: "DELETE",
    });
  },

  getIterations(id: string) {
    return apiFetch<ApiResponse<Iteration[]>>(`/chat/${id}/iterations`);
  },

  getTokens(id: string) {
    return apiFetch<ApiResponse<TokenUsage>>(`/chat/${id}/tokens`);
  },
};

// ═══════════════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════════════
export const settingsApi = {
  get() {
    return apiFetch<ApiResponse<UserSettings>>("/settings");
  },

  update(data: UpdateSettingsRequest) {
    return apiFetch<ApiResponse<UserSettings>>("/settings", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },
};

// ═══════════════════════════════════════════════════════
// API KEYS (BYOK)
// ═══════════════════════════════════════════════════════
export const apiKeysApi = {
  list() {
    return apiFetch<ApiResponse<APIKey[]>>("/api-keys");
  },

  create(data: CreateAPIKeyRequest) {
    return apiFetch<ApiResponse<APIKey>>("/api-keys", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(id: string, data: UpdateAPIKeyRequest) {
    return apiFetch<ApiResponse<APIKey>>(`/api-keys/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete(id: string) {
    return apiFetch<ApiResponse<null>>(`/api-keys/${id}`, {
      method: "DELETE",
    });
  },
};

// ═══════════════════════════════════════════════════════
// MCP SERVERS
// ═══════════════════════════════════════════════════════
export const mcpApi = {
  list() {
    return apiFetch<ApiResponse<MCPServer[]>>("/mcp-servers");
  },

  get(id: string) {
    return apiFetch<ApiResponse<MCPServer>>(`/mcp-servers/${id}`);
  },

  create(data: CreateMCPServerRequest) {
    return apiFetch<ApiResponse<MCPServer>>("/mcp-servers", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  update(id: string, data: UpdateMCPServerRequest) {
    return apiFetch<ApiResponse<MCPServer>>(`/mcp-servers/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  delete(id: string) {
    return apiFetch<ApiResponse<null>>(`/mcp-servers/${id}`, {
      method: "DELETE",
    });
  },

  test(id: string) {
    return apiFetch<ApiResponse<{ status: string }>>(`/mcp-servers/${id}/test`, {
      method: "POST",
    });
  },
};

// ═══════════════════════════════════════════════════════
// BILLING
// ═══════════════════════════════════════════════════════
export const billingApi = {
  getPlans() {
    return apiFetch<ApiResponse<SubscriptionPlan[]>>("/billing/plans");
  },

  subscribe(data: CreateSubscriptionRequest) {
    return apiFetch<ApiResponse<Subscription>>("/billing/subscribe", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  cancel() {
    return apiFetch<ApiResponse<null>>("/billing/cancel", {
      method: "POST",
    });
  },

  getSubscription() {
    return apiFetch<ApiResponse<Subscription>>("/billing/subscription");
  },

  getTransactions(limit = 50, offset = 0) {
    return apiFetch<ApiResponse<Transaction[]>>(
      `/billing/transactions?limit=${limit}&offset=${offset}`
    );
  },

  getTokenUsage() {
    return apiFetch<ApiResponse<TokenUsage>>("/billing/tokens");
  },
};

// ═══════════════════════════════════════════════════════
// NOTIFICATIONS
// ═══════════════════════════════════════════════════════
export const notificationsApi = {
  list(unreadOnly = false, limit = 50, offset = 0) {
    return apiFetch<ApiResponse<Notification[]>>(
      `/notifications?unread_only=${unreadOnly}&limit=${limit}&offset=${offset}`
    );
  },

  markAsRead(id: string) {
    return apiFetch<ApiResponse<null>>(`/notifications/${id}/read`, {
      method: "PATCH",
    });
  },

  markRead(id: string) {
    return apiFetch<ApiResponse<null>>(`/notifications/${id}/read`, {
      method: "PATCH",
    });
  },

  markAllRead() {
    return apiFetch<ApiResponse<null>>("/notifications/read-all", {
      method: "PATCH",
    });
  },
};

// ═══════════════════════════════════════════════════════
// CONTACT
// ═══════════════════════════════════════════════════════
export const contactApi = {
  submit(data: ContactRequest) {
    return apiFetch<ApiResponse<null>>("/contact", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};

// ═══════════════════════════════════════════════════════
// ADMIN
// ═══════════════════════════════════════════════════════
export const adminApi = {
  getDashboard() {
    return apiFetch<ApiResponse<AdminDashboard>>("/admin/dashboard");
  },

  listUsers(page = 1, perPage = 20, search?: string) {
    const params = new URLSearchParams({
      page: String(page),
      per_page: String(perPage),
    });
    if (search) params.set("search", search);
    return apiFetch<PaginatedResponse<User>>(`/admin/users?${params}`);
  },

  getUser(id: string) {
    return apiFetch<ApiResponse<UserWithProfile>>(`/admin/users/${id}`);
  },

  updateUser(id: string, data: AdminUserUpdateRequest) {
    return apiFetch<ApiResponse<User>>(`/admin/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  getConfig() {
    return apiFetch<ApiResponse<AdminConfig[]>>("/admin/config");
  },

  updateConfig(data: AdminConfigUpdateRequest) {
    return apiFetch<ApiResponse<AdminConfig>>("/admin/config", {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  getSystemPrompts() {
    return apiFetch<ApiResponse<SystemPrompt[]>>("/admin/system-prompts");
  },

  createSystemPrompt(data: SystemPromptUpdateRequest) {
    return apiFetch<ApiResponse<SystemPrompt>>("/admin/system-prompts", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateSystemPrompt(id: string, data: SystemPromptUpdateRequest) {
    return apiFetch<ApiResponse<SystemPrompt>>(`/admin/system-prompts/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  deleteSystemPrompt(id: string) {
    return apiFetch<ApiResponse<null>>(`/admin/system-prompts/${id}`, {
      method: "DELETE",
    });
  },

  getDomainRules() {
    return apiFetch<ApiResponse<DomainRule[]>>("/admin/domain-rules");
  },

  createDomainRule(data: DomainRuleRequest) {
    return apiFetch<ApiResponse<DomainRule>>("/admin/domain-rules", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  updateDomainRule(id: string, data: DomainRuleRequest) {
    return apiFetch<ApiResponse<DomainRule>>(`/admin/domain-rules/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  deleteDomainRule(id: string) {
    return apiFetch<ApiResponse<null>>(`/admin/domain-rules/${id}`, {
      method: "DELETE",
    });
  },

  getPlans() {
    return apiFetch<ApiResponse<SubscriptionPlan[]>>("/admin/plans");
  },

  updatePlan(id: string, data: PlanUpdateRequest) {
    return apiFetch<ApiResponse<SubscriptionPlan>>(`/admin/plans/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  createMCPServer(data: CreateMCPServerRequest) {
    return apiFetch<ApiResponse<MCPServer>>("/admin/mcp-servers", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  listMCPServers() {
    return apiFetch<ApiResponse<MCPServer[]>>("/admin/mcp-servers");
  },

  updateMCPServer(id: string, data: UpdateMCPServerRequest) {
    return apiFetch<ApiResponse<MCPServer>>(`/admin/mcp-servers/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  deleteMCPServer(id: string) {
    return apiFetch<ApiResponse<null>>(`/admin/mcp-servers/${id}`, {
      method: "DELETE",
    });
  },

  listContactRequests(page = 1, perPage = 20) {
    return apiFetch<PaginatedResponse<ContactRequestItem>>(
      `/admin/contact-requests?page=${page}&per_page=${perPage}`
    );
  },

  resolveContactRequest(id: string) {
    return apiFetch<ApiResponse<null>>(`/admin/contact-requests/${id}`, {
      method: "PUT",
    });
  },

  updateContactRequest(id: string, data: { status: string; reply?: string }) {
    return apiFetch<ApiResponse<null>>(`/admin/contact-requests/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  getContactRequests({ page = 1 }: { page?: number } = {}) {
    return this.listContactRequests(page);
  },

  // Alias methods so pages can use camelCase variants
  getMcpServers() {
    return this.listMCPServers();
  },

  createMcpServer(data: CreateMCPServerRequest) {
    return this.createMCPServer(data);
  },

  updateMcpServer(id: string, data: UpdateMCPServerRequest) {
    return this.updateMCPServer(id, data);
  },

  deleteMcpServer(id: string) {
    return this.deleteMCPServer(id);
  },

  reloadConfig() {
    return apiFetch<ApiResponse<null>>("/admin/reload-config", {
      method: "POST",
    });
  },
};

// Helper exports
export { getAccessToken, getRefreshToken, setTokens, clearTokens };
