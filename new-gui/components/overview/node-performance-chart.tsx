"use client";

import {
  CartesianGrid,
  LabelList,
  Line,
  LineChart,
  XAxis,
  YAxis,
} from "recharts";

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
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";

import { formatNumber } from "@/lib/formatter";
const chartData = [
  { date: "01/13", profit: 186, profitOnChain: 80, utilization: 70 },
  { date: "01/14", profit: 305, profitOnChain: 200, utilization: 72 },
  { date: "01/15", profit: 237, profitOnChain: 120, utilization: 60 },
  { date: "01/16", profit: 73, profitOnChain: 190, utilization: 55 },
  { date: "01/17", profit: 209, profitOnChain: 130, utilization: 68 },
  { date: "01/18", profit: 214, profitOnChain: 140, utilization: 79 },
];

const chartConfig = {
  profit: {
    label: "⚡ Profit/Outbound (ppm)",
    color: "hsl(var(--chart-1))",
  },
  profitOnChain: {
    label: "⛓️ Profit/Outbound  (ppm)",
    color: "hsl(var(--chart-2))",
  },
  utilization: {
    label: "Onboard Utilization (%)",
    color: "hsl(var(--chart-3))",
  },
} satisfies ChartConfig;

export function NodePerformanceChart() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Node Performance</CardTitle>
        <CardDescription>
          Node Outbound Utilization and Profit/Outbound for last 7 days
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <LineChart
            accessibilityLayer
            data={chartData}
            margin={{
              top: 20,
              left: 15,
              right: 15,
            }}
          >
            <CartesianGrid vertical={false} />
            <YAxis yAxisId="left" orientation="left" hide />
            <YAxis yAxisId="right" orientation="right" hide />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={(value) => value.slice(0, 5)}
              hide
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent indicator="line" />}
            />
            <ChartLegend content={<ChartLegendContent />} />

            <Line
              dataKey="profit"
              type="linear"
              stroke="var(--color-profit)"
              strokeWidth={2}
              dot={{
                fill: "var(--color-profit)",
              }}
              activeDot={{
                r: 6,
              }}
              yAxisId="left"
            >
              <LabelList
                position="top"
                offset={12}
                className="fill-foreground"
                fontSize={12}
                formatter={formatNumber}
              />
            </Line>
            <Line
              dataKey="profitOnChain"
              type="linear"
              stroke="var(--color-profitOnChain)"
              strokeWidth={2}
              dot={{
                fill: "var(--color-profitOnChain)",
              }}
              activeDot={{
                r: 6,
              }}
              yAxisId="left"
            >
              <LabelList
                position="top"
                offset={12}
                className="fill-foreground"
                fontSize={12}
                formatter={formatNumber}
              />
            </Line>
            <Line
              dataKey="utilization"
              type="linear"
              stroke="var(--color-utilization)"
              strokeWidth={2}
              dot={{
                fill: "var(--color-utilization)",
              }}
              activeDot={{
                r: 6,
              }}
              yAxisId="right"
            >
              <LabelList
                position="top"
                offset={12}
                className="fill-foreground"
                fontSize={12}
                formatter={formatNumber}
              />
            </Line>
          </LineChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
