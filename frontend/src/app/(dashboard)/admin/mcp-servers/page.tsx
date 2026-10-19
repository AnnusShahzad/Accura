"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { createMcpServerSchema, type CreateMcpServerFormData } from "@/lib/validations";
import { adminApi } from "@/lib/api-client";
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import { Server, Plus, Pencil, Trash2, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function AdminMcpServersPage() {
  const queryClient = useQueryClient();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editing, setEditing] = useState<MCPServer | null>(null);

  const { data: servers, isLoading } = useQuery({
    queryKey: ["admin", "mcp-servers"],
    queryFn: async () => {
      const res = await adminApi.getMcpServers();
      return res.data as MCPServer[];
    },
  });

  const saveMutation = useMutation({
    mutationFn: (data: CreateMcpServerFormData) => {
      // A blank key field means "keep the current key", not "remove it"
      const { api_key, ...rest } = data;
      const payload = api_key ? { ...rest, api_key } : rest;
      return editing
        ? adminApi.updateMcpServer(editing.id, payload)
        : adminApi.createMcpServer(payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "mcp-servers"] });
      toast.success(editing ? "Server updated" : "Server added");
      setIsDialogOpen(false);
      setEditing(null);
    },
    onError: (e: Error) => toast.error(e.message || "Failed to save server"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.deleteMcpServer(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "mcp-servers"] });
      toast.success("Server deleted");
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
    values: editing
      ? {
          name: editing.name,
          url: editing.url,
          api_key: "",
          description: editing.description || "",
          transport: editing.transport,
        }
      : undefined,
  });

  const openCreate = () => {
    setEditing(null);
    form.reset({
      name: "",
      url: "",
      api_key: "",
      description: "",
      transport: "http",
    });
    setIsDialogOpen(true);
  };

  const openEdit = (server: MCPServer) => {
    setEditing(server);
    setIsDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Global MCP Servers</h1>
          <p className="text-muted-foreground">
            Manage platform-wide MCP servers available to all users
          </p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Add Server
        </Button>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : !servers || servers.length === 0 ? (
        <Card className="py-12 text-center">
          <CardContent>
            <Server className="mx-auto h-12 w-12 text-muted-foreground" />
            <CardTitle className="mt-4">No Global MCP Servers</CardTitle>
            <CardDescription className="mt-2">
              Add platform-wide MCP servers for all users
            </CardDescription>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {servers.map((server) => (
            <Card key={server.id}>
              <CardContent className="flex items-center gap-4 py-4">
                <Server className="h-8 w-8 text-muted-foreground" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <p className="font-medium">{server.name}</p>
                    <Badge variant="outline">{server.transport}</Badge>
                    {server.is_active ? (
                      <Badge className="bg-green-500/15 text-green-600">Active</Badge>
                    ) : (
                      <Badge variant="secondary">Inactive</Badge>
                    )}
                  </div>
                  {server.description && (
                    <p className="text-sm text-muted-foreground">
                      {server.description}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">{server.url}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => openEdit(server)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete Server?</AlertDialogTitle>
                        <AlertDialogDescription>
                          This will remove the server for all users.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Cancel</AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => deleteMutation.mutate(server.id)}
                        >
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog
        open={isDialogOpen}
        onOpenChange={(v) => {
          setIsDialogOpen(v);
          if (!v) setEditing(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {editing ? "Edit MCP Server" : "Add Global MCP Server"}
            </DialogTitle>
          </DialogHeader>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit((data) => saveMutation.mutate(data))}
              className="space-y-4"
            >
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input placeholder="Web Search Server" {...field} />
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
                      <Input placeholder="https://mcp.example.com" {...field} />
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
                    <FormLabel>
                      API Key {editing ? "(leave blank to keep existing)" : "(Optional)"}
                    </FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
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
                <Button type="submit" disabled={saveMutation.isPending}>
                  {saveMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {editing ? "Update" : "Add Server"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
