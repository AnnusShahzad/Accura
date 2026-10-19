"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { createMcpServerSchema, type CreateMcpServerFormData } from "@/lib/validations";
import { mcpApi } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import Link from "next/link";
import { Switch } from "@/components/ui/switch";
import { MCP_TRANSPORTS } from "@/lib/constants";
import type { MCPServer } from "@/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Server, Plus, Trash2, Loader2, Wifi, Globe } from "lucide-react";
import { toast } from "sonner";

export default function McpServersPage() {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const { user } = useAuthStore();
  const canAddServers = user?.tier === "pro" || user?.tier === "business";

  // One request returns both the user's servers and the platform's
  // global ones (the admin endpoint is admin-only and 403s for users).
  const { data: servers, isLoading } = useQuery({
    queryKey: ["mcp-servers"],
    queryFn: async () => {
      const res = await mcpApi.list();
      return res.data;
    },
  });
  const globalServers = servers?.filter((s) => s.is_global);
  const userServers = servers?.filter((s) => !s.is_global);

  const createServer = useMutation({
    mutationFn: (data: CreateMcpServerFormData) => mcpApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      toast.success("MCP server added");
      setIsDialogOpen(false);
    },
    onError: (e: Error) => toast.error(e.message || "Failed to add server"),
  });

  const testServer = useMutation({
    mutationFn: (id: string) => mcpApi.test(id),
    onSuccess: (res) => {
      const tools = res.data.tools.map((t) => t.name).join(", ");
      toast.success(res.message, { description: tools ? `Tools: ${tools}` : "No tools exposed" });
    },
    onError: (e: Error) => toast.error(e.message || "Connection failed"),
  });

  const toggleServer = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      mcpApi.update(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["mcp-servers"] }),
    onError: (e: Error) => toast.error(e.message || "Failed to update server"),
  });

  const deleteServer = useMutation({
    mutationFn: (id: string) => mcpApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["mcp-servers"] });
      toast.success("MCP server deleted");
    },
    onError: (e: Error) => toast.error(e.message || "Failed to delete server"),
  });

  const form = useForm<CreateMcpServerFormData>({
    resolver: zodResolver(createMcpServerSchema),
    defaultValues: {
      name: "",
      url: "",
      api_key: "",
      description: "",
      transport: "http",
    },
  });

  const ServerCard = ({ server, global: isGlobal }: { server: MCPServer; global?: boolean }) => (
    <Card>
      <CardContent className="flex items-center gap-4 py-4">
        <Server className="h-8 w-8 text-muted-foreground" />
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <p className="font-medium">{server.name}</p>
            <Badge variant="outline">{server.transport}</Badge>
            {isGlobal && (
              <Badge variant="secondary">
                <Globe className="mr-1 h-3 w-3" />
                Global
              </Badge>
            )}
            {server.is_active ? (
              <Badge className="bg-green-500/15 text-green-600">Active</Badge>
            ) : (
              <Badge variant="outline">Disabled</Badge>
            )}
          </div>
          {server.description && (
            <p className="text-sm text-muted-foreground">{server.description}</p>
          )}
          <p className="text-xs text-muted-foreground">{server.url}</p>
        </div>
        {!isGlobal && (
          <div className="flex items-center gap-2">
            <Switch
              checked={server.is_active}
              aria-label={server.is_active ? "Disable server" : "Enable server"}
              onCheckedChange={(checked) =>
                toggleServer.mutate({ id: server.id, is_active: checked })
              }
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => testServer.mutate(server.id)}
              disabled={testServer.isPending}
            >
              {testServer.isPending ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : (
                <Wifi className="mr-1 h-3 w-3" />
              )}
              Test
            </Button>
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="ghost" size="icon">
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete MCP Server?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This action cannot be undone.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={() => deleteServer.mutate(server.id)}>
                    Delete
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">MCP Servers</h1>
          <p className="text-muted-foreground">
            Connect external Model Context Protocol servers for tool access
          </p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button disabled={!canAddServers}>
              <Plus className="mr-2 h-4 w-4" />
              Add Server
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add MCP Server</DialogTitle>
              <DialogDescription>
                Connect a new MCP server to extend agent capabilities.
              </DialogDescription>
            </DialogHeader>
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit((data) => createServer.mutate(data))}
                className="space-y-4"
              >
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Name</FormLabel>
                      <FormControl>
                        <Input placeholder="My MCP Server" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="url"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>URL</FormLabel>
                      <FormControl>
                        <Input placeholder="https://mcp.example.com/mcp" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="transport"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Transport</FormLabel>
                      <Select onValueChange={field.onChange} value={field.value}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {MCP_TRANSPORTS.map((t) => (
                            <SelectItem key={t.value} value={t.value}>
                              {t.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="api_key"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>API Key (Optional)</FormLabel>
                      <FormControl>
                        <Input type="password" placeholder="Bearer key" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="description"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Description (Optional)</FormLabel>
                      <FormControl>
                        <Textarea placeholder="What this server provides..." {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <DialogFooter>
                  <Button type="submit" disabled={createServer.isPending}>
                    {createServer.isPending && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Add Server
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </DialogContent>
        </Dialog>
      </div>

      {!canAddServers && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="flex flex-wrap items-center justify-between gap-3 py-4">
            <p className="text-sm">
              Connecting your own MCP servers is available on the Pro and Business plans.
              Platform servers below are available to everyone.
            </p>
            <Button size="sm" asChild>
              <Link href="/settings/billing">Upgrade</Link>
            </Button>
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : (
        <>
          {globalServers && globalServers.length > 0 && (
            <div className="space-y-3">
              <h2 className="text-lg font-semibold">Platform Servers</h2>
              <p className="text-sm text-muted-foreground">
                Globally available servers managed by the platform
              </p>
              {globalServers.map((server: MCPServer) => (
                <ServerCard key={server.id} server={server} global />
              ))}
            </div>
          )}

          <Separator />

          <div className="space-y-3">
            <h2 className="text-lg font-semibold">Your Servers</h2>
            {!userServers || userServers.length === 0 ? (
              <Card className="py-12 text-center">
                <CardContent>
                  <Server className="mx-auto h-12 w-12 text-muted-foreground" />
                  <CardTitle className="mt-4">No Custom Servers</CardTitle>
                  <CardDescription className="mt-2">
                    Add your own MCP servers for extended tool access
                  </CardDescription>
                </CardContent>
              </Card>
            ) : (
              userServers.map((server: MCPServer) => (
                <ServerCard key={server.id} server={server} />
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}
