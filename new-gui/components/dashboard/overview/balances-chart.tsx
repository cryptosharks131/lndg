"use client";

import { Bar, BarChart, LabelList, XAxis, YAxis } from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";
import { formatNumber } from "@/lib/formatter";
import { BalancesChartData } from "@/lib/definitions";

const chartConfig = {
  total_balance: {
    label: "Total Balance",
    color: "hsl(var(--chart-1))",
  },
  offchain_balance: {
    label: "Off-Chain",
    color: "hsl(var(--chart-2))",
  },
  onchain_balance: {
    label: "On-Chain",
    color: "hsl(var(--chart-3))",
  },
  confirmed_balance: {
    label: "Confirmed",
    color: "hsl(var(--chart-4))",
  },
  unconfirmed_balance: {
    label: "Unconfirmed",
    color: "hsl(var(--chart-5))",
  },
} satisfies ChartConfig;

export function BalancesChart({
  chartData,
}: {
  chartData: BalancesChartData[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Balances Overview</CardTitle>
        <CardDescription>Capacities and Balances</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <BarChart
            accessibilityLayer
            data={chartData}
            layout="vertical"
            margin={{
              left: 20,
            }}
          >
            <YAxis
              dataKey="item"
              type="category"
              tickLine={false}
              tickMargin={2}
              axisLine={false}
              tickFormatter={(value) =>
                chartConfig[value as keyof typeof chartConfig]?.label
              }
            />
            <XAxis dataKey="value" type="number" hide />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Bar dataKey="value" layout="vertical" radius={5}
              stackId="a"
            >
              <LabelList
                position="insideLeft"
                offset={12}
                className="fill-white"
                fontSize={12}
                formatter={formatNumber}
              />
            </Bar>

          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
