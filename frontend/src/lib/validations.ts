import { z } from "zod";

// ─── Auth Validations ───
export const loginSchema = z.object({
  email: z.string().email("Please enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

export const registerSchema = z
  .object({
    email: z.string().email("Please enter a valid email"),
    username: z
      .string()
      .min(5, "Username must be at least 5 characters")
      .max(150)
      .regex(
        /^[a-zA-Z0-9_]+$/,
        "Username can only contain letters, numbers, and underscores"
      ),
    password: z
      .string()
      .min(9, "Password must be greater than 8 characters")
      .max(128)
      .regex(/[A-Z]/, "Password must contain at least 1 uppercase letter")
      .regex(/[a-z]/, "Password must contain at least 1 lowercase letter")
      .regex(/[0-9]/, "Password must contain at least 1 number")
      .regex(
        /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/,
        "Password must contain at least 1 special character"
      ),
    confirmPassword: z.string(),
    first_name: z.string().max(150).optional(),
    last_name: z.string().max(150).optional(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

export const changePasswordSchema = z
  .object({
    old_password: z.string().min(1, "Current password is required"),
    new_password: z
      .string()
      .min(9, "Password must be greater than 8 characters")
      .max(128)
      .regex(/[A-Z]/, "Password must contain at least 1 uppercase letter")
      .regex(/[a-z]/, "Password must contain at least 1 lowercase letter")
      .regex(/[0-9]/, "Password must contain at least 1 number")
      .regex(
        /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/,
        "Password must contain at least 1 special character"
      ),
    confirmPassword: z.string(),
  })
  .refine((data) => data.new_password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

export const forgotPasswordSchema = z.object({
  email: z.string().email("Please enter a valid email"),
});

export const resetPasswordSchema = z
  .object({
    new_password: z
      .string()
      .min(8, "Password must be at least 8 characters")
      .max(128),
    confirmPassword: z.string(),
  })
  .refine((data) => data.new_password === data.confirmPassword, {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  });

export const verifyOtpSchema = z.object({
  email: z.string().email("Please enter a valid email"),
  otp: z
    .string()
    .length(6, "OTP must be 6 digits")
    .regex(/^\d+$/, "OTP must contain only numbers"),
});

// ─── Profile Validations ───
export const profileSchema = z.object({
  first_name: z.string().max(150).optional(),
  last_name: z.string().max(150).optional(),
  phone: z.string().max(30).optional(),
  company: z.string().max(255).optional(),
  timezone: z.string().max(64).optional(),
});

// ─── Chat Validations ───
export const createConversationSchema = z.object({
  prompt: z.string().min(1, "Prompt is required"),
  title: z.string().max(500).optional(),
  generator_model: z.string().optional(),
  generator_provider: z.string().optional(),
  evaluator_model: z.string().optional(),
  evaluator_provider: z.string().optional(),
  search_enabled: z.boolean().optional(),
  is_temporary: z.boolean().optional(),
  threshold: z.number().min(0).max(100).optional(),
  max_iterations: z.number().min(1).max(50).optional(),
  timeout_seconds: z.number().min(5).max(600).optional(),
});

export const addAgentSchema = z.object({
  provider: z.string().min(1, "Provider is required"),
  model: z.string().min(1, "Model is required"),
  role: z.string().default("generator"),
});

// ─── Settings Validations ───
export const settingsSchema = z.object({
  global_threshold: z.number().min(0).max(100).optional(),
  max_iterations: z.number().min(1).max(50).optional(),
  timeout_seconds: z.number().min(5).max(600).optional(),
  hide_evaluator_scoring: z.boolean().optional(),
  preferred_generator_model: z.string().optional(),
  preferred_evaluator_model: z.string().optional(),
  preferred_critic_model: z.string().optional(),
  notifications_enabled: z.boolean().optional(),
  notify_in_app: z.boolean().optional(),
  notify_email: z.boolean().optional(),
  notify_slack: z.boolean().optional(),
  notify_teams: z.boolean().optional(),
  slack_webhook_url: z.string().max(500).optional(),
  teams_webhook_url: z.string().max(500).optional(),
  dark_mode: z.boolean().optional(),
  search_enabled: z.boolean().optional(),
});

// ─── API Key Validations ───
export const createApiKeySchema = z.object({
  provider: z.string().min(1, "Provider is required").max(50),
  label: z.string().max(255),
  api_key: z.string().min(1, "API key is required"),
  base_url: z.string().url("Must be a valid URL").or(z.literal("")),
});

// ─── MCP Server Validations ───
export const createMcpServerSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  url: z.string().min(1, "URL is required"),
  api_key: z.string().optional(),
  description: z.string(),
  transport: z.enum(["sse", "stdio", "http"]),
});

// ─── Contact Validations ───
export const contactSchema = z.object({
  name: z.string().min(1, "Name is required").max(255),
  email: z.string().email("Please enter a valid email").max(320),
  company: z.string().max(255).optional(),
  subject: z.string().max(500).optional(),
  message: z.string().min(1, "Message is required"),
  request_type: z.enum(["general", "business_upgrade", "support"]),
});

// ─── Admin Validations ───
export const systemPromptSchema = z.object({
  role: z.enum(["generator", "evaluator", "reprompt"]),
  prompt: z.string().min(1, "Prompt is required"),
  version: z.string().min(1, "Version is required"),
});

export const domainRuleSchema = z.object({
  domain: z.string().min(1, "Domain is required").max(500),
  rule_type: z.enum(["whitelist", "blacklist"]),
});

export const planUpdateSchema = z.object({
  display_name: z.string().optional(),
  price_monthly: z.number().min(0).optional(),
  price_yearly: z.number().min(0).optional(),
  requests_per_minute: z.number().min(1).optional(),
  requests_per_day: z.number().min(1).optional(),
  max_tokens_per_request: z.number().min(1).optional(),
  features: z.array(z.string()).optional(),
  is_active: z.boolean().optional(),
});

// ─── Type Exports ───
export type LoginFormData = z.infer<typeof loginSchema>;
export type RegisterFormData = z.infer<typeof registerSchema>;
export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;
export type VerifyOtpFormData = z.infer<typeof verifyOtpSchema>;
export type ProfileFormData = z.infer<typeof profileSchema>;
export type CreateConversationFormData = z.infer<typeof createConversationSchema>;
export type AddAgentFormData = z.infer<typeof addAgentSchema>;
export type SettingsFormData = z.infer<typeof settingsSchema>;
export type CreateApiKeyFormData = z.infer<typeof createApiKeySchema>;
export type CreateMcpServerFormData = z.infer<typeof createMcpServerSchema>;
export type ContactFormData = z.infer<typeof contactSchema>;
export type SystemPromptFormData = z.infer<typeof systemPromptSchema>;
export type DomainRuleFormData = z.infer<typeof domainRuleSchema>;
export type PlanUpdateFormData = z.infer<typeof planUpdateSchema>;
export type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;
