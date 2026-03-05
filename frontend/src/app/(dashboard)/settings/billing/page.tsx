"use client";

import { useQuery } from "@tanstack/react-query";
import { billingApi } from "@/lib/api-client";
import { useAuthStore } from "@/stores/auth-store";
import { TIERS } from "@/lib/constants";
import { formatDate, formatNumber } from "@/lib/utils";
import type { Subscription, Transaction, TokenUsage } from "@/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
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
  CreditCard,
  TrendingUp,
  Coins,
  ArrowUpRight,
} from "lucide-react";

export default function BillingPage() {
  const { user } = useAuthStore();

  const { data: subscription, isLoading: loadingSub } = useQuery({
    queryKey: ["subscription"],
    queryFn: async () => {
      const res = await billingApi.getSubscription();
      return res.data as Subscription;
    },
  });

  const { data: transactions, isLoading: loadingTx } = useQuery({
    queryKey: ["transactions"],
    queryFn: async () => {
      const res = await billingApi.getTransactions();
      return res.data as Transaction[];
    },
  });

  const { data: tokenUsage, isLoading: loadingTokens } = useQuery({
    queryKey: ["token-usage"],
    queryFn: async () => {
      const res = await billingApi.getTokenUsage();
      return res.data as TokenUsage;
    },
  });

  const currentTierKey = user?.tier || "basic";
  const currentTierLabel = TIERS[currentTierKey as keyof typeof TIERS] || currentTierKey;

  const isLoading = loadingSub || loadingTx || loadingTokens;

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Billing & Subscription</h1>
        <p className="text-muted-foreground">
          Manage your plan, view usage, and review transactions
        </p>
      </div>

      {/* Current Plan */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5" />
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
                  <h3 className="text-2xl font-bold capitalize">
                    {currentTierLabel}
                  </h3>
                  <Badge
                    variant={subscription?.status === "active" ? "default" : "secondary"}
                  >
                    {subscription?.status || "active"}
                  </Badge>
                </div>
                <p className="text-muted-foreground">
                  {subscription?.plan_name || "Free plan"}
                </p>
                {subscription?.current_period_end && (
                  <p className="text-sm text-muted-foreground">
                    Renews {formatDate(subscription.current_period_end)}
                  </p>
                )}
              </div>
              <Button variant="outline">
                <ArrowUpRight className="mr-2 h-4 w-4" />
                Change Plan
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Plan comparison */}
      <div className="grid gap-4 md:grid-cols-3">
        {Object.entries(TIERS).map(([value, label]) => (
          <Card
            key={value}
            className={
              value === user?.tier
                ? "border-primary"
                : ""
            }
          >
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                {label}
                {value === user?.tier && (
                  <Badge>Current</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Button
                variant={value === user?.tier ? "secondary" : "default"}
                className="w-full"
                disabled={value === user?.tier}
              >
                {value === user?.tier ? "Current Plan" : "Upgrade"}
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="usage">
        <TabsList>
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
                    <CardTitle className="text-2xl">
                      {formatNumber(tokenUsage.total_tokens)}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Coins className="h-4 w-4 text-muted-foreground" />
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardDescription>Input Tokens</CardDescription>
                    <CardTitle className="text-2xl">
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
                    <CardTitle className="text-2xl">
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
                    <p className="text-sm text-muted-foreground">
                      {formatNumber(tokenUsage.total_tokens)} total tokens used
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
                      <TableCell>${tx.amount.toFixed(2)}</TableCell>
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
