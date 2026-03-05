import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, X } from "lucide-react";
import Link from "next/link";

const plans = [
  {
    name: "Basic",
    price: "Free",
    priceYearly: "Free",
    description: "Get started with essential AI capabilities",
    features: [
      { text: "10 requests per minute", included: true },
      { text: "100 requests per day", included: true },
      { text: "4,096 max tokens per request", included: true },
      { text: "Community support", included: true },
      { text: "Standard AI models", included: true },
      { text: "BYOK (Bring Your Own Keys)", included: false },
      { text: "MCP Server integration", included: false },
      { text: "Priority support", included: false },
    ],
    cta: "Get Started",
    href: "/register",
    popular: false,
  },
  {
    name: "Pro",
    price: "$29.99",
    priceYearly: "$299.99",
    description: "For power users who need more capacity and features",
    features: [
      { text: "60 requests per minute", included: true },
      { text: "1,000 requests per day", included: true },
      { text: "16,384 max tokens per request", included: true },
      { text: "Priority support", included: true },
      { text: "All AI models", included: true },
      { text: "BYOK (Bring Your Own Keys)", included: true },
      { text: "MCP Server integration", included: true },
      { text: "Advanced analytics", included: true },
    ],
    cta: "Upgrade to Pro",
    href: "/register",
    popular: true,
  },
  {
    name: "Business",
    price: "$99.99",
    priceYearly: "$999.99",
    description: "Custom solutions for organizations and teams",
    features: [
      { text: "200 requests per minute", included: true },
      { text: "10,000 requests per day", included: true },
      { text: "32,768 max tokens per request", included: true },
      { text: "Dedicated support", included: true },
      { text: "All AI models", included: true },
      { text: "BYOK (Bring Your Own Keys)", included: true },
      { text: "MCP Server integration", included: true },
      { text: "Custom branding & SSO", included: true },
    ],
    cta: "Contact Us",
    href: "#contact",
    popular: false,
  },
];

export function Pricing() {
  return (
    <section className="py-24 sm:py-32" id="pricing">
      <div className="mx-auto max-w-7xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
            Simple, Transparent Pricing
          </h2>
          <p className="mt-4 text-lg text-muted-foreground">
            Choose the plan that fits your needs. Upgrade anytime.
          </p>
        </div>
        <div className="mx-auto mt-16 grid max-w-5xl gap-8 lg:grid-cols-3">
          {plans.map((plan) => (
            <Card
              key={plan.name}
              className={`relative flex flex-col ${
                plan.popular ? "border-primary shadow-lg" : ""
              }`}
            >
              {plan.popular && (
                <Badge className="absolute -top-3 left-1/2 -translate-x-1/2">
                  Most Popular
                </Badge>
              )}
              <CardHeader>
                <CardTitle className="text-xl">{plan.name}</CardTitle>
                <div className="mt-2">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  {plan.price !== "Free" && (
                    <span className="text-muted-foreground">/month</span>
                  )}
                </div>
                <CardDescription className="mt-2">
                  {plan.description}
                </CardDescription>
              </CardHeader>
              <CardContent className="flex-1">
                <ul className="space-y-3">
                  {plan.features.map((feature) => (
                    <li key={feature.text} className="flex items-start gap-3">
                      {feature.included ? (
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                      ) : (
                        <X className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground/40" />
                      )}
                      <span
                        className={
                          feature.included ? "" : "text-muted-foreground/60"
                        }
                      >
                        {feature.text}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
              <CardFooter>
                <Button
                  variant={plan.popular ? "default" : "outline"}
                  className="w-full"
                  asChild
                >
                  <Link href={plan.href}>{plan.cta}</Link>
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
