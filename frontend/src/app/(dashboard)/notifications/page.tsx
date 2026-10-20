"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "@/lib/api-client";
import { formatDate } from "@/lib/utils";
import type { Notification } from "@/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Bell,
  CheckCheck,
  Info,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";

const channelIcons: Record<string, React.ReactNode> = {
  in_app: <Info className="h-5 w-5 text-blue-500" />,
  email: <CheckCircle className="h-5 w-5 text-green-500" />,
  slack: <AlertTriangle className="h-5 w-5 text-yellow-500" />,
  teams: <XCircle className="h-5 w-5 text-purple-500" />,
};

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const router = useRouter();

  const remove = useMutation({
    mutationFn: (id: string) => notificationsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
    onError: (e: Error) => toast.error(e.message || "Failed to delete notification"),
  });

  const { data: notifications, isLoading } = useQuery({
    queryKey: ["notifications"],
    queryFn: async () => {
      const res = await notificationsApi.list();
      return res.data as Notification[];
    },
  });

  const markRead = useMutation({
    mutationFn: (id: string) => notificationsApi.markRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAllRead = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
      toast.success("All notifications marked as read");
    },
  });

  const unreadCount =
    notifications?.filter((n) => !n.is_read).length || 0;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Notifications</h1>
          <p className="text-muted-foreground">
            {unreadCount > 0
              ? `${unreadCount} unread notification${unreadCount > 1 ? "s" : ""}`
              : "You're all caught up"}
          </p>
        </div>
        {unreadCount > 0 && (
          <Button
            variant="outline"
            onClick={() => markAllRead.mutate()}
            disabled={markAllRead.isPending}
          >
            <CheckCheck className="mr-2 h-4 w-4" />
            Mark All Read
          </Button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full" />
          ))}
        </div>
      ) : !notifications || notifications.length === 0 ? (
        <Card className="py-16 text-center">
          <CardContent>
            <Bell className="mx-auto h-12 w-12 text-muted-foreground" />
            <CardTitle className="mt-4">No Notifications</CardTitle>
            <CardDescription className="mt-2">
              Notifications will appear here when there&apos;s activity on your account
            </CardDescription>
          </CardContent>
        </Card>
      ) : (
        <div>
          <div className="space-y-2">
            {notifications.map((notification) => (
              <Card
                key={notification.id}
                className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                  !notification.is_read ? "border-primary/30 bg-primary/5" : ""
                }`}
                onClick={() => {
                  if (!notification.is_read) {
                    markRead.mutate(notification.id);
                  }
                  const conversationId = notification.metadata?.conversation_id;
                  if (typeof conversationId === "string") {
                    router.push(`/chat/${conversationId}`);
                  }
                }}
              >
                <CardContent className="flex items-start gap-4 py-4">
                  <div className="mt-0.5">
                    {channelIcons[notification.channel] || (
                      <Bell className="h-5 w-5 text-muted-foreground" />
                    )}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium">{notification.title}</p>
                      {!notification.is_read && (
                        <Badge className="h-2 w-2 rounded-full bg-primary p-0" />
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {notification.body}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {formatDate(notification.created_at)}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-8 w-8 shrink-0"
                    aria-label="Delete notification"
                    onClick={(e) => {
                      e.stopPropagation();
                      remove.mutate(notification.id);
                    }}
                  >
                    <Trash2 className="h-4 w-4 text-muted-foreground" />
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
