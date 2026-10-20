"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  createConversationSchema,
  type CreateConversationFormData,
} from "@/lib/validations";
import { useCreateConversation } from "@/hooks/use-chat";
import { useSettings } from "@/hooks/use-settings";
import { DEFAULTS } from "@/lib/constants";
import { useModels } from "@/hooks/use-models";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Separator } from "@/components/ui/separator";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Loader2, Send, ChevronDown, Settings2 } from "lucide-react";
import { useRouter } from "next/navigation";

export default function NewChatPage() {
  const router = useRouter();
  const { data: settings } = useSettings();
  const { models, ready: modelsReady, providerOf, pick, defaults, searchAvailable, anyUsable } = useModels([
    settings?.preferred_generator_model,
    settings?.preferred_evaluator_model,
  ]);
  const createConversation = useCreateConversation();
  const [showAdvanced, setShowAdvanced] = useState(false);

  const form = useForm<CreateConversationFormData>({
    resolver: zodResolver(createConversationSchema),
    defaultValues: {
      prompt: "",
      title: "",
      generator_model: DEFAULTS.preferredGeneratorModel,
      generator_provider: "openai",
      evaluator_model: DEFAULTS.preferredEvaluatorModel,
      evaluator_provider: "openai",
      search_enabled: false,
      is_temporary: false,
      threshold: DEFAULTS.globalThreshold,
      max_iterations: DEFAULTS.maxIterations,
      timeout_seconds: DEFAULTS.timeoutSeconds,
    },
  });

  // defaultValues are captured on the first render, before the settings
  // query resolves; apply the user's preferences once they arrive without
  // clobbering anything already typed.
  // A preferred model whose provider has no key here falls back to the
  // server's default, so a fresh deployment works out of the box.
  useEffect(() => {
    if (!settings || !modelsReady) return;
    const gen = pick(settings.preferred_generator_model, defaults?.default_generator_model) ||
      DEFAULTS.preferredGeneratorModel;
    const evalModel = pick(settings.preferred_evaluator_model, defaults?.default_evaluator_model) ||
      DEFAULTS.preferredEvaluatorModel;
    form.reset(
      {
        ...form.getValues(),
        generator_model: gen,
        generator_provider: providerOf(gen),
        evaluator_model: evalModel,
        evaluator_provider: providerOf(evalModel),
        search_enabled: searchAvailable && settings.search_enabled,
        threshold: Number(settings.global_threshold),
        max_iterations: settings.max_iterations,
        timeout_seconds: settings.timeout_seconds,
      },
      { keepDirtyValues: true }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps -- helpers are rebuilt each render
  }, [settings, modelsReady, form]);

  const onSubmit = async (data: CreateConversationFormData) => {
    try {
      const result = await createConversation.mutateAsync(data);
      router.push(`/chat/${result.data.id}`);
    } catch {
      // onError in the mutation already shows a toast
    }
  };


  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">New Conversation</h1>
        <p className="text-muted-foreground">
          Configure your AI agents and enter your prompt
        </p>
      </div>

      <Form {...form}>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
          {/* Prompt Card */}
          <Card>
            <CardHeader>
              <CardTitle>Your Prompt</CardTitle>
              <CardDescription>
                What would you like the AI to generate?
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <FormField
                control={form.control}
                name="title"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Title (Optional)</FormLabel>
                    <FormControl>
                      <Input
                        placeholder="Auto-generated if left empty"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="prompt"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Prompt</FormLabel>
                    <FormControl>
                      <Textarea
                        placeholder="Enter your prompt here..."
                        rows={6}
                        className="resize-none"
                        {...field}
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </CardContent>
          </Card>

          {/* Model Selection */}
          <Card>
            <CardHeader>
              <CardTitle>AI Model Selection</CardTitle>
              <CardDescription>
                Choose your Generator and Evaluator models
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!anyUsable && (
                <div className="rounded-md border border-amber-300/60 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-500/30 dark:bg-amber-950/40 dark:text-amber-200">
                  This server has no AI provider key configured yet.{" "}
                  <Link href="/settings/api-keys" className="font-medium underline underline-offset-2">
                    Add your own API key
                  </Link>{" "}
                  to start generating.
                </div>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField
                  control={form.control}
                  name="generator_model"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Generator Model</FormLabel>
                      <Select
                        onValueChange={(val) => {
                          field.onChange(val);
                          form.setValue("generator_provider", providerOf(val));
                        }}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select model" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {models.map((model) => (
                            <SelectItem key={model.value} value={model.value} disabled={!model.usable}>
                              {model.label}
                              {!model.usable && (
                                <span className="ml-1 text-xs text-muted-foreground">· needs API key</span>
                              )}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="evaluator_model"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Evaluator Model</FormLabel>
                      <Select
                        onValueChange={(val) => {
                          field.onChange(val);
                          form.setValue("evaluator_provider", providerOf(val));
                        }}
                        value={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue placeholder="Select model" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {models.map((model) => (
                            <SelectItem key={model.value} value={model.value} disabled={!model.usable}>
                              {model.label}
                              {!model.usable && (
                                <span className="ml-1 text-xs text-muted-foreground">· needs API key</span>
                              )}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div className="flex flex-wrap items-center gap-x-6 gap-y-4">
                <FormField
                  control={form.control}
                  name="search_enabled"
                  render={({ field }) => (
                    <FormItem className="flex items-center gap-3">
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                          disabled={!searchAvailable}
                        />
                      </FormControl>
                      <div>
                        <FormLabel>Web Search</FormLabel>
                        <FormDescription className="text-xs">
                          {searchAvailable
                            ? "Enable Google search for context"
                            : "Not configured on this server"}
                        </FormDescription>
                      </div>
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="is_temporary"
                  render={({ field }) => (
                    <FormItem className="flex items-center gap-3">
                      <FormControl>
                        <Switch
                          checked={field.value}
                          onCheckedChange={field.onChange}
                        />
                      </FormControl>
                      <div>
                        <FormLabel>Temporary Chat</FormLabel>
                        <FormDescription className="text-xs">
                          Keep it out of your conversation history
                        </FormDescription>
                      </div>
                    </FormItem>
                  )}
                />
              </div>
            </CardContent>
          </Card>

          {/* Advanced Settings */}
          <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced}>
            <Card>
              <CollapsibleTrigger asChild>
                <CardHeader className="cursor-pointer">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Settings2 className="h-5 w-5" />
                      <CardTitle>Advanced Settings</CardTitle>
                    </div>
                    <ChevronDown
                      className={`h-5 w-5 transition-transform ${
                        showAdvanced ? "rotate-180" : ""
                      }`}
                    />
                  </div>
                  <CardDescription>
                    Override global settings for this conversation
                  </CardDescription>
                </CardHeader>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="space-y-6">
                  <Separator />
                  <FormField
                    control={form.control}
                    name="threshold"
                    render={({ field }) => (
                      <FormItem>
                        <div className="flex items-center justify-between">
                          <FormLabel>
                            Evaluation Threshold: {field.value}%
                          </FormLabel>
                        </div>
                        <FormControl>
                          <Slider
                            min={0}
                            max={100}
                            step={1}
                            value={[field.value ?? 75]}
                            onValueChange={(v) => field.onChange(v[0])}
                          />
                        </FormControl>
                        <FormDescription>
                          Minimum satisfaction score to accept a response
                        </FormDescription>
                      </FormItem>
                    )}
                  />

                  <div className="grid gap-4 sm:grid-cols-2">
                    <FormField
                      control={form.control}
                      name="max_iterations"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Max Iterations</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min={1}
                              max={50}
                              {...field}
                              onChange={(e) =>
                                field.onChange(Number(e.target.value))
                              }
                            />
                          </FormControl>
                          <FormDescription>
                            Max re-prompting attempts (1–50)
                          </FormDescription>
                        </FormItem>
                      )}
                    />
                    <FormField
                      control={form.control}
                      name="timeout_seconds"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Timeout (seconds)</FormLabel>
                          <FormControl>
                            <Input
                              type="number"
                              min={5}
                              max={600}
                              {...field}
                              onChange={(e) =>
                                field.onChange(Number(e.target.value))
                              }
                            />
                          </FormControl>
                          <FormDescription>
                            Per-agent response timeout (5–600s)
                          </FormDescription>
                        </FormItem>
                      )}
                    />
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>

          <Button
            type="submit"
            size="lg"
            className="w-full"
            disabled={createConversation.isPending}
          >
            {createConversation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Send className="mr-2 h-4 w-4" />
            )}
            Generate Response
          </Button>
        </form>
      </Form>
    </div>
  );
}
