"use client";

import { use, useState } from "react";
import {
  useConversation,
  useRenameConversation,
  useAddAgent,
} from "@/hooks/use-chat";
import { useSettings } from "@/hooks/use-settings";
import { AI_MODELS } from "@/lib/constants";
import { formatDate, formatNumber } from "@/lib/utils";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
} from "lucide-react";

export default function ChatDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { data: conversation, isLoading } = useConversation(id);
  const { data: settings } = useSettings();
  const renameConversation = useRenameConversation();
  const addAgent = useAddAgent();

  const [renameTitle, setRenameTitle] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const [newAgentModel, setNewAgentModel] = useState("");
  const [newAgentProvider, setNewAgentProvider] = useState("");

  const hideScoring = settings?.hide_evaluator_scoring ?? false;

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
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
      renameConversation.mutate({
        id,
        data: { title: renameTitle.trim() },
      });
      setIsRenaming(false);
    }
  };

  const handleAddAgent = () => {
    if (newAgentModel && newAgentProvider) {
      addAgent.mutate({
        id,
        data: {
          model: newAgentModel,
          provider: newAgentProvider,
          role: "generator",
        },
      });
      setNewAgentModel("");
      setNewAgentProvider("");
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            {isRenaming ? (
              <div className="flex items-center gap-2">
                <Input
                  value={renameTitle}
                  onChange={(e) => setRenameTitle(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleRename()}
                  className="w-64"
                  autoFocus
                />
                <Button size="sm" onClick={handleRename}>
                  Save
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setIsRenaming(false)}
                >
                  Cancel
                </Button>
              </div>
            ) : (
              <>
                <h1 className="text-2xl font-bold">{conversation.title}</h1>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => {
                    setRenameTitle(conversation.title);
                    setIsRenaming(true);
                  }}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            Created {formatDate(conversation.created_at)}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant={
              conversation.status === "completed" ? "default" : "secondary"
            }
          >
            {conversation.status === "active" ? (
              <Loader2 className="mr-1 h-3 w-3 animate-spin" />
            ) : (
              <CheckCircle2 className="mr-1 h-3 w-3" />
            )}
            {conversation.status}
          </Badge>
          {conversation.search_enabled && (
            <Badge variant="outline">Search Enabled</Badge>
          )}
          {conversation.is_temporary && (
            <Badge variant="outline">Temporary</Badge>
          )}
        </div>
      </div>

      {/* Status / Processing Indicator */}
      {conversation.status === "active" && (
        <Card className="border-primary/50 bg-primary/5">
          <CardContent className="flex items-center gap-4 py-4">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <div className="flex-1">
              <p className="font-medium">Processing your prompt...</p>
              <p className="text-sm text-muted-foreground">
                AI agents are generating and evaluating responses. This page
                will update automatically.
              </p>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Prompt */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Your Prompt</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap">{conversation.prompt}</p>
        </CardContent>
      </Card>

      {/* Best Response */}
      {conversation.best_response && (
        <Card className="border-primary/50">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Brain className="h-5 w-5 text-primary" />
                Best Response
              </CardTitle>
              {!hideScoring && conversation.best_score > 0 && (
                <Badge variant="default" className="text-sm">
                  Score: {conversation.best_score}%
                </Badge>
              )}
            </div>
            {!hideScoring && (
              <Progress value={conversation.best_score} className="mt-2" />
            )}
          </CardHeader>
          <CardContent className="px-5 pb-6 sm:px-8 sm:pb-8">
            <ResponseViewer
              content={conversation.best_response}
              title="Best Response"
              previewHeight={360}
            />
          </CardContent>
        </Card>
      )}

      {/* Token Usage Summary */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <Coins className="h-8 w-8 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Input Tokens</p>
              <p className="text-xl font-bold">
                {formatNumber(conversation.tokens_input)}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <Coins className="h-8 w-8 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Output Tokens</p>
              <p className="text-xl font-bold">
                {formatNumber(conversation.tokens_output)}
              </p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 pt-6">
            <Bot className="h-8 w-8 text-muted-foreground" />
            <div>
              <p className="text-sm text-muted-foreground">Agents</p>
              <p className="text-xl font-bold">
                {conversation.agents?.length || 0}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs: Agents, Iterations */}
      <Tabs defaultValue="agents">
        <TabsList>
          <TabsTrigger value="agents">
            Agents ({conversation.agents?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="iterations">
            Iterations ({conversation.iterations?.length || 0})
          </TabsTrigger>
        </TabsList>

        {/* Agents */}
        <TabsContent value="agents" className="space-y-4">
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              AI models used in this conversation
            </p>
            <Dialog>
              <DialogTrigger asChild>
                <Button size="sm" variant="outline">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Agent
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Add New Agent</DialogTitle>
                  <DialogDescription>
                    Add another AI model to generate a response using the same
                    prompt. The evaluator will compare all responses.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
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
                      <SelectTrigger>
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
                </div>
                <DialogFooter>
                  <Button
                    onClick={handleAddAgent}
                    disabled={!newAgentModel || addAgent.isPending}
                  >
                    {addAgent.isPending && (
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    )}
                    Add Agent
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            {conversation.agents?.map((agent) => (
              <Card key={agent.id}>
                <CardContent className="flex items-center gap-4 pt-6">
                  <Bot className="h-10 w-10 text-primary" />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium capitalize">{agent.model}</p>
                      <Badge
                        variant={
                          agent.role === "generator" ? "default" : "secondary"
                        }
                      >
                        {agent.role}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground capitalize">
                      {agent.provider}
                      {agent.added_mid_chat && " • Added mid-chat"}
                    </p>
                  </div>
                  <Badge variant={agent.is_active ? "default" : "outline"}>
                    {agent.is_active ? "Active" : "Inactive"}
                  </Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Iterations */}
        <TabsContent value="iterations" className="space-y-4">
          <ScrollArea className="h-[600px]">
            {conversation.iterations?.length === 0 ? (
              <p className="py-8 text-center text-muted-foreground">
                No iterations yet
              </p>
            ) : (
              <div className="space-y-4">
                {conversation.iterations?.map((iter) => (
                  <Card key={iter.id}>
                    <CardHeader className="pb-3">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base">
                          Iteration #{iter.iteration_number}
                        </CardTitle>
                        <div className="flex items-center gap-2">
                          {iter.timed_out && (
                            <Badge variant="destructive">
                              <AlertTriangle className="mr-1 h-3 w-3" />
                              Timed Out
                            </Badge>
                          )}
                          {!hideScoring && (
                            <Badge
                              variant={
                                iter.score >= 75 ? "default" : "secondary"
                              }
                            >
                              {iter.score}%
                            </Badge>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-4 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Timer className="h-3 w-3" />
                          {iter.duration_ms}ms
                        </span>
                        <span className="flex items-center gap-1">
                          <Coins className="h-3 w-3" />
                          {formatNumber(
                            iter.tokens_input + iter.tokens_output
                          )}{" "}
                          tokens
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(iter.created_at)}
                        </span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {iter.rephrased_prompt && (
                        <div>
                          <p className="text-xs font-medium text-muted-foreground">
                            Rephrased Prompt:
                          </p>
                          <p className="mt-1 text-sm">{iter.rephrased_prompt}</p>
                        </div>
                      )}
                      <Separator />
                      <div>
                        <p className="text-xs font-medium text-muted-foreground">
                          Response:
                        </p>
                        <ResponseViewer
                          content={iter.response}
                          title={`Iteration #${iter.iteration_number} Response`}
                          className="mt-2"
                          previewHeight={280}
                        />
                      </div>
                      {!hideScoring && iter.evaluation_reasoning && (
                        <>
                          <Separator />
                          <div>
                            <p className="text-xs font-medium text-muted-foreground">
                              Evaluation:
                            </p>
                            <p className="mt-1 text-sm text-muted-foreground">
                              {iter.evaluation_reasoning}
                            </p>
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
      </Tabs>
    </div>
  );
}
