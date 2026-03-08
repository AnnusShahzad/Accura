"use client";

import { useState } from "react";
import { useConversations, useDeleteConversation } from "@/hooks/use-chat";
import { useChatStore } from "@/stores/chat-store";
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
          <p className="text-muted-foreground">Your AI conversation history</p>
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
            <div key={i} className="rounded-lg border bg-card p-4 space-y-2">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          ))}
        </div>
      ) : conversations.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 rounded-lg border bg-card gap-4">
          <MessageSquare className="h-10 w-10 text-muted-foreground" />
          <div className="text-center">
            <p className="font-semibold">No conversations yet</p>
            <p className="text-sm text-muted-foreground">Start a new chat to begin generating AI responses</p>
          </div>
          <Button asChild size="sm">
            <Link href="/chat/new">
              <Plus className="mr-2 h-4 w-4" />
              Start First Chat
            </Link>
          </Button>
        </div>
      ) : (
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              className="group relative rounded-lg border bg-card transition-colors hover:border-primary/50"
            >
              {/* Single compact content block */}
              <div className="p-4 space-y-2">

                {/* Row 1: Badge + Delete */}
                <div className="flex items-center justify-between">
                  <Badge
                    variant={conv.status === "completed" ? "default" : "secondary"}
                    className="text-xs px-2 py-0"
                  >
                    {conv.status}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 -mr-1 opacity-0 group-hover:opacity-100 transition-opacity hover:bg-destructive/10"
                    onClick={(e) => {
                      e.preventDefault();
                      setConfirmId(conv.id);
                    }}
                  >
                    <Trash2 className="h-3 w-3 text-destructive" />
                  </Button>
                </div>

                {/* Row 2: Title — clickable */}
                <Link href={`/chat/${conv.id}`} className="block">
                  <p className="text-sm font-semibold line-clamp-2 leading-snug hover:text-primary transition-colors">
                    {conv.title}
                  </p>
                </Link>

                {/* Row 3: Date + Score */}
                <div className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{formatDate(conv.created_at)}</span>
                  {conv.best_score > 0 && (
                    <span className="text-xs font-medium text-primary">Score: {conv.best_score}%</span>
                  )}
                </div>

              </div>
            </div>
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
