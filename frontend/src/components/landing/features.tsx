import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Zap,
  Brain,
  Repeat,
  Server,
  Search,
  Shield,
} from "lucide-react";

const features = [
  {
    icon: Brain,
    title: "Multi-Agent Generation",
    description:
      "Run multiple AI models simultaneously — GPT 5.2, GPT 5.1, DeepSeek V3 — and let them compete to give you the best response.",
  },
  {
    icon: Zap,
    title: "Intelligent Evaluation",
    description:
      "An independent Evaluator agent scores every response on quality, relevance, and accuracy against your custom threshold.",
  },
  {
    icon: Repeat,
    title: "Auto Re-Prompting",
    description:
      "If the score falls below your threshold, Accura automatically rephrases your prompt and re-generates until quality is met.",
  },
  {
    icon: Server,
    title: "MCP Server Integration",
    description:
      "Connect your own MCP (Model Context Protocol) servers for tool-augmented AI generation with real-time data.",
  },
  {
    icon: Search,
    title: "Web Search Augmented",
    description:
      "Enable Google search integration so the AI can find and incorporate real-time information into its responses.",
  },
  {
    icon: Shield,
    title: "Bring Your Own Keys",
    description:
      "Use your own OpenAI-compatible API keys for unlimited generation with zero platform limitations.",
  },
];

export function Features() {
  return (
    <section className="py-24 sm:py-32" id="features">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Built for Quality, Designed for Scale
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Everything you need to get consistently excellent AI responses.
          </p>
        </div>
        <div className="mx-auto mt-16 grid max-w-5xl gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => (
            <Card key={feature.title} className="border-2 transition-colors hover:border-primary/50">
              <CardHeader>
                <feature.icon className="mb-2 h-8 w-8 text-primary" />
                <CardTitle className="text-lg">{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
