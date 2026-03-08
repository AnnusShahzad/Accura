"use client";

import { useState } from "react";
import { useConversations, useDeleteConversation } from "@/hooks/use-chat";
import { useChatStore } from "@/stores/chat-store";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
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
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import Link from "next/link";
import { formatDate } from "@/lib/utils";

export default function ChatListPage() {
  const { data, isLoading } = useConversations();
  const { conversations } = useChatStore();
  const deleteConversation = useDeleteConversation();
  const [confirmId, setConfirmId] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Conversations</h1>
          <p className="text-muted-foreground">
            Your AI conversation history
          </p>
        </div>
        <Button asChild>
          <Link href="/chat/new">
            <Plus className="mr-2 h-4 w-4" />
            New Chat
          </Link>
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-3/4" />
                <Skeleton className="mt-2 h-4 w-1/2" />
              </CardHeader>
            </Card>
          ))}
        </div>
      ) : conversations.length === 0 ? (
        <Card className="flex flex-col items-center justify-center py-16">
          <MessageSquare className="h-12 w-12 text-muted-foreground" />
          <CardHeader className="text-center">
            <CardTitle>No conversations yet</CardTitle>
            <CardDescription>
              Start a new chat to begin generating AI responses
            </CardDescription>
          </CardHeader>
          <Button asChild>
            <Link href="/chat/new">
              <Plus className="mr-2 h-4 w-4" />
              Start First Chat
            </Link>
          </Button>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {conversations.map((conv) => (
            <Card
              key={conv.id}
              className="group flex flex-col transition-colors hover:border-primary/50"
            >
              {/* Top row: Badge + Delete button */}
              <div className="flex items-center justify-between px-6 pt-5">
                <Badge
                  variant={
                    conv.status === "completed" ? "default" : "secondary"
                  }
                >
                  {conv.status}
                </Badge>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive/10"
                  onClick={(e) => {
                    e.preventDefault();
                    setConfirmId(conv.id);
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5 text-destructive" />
                </Button>
              </div>

              {/* Title + meta — clickable */}
              <Link href={`/chat/${conv.id}`} className="flex-1">
                <CardHeader className="pt-3">
                  <CardTitle className="text-base line-clamp-2">
                    {conv.title}
                  </CardTitle>
                  <CardDescription className="flex items-center justify-between pt-1">
                    <span>{formatDate(conv.created_at)}</span>
                    {conv.best_score > 0 && (
                      <span className="font-medium text-primary">
                        Score: {conv.best_score}%
                      </span>
                    )}
                  </CardDescription>
                </CardHeader>
              </Link>
            </Card>
          ))}
        </div>
      )}

      {data && data.pages > 1 && (
        <div className="flex justify-center">
          <p className="text-sm text-muted-foreground">
            Showing {data.items.length} of {data.total} conversations
          </p>
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={!!confirmId} onOpenChange={() => setConfirmId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this conversation?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The conversation will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => {
                if (confirmId) {
                  deleteConversation.mutate(confirmId);
                  setConfirmId(null);
                }
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}