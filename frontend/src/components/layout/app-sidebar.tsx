"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { Badge } from "@/components/ui/badge";
import { useAuthStore } from "@/stores/auth-store";
import {
  MessageSquare,
  Settings,
  Key,
  Server,
  CreditCard,
  Bell,
  Shield,
  Plus,
  Zap,
} from "lucide-react";

const mainNav = [
  { title: "Chat", href: "/chat", icon: MessageSquare },
  { title: "New Chat", href: "/chat/new", icon: Plus },
];

const settingsNav = [
  { title: "General", href: "/settings", icon: Settings },
  { title: "API Keys", href: "/settings/api-keys", icon: Key },
  { title: "MCP Servers", href: "/settings/mcp-servers", icon: Server },
  { title: "Billing", href: "/settings/billing", icon: CreditCard },
  { title: "Notifications", href: "/settings/notifications", icon: Bell },
];

const adminNav = [
  { title: "Dashboard", href: "/admin", icon: Shield },
  { title: "Users", href: "/admin/users", icon: Shield },
  { title: "Plans & Pricing", href: "/admin/plans", icon: CreditCard },
  { title: "System Prompts", href: "/admin/prompts", icon: Zap },
  { title: "Domain Rules", href: "/admin/domains", icon: Server },
  { title: "MCP Servers", href: "/admin/mcp-servers", icon: Server },
  { title: "Configuration", href: "/admin/config", icon: Settings },
  { title: "Contact Requests", href: "/admin/contacts", icon: MessageSquare },
];

export function AppSidebar() {
  const pathname = usePathname();
  const { user } = useAuthStore();

  return (
    <Sidebar>
      <SidebarHeader className="border-b p-4">
        <Link href="/chat" className="flex items-center gap-2">
          <Zap className="h-6 w-6 text-primary" />
          <span className="text-lg font-bold">Accura</span>
        </Link>
        {user && (
          <Badge variant="secondary" className="mt-1 w-fit capitalize">
            {user.tier}
          </Badge>
        )}
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Conversations</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {mainNav.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname === item.href}
                  >
                    <Link href={item.href}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Settings</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {settingsNav.map((item) => (
                <SidebarMenuItem key={item.href}>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname === item.href}
                  >
                    <Link href={item.href}>
                      <item.icon className="h-4 w-4" />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        {user?.is_admin && (
          <SidebarGroup>
            <SidebarGroupLabel>Admin</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {adminNav.map((item) => (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      asChild
                      isActive={pathname === item.href}
                    >
                      <Link href={item.href}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t p-4">
        <p className="text-xs text-muted-foreground">
          &copy; {new Date().getFullYear()} Accura AI
        </p>
      </SidebarFooter>
    </Sidebar>
  );
}
