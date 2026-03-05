"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api-client";
import type { AdminConfig } from "@/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Settings, Pencil, Loader2, Save } from "lucide-react";
import { toast } from "sonner";

export default function AdminConfigPage() {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState<AdminConfig | null>(null);
  const [editValue, setEditValue] = useState("");
  const [editDescription, setEditDescription] = useState("");

  const { data: configs, isLoading } = useQuery({
    queryKey: ["admin", "config"],
    queryFn: async () => {
      const res = await adminApi.getConfig();
      return res.data as AdminConfig[];
    },
  });

  const updateConfig = useMutation({
    mutationFn: (data: { key: string; value: unknown; description?: string }) =>
      adminApi.updateConfig(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "config"] });
      toast.success("Configuration updated");
      setEditing(null);
    },
    onError: () => toast.error("Failed to update configuration"),
  });

  const openEdit = (config: AdminConfig) => {
    setEditing(config);
    setEditValue(
      typeof config.value === "string"
        ? config.value
        : JSON.stringify(config.value, null, 2)
    );
    setEditDescription(config.description || "");
  };

  const handleSave = () => {
    if (!editing) return;
    let parsedValue: unknown = editValue;
    try {
      parsedValue = JSON.parse(editValue);
    } catch {
      // keep as string
    }
    updateConfig.mutate({
      key: editing.key,
      value: parsedValue,
      description: editDescription || undefined,
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Platform Configuration</h1>
        <p className="text-muted-foreground">
          View and update global configuration key-value pairs
        </p>
      </div>

      {!configs || configs.length === 0 ? (
        <Card className="py-12 text-center">
          <CardContent>
            <Settings className="mx-auto h-12 w-12 text-muted-foreground" />
            <CardTitle className="mt-4">No Configuration</CardTitle>
            <CardDescription className="mt-2">
              No configuration entries found
            </CardDescription>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Key</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="w-[80px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {configs.map((config) => (
                <TableRow key={config.id}>
                  <TableCell className="font-mono text-sm">
                    {config.key}
                  </TableCell>
                  <TableCell className="max-w-[300px] truncate font-mono text-sm">
                    {typeof config.value === "string"
                      ? config.value
                      : JSON.stringify(config.value)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {config.description}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => openEdit(config)}
                    >
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editing} onOpenChange={() => setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Edit: <span className="font-mono">{editing?.key}</span>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Value</label>
              <Textarea
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                rows={5}
                className="font-mono text-sm"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Description</label>
              <Input
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={updateConfig.isPending}>
              {updateConfig.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
