"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api-client";
import type { AdminConfig } from "@/types";
import {
  Card,
  CardContent,
  CardDescription,
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
  DialogDescription,
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
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Settings, Pencil, Loader2, Save, Plus, Trash2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const KEY_PATTERN = /^[A-Za-z0-9_-]+(\.[A-Za-z0-9_-]+)*$/;

const EXAMPLES = [
  "evaluation.global_threshold",
  "evaluation.default_max_iterations",
  "ai.default_generator_model",
  "ai.max_tool_rounds",
  "branding.support_email",
];

function formatValue(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

export default function AdminConfigPage() {
  const queryClient = useQueryClient();
  // null = closed, "new" = creating, otherwise the entry being edited
  const [editing, setEditing] = useState<AdminConfig | "new" | null>(null);
  const [editKey, setEditKey] = useState("");
  const [editValue, setEditValue] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [deleting, setDeleting] = useState<AdminConfig | null>(null);

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
      toast.success("Configuration saved and applied");
      setEditing(null);
    },
    onError: (e: Error) => toast.error(e.message || "Failed to update configuration"),
  });

  const deleteConfig = useMutation({
    mutationFn: (key: string) => adminApi.deleteConfig(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "config"] });
      toast.success("Override removed – default restored");
      setDeleting(null);
    },
    onError: (e: Error) => toast.error(e.message || "Failed to delete entry"),
  });

  const reload = useMutation({
    mutationFn: () => adminApi.reloadConfig(),
    onSuccess: () => toast.success("config.yaml and environment reloaded"),
    onError: (e: Error) => toast.error(e.message || "Failed to reload configuration"),
  });

  const openCreate = () => {
    setEditing("new");
    setEditKey("");
    setEditValue("");
    setEditDescription("");
  };

  const openEdit = (config: AdminConfig) => {
    setEditing(config);
    setEditKey(config.key);
    setEditValue(formatValue(config.value));
    setEditDescription(config.description || "");
  };

  const keyValid = KEY_PATTERN.test(editKey);

  const handleSave = () => {
    if (!editing || !keyValid) return;
    // Numbers, booleans, objects and quoted strings are parsed as JSON;
    // anything else is stored as a plain string.
    let parsedValue: unknown = editValue;
    try {
      parsedValue = JSON.parse(editValue);
    } catch {
      // keep as string
    }
    updateConfig.mutate({
      key: editKey,
      value: parsedValue,
      description: editDescription,
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
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Platform Configuration</h1>
          <p className="text-muted-foreground">
            Runtime overrides for config.yaml. Keys are dotted paths (e.g.{" "}
            <code className="font-mono text-xs">evaluation.global_threshold</code>) and take
            effect immediately, without a restart.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => reload.mutate()} disabled={reload.isPending}>
            {reload.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="mr-2 h-4 w-4" />
            )}
            Reload YAML
          </Button>
          <Button onClick={openCreate}>
            <Plus className="mr-2 h-4 w-4" />
            Add Override
          </Button>
        </div>
      </div>

      {!configs || configs.length === 0 ? (
        <Card className="py-12 text-center">
          <CardContent>
            <Settings className="mx-auto h-12 w-12 text-muted-foreground" />
            <CardTitle className="mt-4">No Overrides</CardTitle>
            <CardDescription className="mt-2">
              Everything currently comes from config.yaml and environment variables.
            </CardDescription>
            <Button className="mt-4" variant="outline" onClick={openCreate}>
              <Plus className="mr-2 h-4 w-4" />
              Add your first override
            </Button>
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
                <TableHead>Updated by</TableHead>
                <TableHead className="w-[100px]">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {configs.map((config) => (
                <TableRow key={config.id}>
                  <TableCell className="font-mono text-sm">{config.key}</TableCell>
                  <TableCell className="max-w-[300px] truncate font-mono text-sm">
                    {typeof config.value === "string"
                      ? config.value
                      : JSON.stringify(config.value)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {config.description}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {config.updated_by}
                  </TableCell>
                  <TableCell>
                    <div className="flex">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Edit ${config.key}`}
                        onClick={() => openEdit(config)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete ${config.key}`}
                        onClick={() => setDeleting(config)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={!!editing} onOpenChange={(open) => !open && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing === "new" ? "Add Override" : "Edit Override"}</DialogTitle>
            <DialogDescription>
              Values are parsed as JSON when possible (numbers, true/false, lists,
              objects); anything else is saved as text.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="config-key">Key</Label>
              <Input
                id="config-key"
                value={editKey}
                onChange={(e) => setEditKey(e.target.value.trim())}
                disabled={editing !== "new"}
                placeholder="evaluation.global_threshold"
                className="font-mono"
                list="config-key-examples"
              />
              <datalist id="config-key-examples">
                {EXAMPLES.map((k) => (
                  <option key={k} value={k} />
                ))}
              </datalist>
              {editKey && !keyValid && (
                <p className="text-xs text-destructive">
                  Use letters, numbers, - and _ separated by dots.
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="config-value">Value</Label>
              <Textarea
                id="config-value"
                value={editValue}
                onChange={(e) => setEditValue(e.target.value)}
                rows={6}
                className="font-mono text-sm"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="config-description">Description</Label>
              <Input
                id="config-description"
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={updateConfig.isPending || !keyValid}>
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

      <AlertDialog open={!!deleting} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remove this override?</AlertDialogTitle>
            <AlertDialogDescription>
              <code className="font-mono">{deleting?.key}</code> will fall back to its value
              from config.yaml or the environment.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleting && deleteConfig.mutate(deleting.key)}>
              Remove
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
