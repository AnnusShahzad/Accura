"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { settingsSchema, type SettingsFormData } from "@/lib/validations";
import { settingsApi } from "@/lib/api-client";
import { useSettings } from "@/hooks/use-settings";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { Bell, Loader2, Webhook, Mail, MessageSquare } from "lucide-react";
import { toast } from "sonner";

const channelIcons: Record<string, React.ReactNode> = {
  in_app: <Bell className="h-5 w-5" />,
  email: <Mail className="h-5 w-5" />,
  slack: <MessageSquare className="h-5 w-5" />,
  teams: <MessageSquare className="h-5 w-5" />,
};

export default function NotificationsSettingsPage() {
  const queryClient = useQueryClient();
  const { data: settings, isLoading } = useSettings();

  const updateSettings = useMutation({
    mutationFn: (data: Partial<SettingsFormData>) => settingsApi.update(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      toast.success("Notification settings saved");
    },
    onError: (e: Error) => toast.error(e.message || "Failed to save settings"),
  });

  const form = useForm<SettingsFormData>({
    resolver: zodResolver(settingsSchema),
    defaultValues: {
      notify_in_app: settings?.notify_in_app ?? true,
      notify_email: settings?.notify_email ?? false,
      notify_slack: settings?.notify_slack ?? false,
      notify_teams: settings?.notify_teams ?? false,
      slack_webhook_url: settings?.slack_webhook_url ?? "",
      teams_webhook_url: settings?.teams_webhook_url ?? "",
    },
    values: settings
      ? {
          notify_in_app: settings.notify_in_app,
          notify_email: settings.notify_email,
          notify_slack: settings.notify_slack,
          notify_teams: settings.notify_teams,
          slack_webhook_url: settings.slack_webhook_url || "",
          teams_webhook_url: settings.teams_webhook_url || "",
        }
      : undefined,
  });

  const watchSlack = form.watch("notify_slack");
  const watchTeams = form.watch("notify_teams");

  const onSubmit = (data: SettingsFormData) => {
    if (data.notify_slack && !data.slack_webhook_url) {
      form.setError("slack_webhook_url", { message: "Required when Slack notifications are on" });
      return;
    }
    if (data.notify_teams && !data.teams_webhook_url) {
      form.setError("teams_webhook_url", { message: "Required when Teams notifications are on" });
      return;
    }
    updateSettings.mutate(data);
  };

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Notifications</h1>
        <p className="text-muted-foreground">
          Configure how and where you receive notifications
        </p>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Notification Channels */}
        <Card>
          <CardHeader>
            <CardTitle>Channels</CardTitle>
            <CardDescription>
              Choose which channels you want to receive notifications on
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="flex items-center gap-3">
                {channelIcons.in_app}
                <div>
                  <p className="font-medium">In-App Notifications</p>
                  <p className="text-sm text-muted-foreground">
                    Receive notifications in the dashboard
                  </p>
                </div>
              </div>
              <Switch
                aria-label="In-app notifications"
                checked={form.watch("notify_in_app")}
                onCheckedChange={(v) => form.setValue("notify_in_app", v)}
              />
            </div>

            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="flex items-center gap-3">
                {channelIcons.email}
                <div>
                  <p className="font-medium">Email Notifications</p>
                  <p className="text-sm text-muted-foreground">
                    Get notified via email for important events
                  </p>
                </div>
              </div>
              <Switch
                aria-label="Email notifications"
                checked={form.watch("notify_email")}
                onCheckedChange={(v) => form.setValue("notify_email", v)}
              />
            </div>

            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="flex items-center gap-3">
                {channelIcons.slack}
                <div>
                  <p className="font-medium">Slack</p>
                  <p className="text-sm text-muted-foreground">
                    Send notifications to a Slack channel
                  </p>
                </div>
              </div>
              <Switch
                aria-label="Slack notifications"
                checked={form.watch("notify_slack")}
                onCheckedChange={(v) => form.setValue("notify_slack", v)}
              />
            </div>

            <div className="flex items-center justify-between rounded-lg border p-4">
              <div className="flex items-center gap-3">
                {channelIcons.teams}
                <div>
                  <p className="font-medium">Microsoft Teams</p>
                  <p className="text-sm text-muted-foreground">
                    Send notifications to a Teams channel
                  </p>
                </div>
              </div>
              <Switch
                aria-label="Microsoft Teams notifications"
                checked={form.watch("notify_teams")}
                onCheckedChange={(v) => form.setValue("notify_teams", v)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Webhook Configuration */}
        {(watchSlack || watchTeams) && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Webhook className="h-5 w-5" />
                Webhook URLs
              </CardTitle>
              <CardDescription>
                Provide webhook URLs for your enabled integrations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {watchSlack && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Slack Webhook URL
                  </label>
                  <Input
                    placeholder="https://hooks.slack.com/services/..."
                    {...form.register("slack_webhook_url")}
                  />
                  {form.formState.errors.slack_webhook_url && (
                    <p className="text-xs text-destructive">
                      {form.formState.errors.slack_webhook_url?.message}
                    </p>
                  )}
                </div>
              )}
              {watchTeams && (
                <div className="space-y-2">
                  <label className="text-sm font-medium">
                    Teams Webhook URL
                  </label>
                  <Input
                    placeholder="https://outlook.office.com/webhook/..."
                    {...form.register("teams_webhook_url")}
                  />
                  {form.formState.errors.teams_webhook_url && (
                    <p className="text-xs text-destructive">
                      {form.formState.errors.teams_webhook_url?.message}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        <div className="flex justify-end">
          <Button type="submit" disabled={updateSettings.isPending}>
            {updateSettings.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            Save Notification Settings
          </Button>
        </div>
      </form>
    </div>
  );
}
