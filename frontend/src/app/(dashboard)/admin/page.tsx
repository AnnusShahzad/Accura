"use client";

import { useQuery } from "@tanstack/react-query";
import { adminApi } from "@/lib/api-client";
import { formatNumber } from "@/lib/utils";
import type { AdminDashboard } from "@/types";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Users,
  MessageSquare,
  DollarSign,
  TrendingUp,
  Coins,
  Activity,
} from "lucide-react";

export default function AdminDashboardPage() {
  const { data: dashboard, isLoading } = useQuery({
    queryKey: ["admin", "dashboard"],
    queryFn: async () => {
      const res = await adminApi.getDashboard();
      return res.data as AdminDashboard;
    },
  });

  const stats = dashboard
    ? [
        {
          title: "Total Users",
          value: formatNumber(dashboard.total_users),
          icon: Users,
          description: `${dashboard.active_subscriptions} subscribed`,
        },
        {
          title: "Active Subscriptions",
          value: formatNumber(dashboard.active_subscriptions),
          icon: MessageSquare,
          description: "Paid plans",
        },
        {
          title: "Total Revenue",
          value: `$${dashboard.total_revenue?.toFixed(2) || "0.00"}`,
          icon: DollarSign,
          description: "All time",
        },
        {
          title: "Tokens This Month",
          value: formatNumber(dashboard.tokens_generated_month || 0),
          icon: Coins,
          description: "Platform wide",
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Admin Dashboard</h1>
        <p className="text-muted-foreground">
          Platform overview and key metrics
        </p>
      </div>

      {/* Stats Grid */}
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <stat.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Tier Distribution */}
      {dashboard?.tier_distribution && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              Tier Distribution
            </CardTitle>
            <CardDescription>Users per subscription tier</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              {Object.entries(dashboard.tier_distribution).map(
                ([tier, count]) => (
                  <div
                    key={tier}
                    className="flex items-center justify-between rounded-lg border p-4"
                  >
                    <span className="font-medium capitalize">{tier}</span>
                    <span className="text-2xl font-bold">
                      {formatNumber(count as number)}
                    </span>
                  </div>
                )
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Transactions */}
      {dashboard?.recent_transactions && dashboard.recent_transactions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              Recent Transactions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {dashboard.recent_transactions.slice(0, 5).map((tx) => (
                <div
                  key={tx.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="text-sm font-medium">{tx.description}</p>
                    <p className="text-xs text-muted-foreground">
                      {tx.created_at}
                    </p>
                  </div>
                  <p className="font-medium">${tx.amount.toFixed(2)}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
