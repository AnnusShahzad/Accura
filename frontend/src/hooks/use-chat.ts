"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError, chatApi } from "@/lib/api-client";
import { useChatStore } from "@/stores/chat-store";
import type {
  CreateConversationRequest,
  AddAgentRequest,
  RenameConversationRequest,
} from "@/types";
import { toast } from "sonner";

export function useConversations(page = 1) {
  const { setConversations } = useChatStore();

  return useQuery({
    queryKey: ["conversations", page],
    queryFn: async () => {
      const res = await chatApi.list(page);
      setConversations(res.data.items);
      return res.data;
    },
    // Keep list badges fresh while something is still generating
    refetchInterval: (query) =>
      query.state.data?.items.some((c) => c.status === "active") ? 5000 : false,
  });
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: ["conversation", id],
    queryFn: async () => {
      const res = await chatApi.get(id);
      return res.data;
    },
    enabled: !!id,
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 1,
    refetchInterval: (query) => {
      const data = query.state.data;
      return data?.status === "active" ? 2000 : false;
    },
  });
}

export function useCreateConversation() {
  const queryClient = useQueryClient();
  const { addConversation, selectConversation } = useChatStore();

  return useMutation({
    mutationFn: (data: CreateConversationRequest) => chatApi.create(data),
    onSuccess: (res) => {
      addConversation({
        id: res.data.id,
        title: res.data.title,
        status: res.data.status,
        best_score: res.data.best_score,
        created_at: res.data.created_at,
      });
      selectConversation(res.data.id);
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to create conversation");
    },
  });
}

export function useRenameConversation() {
  const queryClient = useQueryClient();
  const { updateConversation } = useChatStore();

  return useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: RenameConversationRequest;
    }) => chatApi.rename(id, data),
    onSuccess: (_, { id, data }) => {
      updateConversation(id, { title: data.title });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.invalidateQueries({ queryKey: ["conversation", id] });
      toast.success("Conversation renamed");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to rename");
    },
  });
}

export function useAddAgent() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: AddAgentRequest }) =>
      chatApi.addAgent(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["conversation", id] });
      queryClient.invalidateQueries({ queryKey: ["conversation-messages", id] });
      toast.success("Agent added – generating an alternative response");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to add agent");
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  const { removeConversation } = useChatStore();

  return useMutation({
    mutationFn: (id: string) => chatApi.delete(id),
    onSuccess: (_, id) => {
      removeConversation(id);
      queryClient.removeQueries({ queryKey: ["conversation", id] });
      queryClient.removeQueries({ queryKey: ["conversation-messages", id] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      toast.success("Conversation deleted");
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to delete");
    },
  });
}

export function useConversationIterations(id: string) {
  return useQuery({
    queryKey: ["conversation-iterations", id],
    queryFn: async () => {
      const res = await chatApi.getIterations(id);
      return res.data;
    },
    enabled: !!id,
  });
}

export function useConversationMessages(id: string, isActive = false) {
  return useQuery({
    queryKey: ["conversation-messages", id],
    queryFn: async () => {
      const res = await chatApi.getMessages(id);
      return res.data;
    },
    enabled: !!id,
    // Poll only while a response is being generated
    refetchInterval: isActive ? 2000 : false,
    staleTime: 0,
  });
}

export function useRetryConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => chatApi.retry(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ["conversation", id] });
      queryClient.invalidateQueries({ queryKey: ["conversation-messages", id] });
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to retry");
    },
  });
}

export function useSendFollowUpMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, prompt, search_enabled }: { id: string; prompt: string; search_enabled?: boolean }) =>
      chatApi.sendMessage(id, { prompt, search_enabled }),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ["conversation", id] });
      queryClient.invalidateQueries({ queryKey: ["conversation-messages", id] });
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to send message");
    },
  });
}
