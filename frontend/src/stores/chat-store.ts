import { create } from "zustand";
import type { ConversationListItem } from "@/types";

interface ChatState {
  conversations: ConversationListItem[];
  selectedConversationId: string | null;
  isCreating: boolean;
  setConversations: (conversations: ConversationListItem[]) => void;
  addConversation: (conversation: ConversationListItem) => void;
  removeConversation: (id: string) => void;
  selectConversation: (id: string | null) => void;
  setCreating: (isCreating: boolean) => void;
  updateConversation: (
    id: string,
    data: Partial<ConversationListItem>
  ) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversations: [],
  selectedConversationId: null,
  isCreating: false,

  setConversations: (conversations) => set({ conversations }),

  addConversation: (conversation) =>
    set((state) => ({
      conversations: [conversation, ...state.conversations],
    })),

  removeConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      selectedConversationId:
        state.selectedConversationId === id
          ? null
          : state.selectedConversationId,
    })),

  selectConversation: (id) => set({ selectedConversationId: id }),

  setCreating: (isCreating) => set({ isCreating }),

  updateConversation: (id, data) =>
    set((state) => ({
      conversations: state.conversations.map((c) =>
        c.id === id ? { ...c, ...data } : c
      ),
    })),
}));
