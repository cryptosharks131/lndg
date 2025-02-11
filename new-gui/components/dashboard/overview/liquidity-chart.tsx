"use client";

import * as React from "react";
import { Label, Legend, Pie, PieChart } from "recharts";

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
import { LiquidityChartData } from "@/lib/definitions";

// Sample chart data
// const chartData: LiquidtyChartData[] = [
//     { status: "inbound", value: 20000000, fill: "var(--color-inbound)" },
//     { status: "outbound", value: 100000000, fill: "var(--color-outbound)" },
//     { status: "unsettled", value: 500000, fill: "var(--color-unsettled)" },
// ];

// Function to calculate the liquidity ratio
const calculateLiquidityRatio = (data: LiquidityChartData[]): number => {
  const inbound = data.find((item) => item.status === "inbound")?.value ?? 0;
  const outbound = data.find((item) => item.status === "outbound")?.value ?? 1; // Default to 1 to avoid division by zero
  return inbound / outbound;
};

const chartConfig = {
  liquidity: {
    label: "Liquidity",
  },
  outbound: {
    label: "Outbound",
    color: "hsl(var(--chart-1))",
  },
  inbound: {
    label: "Inbound",
    color: "hsl(var(--chart-2))",
  },
  unsettled: {
    label: "Unsettled",
    color: "hsl(var(--chart-3))",
  },
} satisfies ChartConfig;

export function LiquidityChart({
  chartData,
}: {
  chartData: LiquidityChartData[];
}) {
  const liquidityRatio = calculateLiquidityRatio(chartData);

  return (
    <Card className="">
      <CardHeader className="">
        <CardTitle>Node Liquidity</CardTitle>
        <CardDescription>
          Displaying the liquidity distribution of the node
        </CardDescription>
      </CardHeader>
      <CardContent className="">
        <ChartContainer config={chartConfig} className="">
          <PieChart>
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <ChartLegend content={<ChartLegendContent />} />

            <Pie
              data={chartData}
              dataKey="value"
              nameKey="status"
              innerRadius={45}
              outerRadius={65}
              strokeWidth={5}
            >
              <Label
                content={({ viewBox }) => {
                  if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                    return (
                      <text
                        x={viewBox.cx}
                        y={viewBox.cy}
                        textAnchor="middle"
                        dominantBaseline="middle"
                      >
                        <tspan
                          x={viewBox.cx}
                          y={viewBox.cy}
                          className="fill-foreground text-3xl font-bold"
                        >
                          {liquidityRatio.toLocaleString('en-US', { style: 'percent' })}
                        </tspan>
                        <tspan
                          x={viewBox.cx}
                          y={(viewBox.cy || 0) + 24}
                          className="fill-foreground"
                        >
                          Ratio
                        </tspan>
                      </text>
                    );
                  }
                }}
              />
            </Pie>
          </PieChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
