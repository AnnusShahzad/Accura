"use client";

import { use, useEffect, useRef, useState } from "react";
import {
  useConversation,
  useRenameConversation,
  useAddAgent,
  useConversationMessages,
  useSendFollowUpMessage,
} from "@/hooks/use-chat";
import { useSettings } from "@/hooks/use-settings";
import { AI_MODELS } from "@/lib/constants";
import { formatDate, formatNumber, cn } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ResponseViewer } from "@/components/ui/response-viewer";
import {
  Loader2,
  Pencil,
  Plus,
  Bot,
  Brain,
  Clock,
  Coins,
  CheckCircle2,
  AlertTriangle,
  Timer,
  Send,
  Search,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  User,
} from "lucide-react";
import type { ChatMessage } from "@/types";

// ─── Thinking Bubble ──────────────────────────────────────────────────────────
function ThinkingBubble({
  currentIteration,
  maxIterations,
  currentBestScore,
}: {
  currentIteration?: number;
  maxIterations?: number;
  currentBestScore?: number;
}) {
  return (
    <div className="flex items-end gap-3 justify-start">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 border border-primary/20">
        <Bot className="h-4 w-4 text-primary" />
      </div>
      <div className="max-w-[70%] rounded-2xl rounded-bl-sm border bg-card px-4 py-3 shadow-sm">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
          <span className="font-medium">Thinking…</span>
          {currentIteration !== undefined && maxIterations !== undefined && (
            <Badge variant="outline" className="text-xs px-1.5 py-0 h-5">
              {currentIteration}/{maxIterations} iterations
            </Badge>
          )}
          {currentBestScore !== undefined && currentBestScore > 0 && (
            <Badge variant="secondary" className="text-xs px-1.5 py-0 h-5">
              Best: {currentBestScore}%
            </Badge>
          )}
        </div>
        <div className="mt-2 flex gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:0ms]" />
          <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:150ms]" />
          <span className="h-1.5 w-1.5 rounded-full bg-primary/60 animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}

// ─── Message Bubble ───────────────────────────────────────────────────────────
function MessageBubble({
  message,
  hideScoring,
  searchEnabled,
}: {
  message: ChatMessage;
  hideScoring: boolean;
  searchEnabled: boolean;
}) {
  const isUser = message.role === "user";
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={cn("flex items-end gap-3", isUser ? "flex-row-reverse" : "flex-row")}>
      {/* Avatar */}
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
          isUser
            ? "bg-primary/10 border-primary/20"
            : "bg-secondary border-border"
        )}
      >
        {isUser ? (
          <User className="h-4 w-4 text-primary" />
        ) : (
          <Brain className="h-4 w-4 text-foreground" />
        )}
      </div>

      {/* Bubble */}
      <div
        className={cn(
          "max-w-[72%] space-y-1.5 rounded-2xl border px-4 py-3 shadow-sm",
          isUser
            ? "rounded-br-sm bg-primary text-primary-foreground border-primary"
            : "rounded-bl-sm bg-card border-border"
        )}
      >
        {/* Header meta for assistant messages */}
        {!isUser && (
          <div className="flex flex-wrap items-center gap-1.5 mb-2">
            {!hideScoring && message.score != null && message.score > 0 && (
              <Badge
                variant={message.score >= 75 ? "default" : "secondary"}
                className="text-xs h-5 px-1.5 py-0"
              >
                Score: {Number(message.score).toFixed(1)}%
              </Badge>
            )}
            {searchEnabled && (
              <Badge variant="outline" className="text-xs h-5 px-1.5 py-0">
                <Search className="h-3 w-3 mr-1" />
                Web Search
              </Badge>
            )}
          </div>
        )}

        {/* Content */}
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <div className={cn("text-sm overflow-hidden", !expanded && "max-h-64")}>
            <ResponseViewer
              content={message.content}
              title="Response"
              previewHeight={expanded ? undefined : 200}
            />
          </div>
        )}

        {/* Expand button for long assistant responses */}
        {!isUser && message.content && message.content.length > 500 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground mt-1 transition-colors"
          >
            <ChevronDown
              className={cn("h-3 w-3 transition-transform", expanded && "rotate-180")}
            />
            {expanded ? "Collapse" : "Expand full response"}
          </button>
        )}

        {/* Timestamp */}
        <p className={cn("text-xs mt-1", isUser ? "text-primary-foreground/60 text-right" : "text-muted-foreground")}>
          {formatDate(message.created_at)}
        </p>
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
export default function ChatDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: conversation, isLoading } = useConversation(id);
  const { data: messages, isLoading: messagesLoading } = useConversationMessages(id);
  const { data: settings } = useSettings();
  const renameConversation = useRenameConversation();
  const addAgent = useAddAgent();
  const sendFollowUp = useSendFollowUpMessage();

  const [renameTitle, setRenameTitle] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [newAgentModel, setNewAgentModel] = useState("");
  const [newAgentProvider, setNewAgentProvider] = useState("");
  const [followUpText, setFollowUpText] = useState("");
  const [showDetails, setShowDetails] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  const hideScoring = settings?.hide_evaluator_scoring ?? false;
  const isActive = conversation?.status === "active";

  // Auto-scroll to bottom whenever messages change or status becomes active
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, isActive]);

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-120px)] flex-col gap-4">
        <Skeleton className="h-10 w-1/3" />
        <Skeleton className="flex-1 w-full" />
        <Skeleton className="h-14 w-full" />
      </div>
    );
  }

  if (!conversation) {
    return (
      <div className="flex flex-col items-center py-16">
        <p className="text-muted-foreground">Conversation not found</p>
      </div>
    );
  }

  const handleRename = () => {
    if (renameTitle.trim()) {
      renameConversation.mutate({ id, data: { title: renameTitle.trim() } });
      setIsRenaming(false);
    }
  };

  const handleAddAgent = () => {
    if (newAgentModel && newAgentProvider) {
      addAgent.mutate({ id, data: { model: newAgentModel, provider: newAgentProvider, role: "generator" } });
      setNewAgentModel("");
      setNewAgentProvider("");
    }
  };

  const handleSendFollowUp = () => {
    const text = followUpText.trim();
    if (!text || sendFollowUp.isPending) return;
    setFollowUpText("");
    sendFollowUp.mutate({ id, prompt: text });
  };

  // Build the displayed messages: if the API returned messages use those,
  // otherwise fall back to constructing them from conversation fields
  const displayMessages: ChatMessage[] = messages && messages.length > 0
    ? messages.filter((m) => m.role === "user" || m.role === "assistant")
    : [
        ...(conversation.prompt
          ? [{
              id: "fallback-user",
              conversation_id: id,
              role: "user" as const,
              content: conversation.prompt,
              created_at: conversation.created_at,
            }]
          : []),
        ...(conversation.best_response
          ? [{
              id: "fallback-assistant",
              conversation_id: id,
              role: "assistant" as const,
              content: conversation.best_response,
              score: conversation.best_score,
              created_at: conversation.created_at,
            }]
          : []),
      ];

  const meta = conversation.metadata;

  return (
    <div className="flex h-[calc(100vh-100px)] flex-col gap-0">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between pb-3 border-b shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          {isRenaming ? (
            <div className="flex items-center gap-2">
              <Input
                value={renameTitle}
                onChange={(e) => setRenameTitle(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleRename()}
                className="w-56 h-8"
                autoFocus
              />
              <Button size="sm" className="h-8" onClick={handleRename}>Save</Button>
              <Button size="sm" variant="ghost" className="h-8" onClick={() => setIsRenaming(false)}>Cancel</Button>
            </div>
          ) : (
            <>
              <h1 className="text-lg font-bold truncate max-w-xs">{conversation.title}</h1>
              <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={() => { setRenameTitle(conversation.title); setIsRenaming(true); }}>
                <Pencil className="h-3.5 w-3.5" />
              </Button>
            </>
          )}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {isActive && (
            <Badge variant="secondary" className="gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              Processing
            </Badge>
          )}
          {conversation.status === "completed" && (
            <Badge variant="default" className="gap-1">
              <CheckCircle2 className="h-3 w-3" />
              {!hideScoring ? `${conversation.best_score}%` : "Done"}
            </Badge>
          )}
          {conversation.search_enabled && (
            <Badge variant="outline" className="gap-1 text-xs">
              <Search className="h-3 w-3" />
              Search
            </Badge>
          )}
          {conversation.is_temporary && (
            <Badge variant="outline" className="text-xs">Temporary</Badge>
          )}

          {/* Add Agent */}
          <Dialog>
            <DialogTrigger asChild>
              <Button size="sm" variant="outline" className="h-7 text-xs gap-1">
                <Plus className="h-3 w-3" />
                Agent
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add New Agent</DialogTitle>
                <DialogDescription>
                  Add another AI model to generate an alternative response.
                </DialogDescription>
              </DialogHeader>
              <div>
                <label className="text-sm font-medium">Model</label>
                <Select
                  value={newAgentModel}
                  onValueChange={(val) => {
                    setNewAgentModel(val);
                    const model = AI_MODELS.find((m) => m.value === val);
                    if (model) setNewAgentProvider(model.provider);
                  }}
                >
                  <SelectTrigger className="mt-1">
                    <SelectValue placeholder="Select model" />
                  </SelectTrigger>
                  <SelectContent>
                    {AI_MODELS.map((model) => (
                      <SelectItem key={model.value} value={model.value}>
                        {model.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <DialogFooter>
                <Button onClick={handleAddAgent} disabled={!newAgentModel || addAgent.isPending}>
                  {addAgent.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  Add Agent
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* ── Score Progress (only while active) ─────────────────────────────── */}
      {!hideScoring && isActive && meta?.current_best_score !== undefined && meta.current_best_score > 0 && (
        <div className="py-2 px-1 shrink-0">
          <div className="flex justify-between text-xs text-muted-foreground mb-1">
            <span>Quality progress</span>
            <span>{meta.current_best_score}% / {conversation.threshold ?? 75}% threshold</span>
          </div>
          <Progress value={meta.current_best_score} className="h-1.5" />
        </div>
      )}

      {/* ── Chat Messages ───────────────────────────────────────────────────── */}
      <ScrollArea className="flex-1 min-h-0" ref={scrollRef as any}>
        <div className="flex flex-col gap-5 py-4 px-1">
          {messagesLoading && displayMessages.length === 0 ? (
            <div className="space-y-4">
              <Skeleton className="h-16 w-2/3" />
              <Skeleton className="h-24 w-3/4 ml-auto" />
            </div>
          ) : (
            displayMessages.map((msg) => (
              <MessageBubble
                key={msg.id}
                message={msg}
                hideScoring={hideScoring}
                searchEnabled={conversation.search_enabled}
              />
            ))
          )}

          {/* Thinking bubble when processing */}
          {isActive && (
            <ThinkingBubble
              currentIteration={meta?.current_iteration}
              maxIterations={meta?.max_iterations}
              currentBestScore={meta?.current_best_score}
            />
          )}
        </div>
      </ScrollArea>

      {/* ── Follow-up Input ─────────────────────────────────────────────────── */}
      <div className="shrink-0 border-t pt-3">
        {isActive ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground px-1 py-2">
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            AI is generating a response… input unlocks when complete.
          </div>
        ) : (
          <div className="flex items-end gap-2">
            <Textarea
              value={followUpText}
              onChange={(e) => setFollowUpText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendFollowUp();
                }
              }}
              placeholder="Send a follow-up message… (Enter to send, Shift+Enter for newline)"
              rows={1}
              className="flex-1 resize-none min-h-[40px] max-h-[120px]"
              disabled={sendFollowUp.isPending}
            />
            <Button
              size="icon"
              onClick={handleSendFollowUp}
              disabled={!followUpText.trim() || sendFollowUp.isPending}
              className="shrink-0"
            >
              {sendFollowUp.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        )}
      </div>

      {/* ── Details Panel: Agents, Iterations, Tokens ──────────────────────── */}
      <Collapsible
        open={showDetails}
        onOpenChange={setShowDetails}
        className="shrink-0 border-t mt-3"
      >
        <div className="flex items-center justify-center py-1">
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="h-6 text-xs text-muted-foreground hover:text-foreground">
              {showDetails ? "Hide Details" : "Show Details"}
              <ChevronDown className={cn("ml-1 h-3 w-3 transition-transform", showDetails && "rotate-180")} />
            </Button>
          </CollapsibleTrigger>
        </div>
        <CollapsibleContent>
          <div className="pt-2 pb-1">
            <Tabs defaultValue="iterations">
              <TabsList className="h-7 w-full justify-start overflow-auto">
                <TabsTrigger value="iterations" className="text-xs h-6">
                  Iterations ({conversation.iterations?.length ?? 0})
                </TabsTrigger>
                <TabsTrigger value="agents" className="text-xs h-6">
                  Agents ({conversation.agents?.length ?? 0})
                </TabsTrigger>
                <TabsTrigger value="tokens" className="text-xs h-6">
                  Tokens
                </TabsTrigger>
              </TabsList>

              {/* Iterations */}
              <TabsContent value="iterations" className="mt-3">
                <ScrollArea className="h-48">
                  {(conversation.iterations?.length ?? 0) === 0 ? (
                    <p className="py-8 text-center text-sm text-muted-foreground">No iterations yet</p>
                  ) : (
                    <div className="space-y-3">
                      {conversation.iterations?.map((iter) => (
                        <Card key={iter.id}>
                          <CardHeader className="pb-2 pt-3 px-4">
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-sm">Iteration #{iter.iteration_number}</CardTitle>
                              <div className="flex items-center gap-1.5">
                                {iter.timed_out && (
                                  <Badge variant="destructive" className="text-xs h-5">
                                    <AlertTriangle className="mr-1 h-3 w-3" />
                                    Timed Out
                                  </Badge>
                                )}
                                {!hideScoring && (
                                  <Badge variant={iter.score >= 75 ? "default" : "secondary"} className="text-xs h-5">
                                    {iter.score}%
                                  </Badge>
                                )}
                              </div>
                            </div>
                            <div className="flex gap-3 text-xs text-muted-foreground">
                              <span className="flex items-center gap-1"><Timer className="h-3 w-3" />{iter.duration_ms}ms</span>
                              <span className="flex items-center gap-1"><Coins className="h-3 w-3" />{formatNumber(iter.tokens_input + iter.tokens_output)} tokens</span>
                              <span className="flex items-center gap-1"><Clock className="h-3 w-3" />{formatDate(iter.created_at)}</span>
                            </div>
                          </CardHeader>
                          <CardContent className="px-4 pb-3 space-y-2">
                            {iter.rephrased_prompt && (
                              <div>
                                <p className="text-xs font-medium text-muted-foreground">Rephrased Prompt:</p>
                                <p className="mt-0.5 text-xs">{iter.rephrased_prompt}</p>
                              </div>
                            )}
                            <Separator />
                            <div>
                              <p className="text-xs font-medium text-muted-foreground">Response:</p>
                              <ResponseViewer content={iter.response} title={`Iteration #${iter.iteration_number}`} className="mt-1" previewHeight={200} />
                            </div>
                            {!hideScoring && iter.evaluation_reasoning && (
                              <>
                                <Separator />
                                <div>
                                  <p className="text-xs font-medium text-muted-foreground">Evaluation:</p>
                                  <p className="mt-0.5 text-xs text-muted-foreground">{iter.evaluation_reasoning}</p>
                                </div>
                              </>
                            )}
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </ScrollArea>
              </TabsContent>

              {/* Agents */}
              <TabsContent value="agents" className="mt-3">
                <ScrollArea className="h-48">
                <div className="grid gap-2 sm:grid-cols-2">
                  {conversation.agents?.map((agent) => (
                    <Card key={agent.id}>
                      <CardContent className="flex items-center gap-3 py-3 px-4">
                        <Bot className="h-8 w-8 text-primary shrink-0" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <p className="font-medium text-sm truncate">{agent.model}</p>
                            <Badge variant={agent.role === "generator" ? "default" : "secondary"} className="text-xs h-5 px-1.5">
                              {agent.role}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground capitalize">
                            {agent.provider}{agent.added_mid_chat && " • Added mid-chat"}
                          </p>
                        </div>
                        <Badge variant={agent.is_active ? "default" : "outline"} className="text-xs shrink-0">
                          {agent.is_active ? "Active" : "Inactive"}
                        </Badge>
                      </CardContent>
                    </Card>
                  ))}
                </div>
                </ScrollArea>
              </TabsContent>

              {/* Token Usage */}
              <TabsContent value="tokens" className="mt-3">
                <div className="grid gap-3 sm:grid-cols-3">
                  <Card>
                    <CardContent className="flex items-center gap-3 pt-4 pb-4">
                      <Coins className="h-7 w-7 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">Input Tokens</p>
                        <p className="text-lg font-bold">{formatNumber(conversation.tokens_input)}</p>
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="flex items-center gap-3 pt-4 pb-4">
                      <Coins className="h-7 w-7 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">Output Tokens</p>
                        <p className="text-lg font-bold">{formatNumber(conversation.tokens_output)}</p>
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="flex items-center gap-3 pt-4 pb-4">
                      <Bot className="h-7 w-7 text-muted-foreground" />
                      <div>
                        <p className="text-xs text-muted-foreground">Agents</p>
                        <p className="text-lg font-bold">{conversation.agents?.length ?? 0}</p>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}
