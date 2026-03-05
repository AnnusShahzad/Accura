"use client";

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
import { Plus, MessageSquare, Trash2 } from "lucide-react";
import Link from "next/link";
import { formatDate } from "@/lib/utils";

export default function ChatListPage() {
  const { data, isLoading } = useConversations();
  const { conversations } = useChatStore();
  const deleteConversation = useDeleteConversation();

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
              className="group relative transition-colors hover:border-primary/50"
            >
              <Link href={`/chat/${conv.id}`}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-base line-clamp-2">
                      {conv.title}
                    </CardTitle>
                    <Badge
                      variant={
                        conv.status === "completed" ? "default" : "secondary"
                      }
                    >
                      {conv.status}
                    </Badge>
                  </div>
                  <CardDescription className="flex items-center justify-between">
                    <span>{formatDate(conv.created_at)}</span>
                    {conv.best_score > 0 && (
                      <span className="font-medium text-primary">
                        Score: {conv.best_score}%
                      </span>
                    )}
                  </CardDescription>
                </CardHeader>
              </Link>
              <Button
                variant="ghost"
                size="icon"
                className="absolute right-2 top-2 opacity-0 group-hover:opacity-100"
                onClick={(e) => {
                  e.preventDefault();
                  deleteConversation.mutate(conv.id);
                }}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
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
    </div>
  );
}
