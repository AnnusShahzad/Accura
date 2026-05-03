"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { billingApi, userApi } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import { TIERS } from "@/lib/constants";
import { formatDate, formatNumber, cn } from "@/lib/utils";
import type { Subscription, Transaction, TokenUsage, SubscriptionPlan } from "@/types";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  CardFooter,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  CreditCard,
  TrendingUp,
  Coins,
  ArrowUpRight,
  Check,
  Loader2,
} from "lucide-react";

export default function BillingPage() {
  const { user, setUser } = useAuthStore();
  const queryClient = useQueryClient();

  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">("monthly");
  const [selectedPlan, setSelectedPlan] = useState<SubscriptionPlan | null>(null);
  const [isPaymentModalOpen, setIsPaymentModalOpen] = useState(false);
  const [cardNumber, setCardNumber] = useState("");
  const [expiry, setExpiry] = useState("");
  const [cvc, setCvc] = useState("");

  const { data: plans, isLoading: loadingPlans } = useQuery({
    queryKey: ["plans"],
    queryFn: async () => {
      const res = await billingApi.getPlans();
      return res.data;
    },
  });

  const { data: subscription, isLoading: loadingSub } = useQuery({
    queryKey: ["subscription"],
    queryFn: async () => {
      const res = await billingApi.getSubscription();
      return res.data;
    },
  });

  const { data: transactions, isLoading: loadingTx } = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => {
      const res = await billingApi.getTransactions();
      return res.data;
    },
  });

  const { data: tokenUsage, isLoading: loadingTokens } = useQuery({
    queryKey: ["token-usage"],
    queryFn: async () => {
      const res = await billingApi.getTokenUsage();
      return res.data;
    },
  });

  const subscribe = useMutation({
    mutationFn: (data: { plan_name: string; billing_cycle: "monthly" | "yearly" }) =>
      billingApi.subscribe(data),
    onSuccess: async () => {
      toast.success("Subscription upgraded successfully!");
      queryClient.invalidateQueries({ queryKey: ["subscription"] });
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      
      try {
        const meRes = await userApi.getMe();
        if (meRes.success) {
          setUser(meRes.data.user, meRes.data.profile);
        }
      } catch (e) {
        console.error("Failed to refresh user profile", e);
      }

      setIsPaymentModalOpen(false);
      setSelectedPlan(null);
      // Reset form
      setCardNumber("");
      setExpiry("");
      setCvc("");
    },
    onError: (err: any) => {
      toast.error(err.message || "Upgrade failed");
    },
  });

  const handleUpgradeClick = (plan: SubscriptionPlan) => {
    if (plan.name === "business") {
      toast.info("Please contact us for Business tier access.");
      return;
    }
    setSelectedPlan(plan);
    setIsPaymentModalOpen(true);
  };

  const handleProcessPayment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPlan) return;
    subscribe.mutate({
      plan_name: selectedPlan.name,
      billing_cycle: billingCycle,
    });
  };

  const currentTierKey = user?.tier || "basic";
  const currentTierLabel = TIERS[currentTierKey as keyof typeof TIERS] || currentTierKey;

  const isLoading = loadingSub || loadingTx || loadingTokens || loadingPlans;

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Billing & Subscription</h1>
        <p className="text-muted-foreground mt-2">
          Manage your plan, view usage, and review transactions
        </p>
      </div>

      {/* Current Plan */}
      <Card className="border-primary/50 shadow-sm bg-primary/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CreditCard className="h-5 w-5 text-primary" />
            Current Plan
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loadingSub ? (
            <Skeleton className="h-24 w-full" />
          ) : (
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <h3 className="text-3xl font-bold capitalize">
                    {currentTierLabel}
                  </h3>
                  <Badge
                    variant={subscription?.status === "active" ? "default" : "secondary"}
                    className="h-6 px-2"
                  >
                    {subscription?.status || "active"}
                  </Badge>
                </div>
                <p className="text-muted-foreground">
                  {subscription?.plan_name || "Free plan"}
                </p>
                {subscription?.current_period_end && (
                  <p className="text-sm font-medium">
                    Renews on {formatDate(subscription.current_period_end)}
                  </p>
                )}
              </div>
              <Button onClick={() => {
                const element = document.getElementById('plans-section');
                element?.scrollIntoView({ behavior: 'smooth' });
              }}>
                <ArrowUpRight className="mr-2 h-4 w-4" />
                Change Plan
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Plan comparison */}
      <div id="plans-section" className="space-y-6 pt-4">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div>
            <h2 className="text-2xl font-bold">Subscription Plans</h2>
            <p className="text-muted-foreground">Choose the perfect plan for your needs</p>
          </div>
          <div className="flex items-center gap-3 bg-secondary/50 p-1.5 rounded-full border">
            <span className={cn("text-sm font-medium px-3 py-1 rounded-full cursor-pointer transition-colors", billingCycle === "monthly" ? "bg-background shadow-sm" : "text-muted-foreground")} onClick={() => setBillingCycle("monthly")}>Monthly</span>
            <span className={cn("text-sm font-medium px-3 py-1 rounded-full cursor-pointer transition-colors", billingCycle === "yearly" ? "bg-background shadow-sm" : "text-muted-foreground")} onClick={() => setBillingCycle("yearly")}>Yearly <span className="text-primary text-xs ml-1">-20%</span></span>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-3">
          {loadingPlans ? (
             Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-96 w-full" />)
          ) : plans?.map((plan) => {
            const isCurrent = plan.name === user?.tier;
            const price = billingCycle === "yearly" ? plan.price_yearly / 12 : plan.price_monthly;
            const displayPrice = price > 0 ? `$${price.toFixed(2)}` : "Free";

            return (
              <Card
                key={plan.id}
                className={cn(
                  "relative flex flex-col transition-all duration-200 hover:shadow-md",
                  isCurrent ? "border-primary shadow-sm" : "border-border"
                )}
              >
                {isCurrent && (
                  <div className="absolute -top-3 left-0 right-0 flex justify-center">
                    <Badge className="bg-primary text-primary-foreground">Current Plan</Badge>
                  </div>
                )}
                <CardHeader className="text-center pt-8">
                  <CardTitle className="text-xl">{plan.display_name}</CardTitle>
                  <div className="mt-4 flex items-baseline justify-center gap-1">
                    <span className="text-4xl font-bold">{displayPrice}</span>
                    {price > 0 && <span className="text-muted-foreground">/mo</span>}
                  </div>
                  {price > 0 && billingCycle === "yearly" && (
                    <p className="text-xs text-muted-foreground mt-1">Billed ${plan.price_yearly} annually</p>
                  )}
                </CardHeader>
                <CardContent className="flex-1">
                  <ul className="space-y-3 text-sm">
                    {(Array.isArray(plan.features) ? plan.features : (typeof plan.features === 'string' ? JSON.parse(plan.features) : [])).map((feature: any, i: number) => (
                      <li key={i} className="flex items-center gap-2">
                        <Check className="h-4 w-4 text-primary shrink-0" />
                        <span className="text-muted-foreground">{feature}</span>
                      </li>
                    ))}
                    <li className="flex items-center gap-2">
                      <Check className="h-4 w-4 text-primary shrink-0" />
                      <span className="text-muted-foreground">{plan.requests_per_day} requests / day</span>
                    </li>
                  </ul>
                </CardContent>
                <CardFooter>
                  <Button
                    variant={isCurrent ? "outline" : "default"}
                    className="w-full"
                    disabled={isCurrent}
                    onClick={() => handleUpgradeClick(plan)}
                  >
                    {isCurrent ? "Active Plan" : (plan.name === "business" ? "Contact Us" : "Upgrade")}
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Mock Payment Dialog */}
      <Dialog open={isPaymentModalOpen} onOpenChange={setIsPaymentModalOpen}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Complete Payment</DialogTitle>
            <DialogDescription>
              You are upgrading to the <strong className="text-foreground">{selectedPlan?.display_name}</strong> plan ({billingCycle}).
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleProcessPayment} className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="card">Card Number (Mock)</Label>
              <div className="relative">
                <CreditCard className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="card"
                  placeholder="0000 0000 0000 0000"
                  className="pl-9"
                  value={cardNumber}
                  onChange={(e) => setCardNumber(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="expiry">Expiry</Label>
                <Input
                  id="expiry"
                  placeholder="MM/YY"
                  value={expiry}
                  onChange={(e) => setExpiry(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="cvc">CVC</Label>
                <Input
                  id="cvc"
                  placeholder="123"
                  type="password"
                  maxLength={4}
                  value={cvc}
                  onChange={(e) => setCvc(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="bg-secondary/50 p-3 rounded-lg text-sm flex justify-between items-center mt-2">
              <span className="text-muted-foreground">Total due today:</span>
              <span className="font-bold text-lg">
                ${billingCycle === "yearly" ? selectedPlan?.price_yearly : selectedPlan?.price_monthly}
              </span>
            </div>
            <DialogFooter className="mt-6">
              <Button type="button" variant="ghost" onClick={() => setIsPaymentModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={subscribe.isPending}>
                {subscribe.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Pay Securely
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Tabs defaultValue="usage" className="pt-6">
        <TabsList className="mb-4">
          <TabsTrigger value="usage">Token Usage</TabsTrigger>
          <TabsTrigger value="transactions">Transactions</TabsTrigger>
        </TabsList>

        <TabsContent value="usage" className="space-y-4">
          {loadingTokens ? (
            <div className="grid gap-4 md:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-28" />
              ))}
            </div>
          ) : tokenUsage ? (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Total Tokens</CardDescription>
                    <CardTitle className="text-3xl">
                      {formatNumber(tokenUsage.total_tokens)}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Coins className="h-4 w-4 text-primary" />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Input Tokens</CardDescription>
                    <CardTitle className="text-3xl">
                      {formatNumber(tokenUsage.total_input_tokens)}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Output Tokens</CardDescription>
                    <CardTitle className="text-3xl">
                      {formatNumber(tokenUsage.total_output_tokens)}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </CardContent>
                </Card>
              </div>
              {tokenUsage.period_start && tokenUsage.period_end && (
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Usage Period</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <p className="text-sm text-muted-foreground">
                      {formatDate(tokenUsage.period_start)} &mdash;{" "}
                      {formatDate(tokenUsage.period_end)}
                    </p>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            <Card className="py-12 text-center">
              <CardContent>
                <Coins className="mx-auto h-12 w-12 text-muted-foreground" />
                <CardTitle className="mt-4">No Usage Data</CardTitle>
                <CardDescription className="mt-2">
                  Start a conversation to see token usage
                </CardDescription>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="transactions">
          {loadingTx ? (
            <Skeleton className="h-64 w-full" />
          ) : !transactions || transactions.length === 0 ? (
            <Card className="py-12 text-center">
              <CardContent>
                <CreditCard className="mx-auto h-12 w-12 text-muted-foreground" />
                <CardTitle className="mt-4">No Transactions</CardTitle>
                <CardDescription className="mt-2">
                  Billing history will appear here
                </CardDescription>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {transactions.map((tx: Transaction) => (
                    <TableRow key={tx.id}>
                      <TableCell>{formatDate(tx.created_at)}</TableCell>
                      <TableCell>{tx.description}</TableCell>
                      <TableCell className="font-medium">${Number(tx.amount).toFixed(2)}</TableCell>
                      <TableCell>
                        <Badge
                          variant={
                            tx.status === "succeeded" ? "default" : "secondary"
                          }
                        >
                          {tx.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
