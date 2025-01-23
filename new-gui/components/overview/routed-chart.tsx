"use client";

import * as React from "react";
import { Bar, BarChart, CartesianGrid, LabelList, XAxis } from "recharts";

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
import { AggregatedData } from "@/lib/definitions";
// const chartData = [

//   { date: "2024-06-01", value: 178 },
//   { date: "2024-06-02", value: 470 },
//   { date: "2024-06-03", value: 103 },
//   { date: "2024-06-04", value: 439 },
//   { date: "2024-06-05", value: 88 },
//   { date: "2024-06-06", value: 294 },
//   { date: "2024-06-07", value: 323 },
//   { date: "2024-06-08", value: 385 },
//   { date: "2024-06-09", value: 438 },
//   { date: "2024-06-10", value: 155 },
//   { date: "2024-06-11", value: 92 },
//   { date: "2024-06-12", value: 492 },
//   { date: "2024-06-13", value: 81 },
//   { date: "2024-06-14", value: 426 },
//   { date: "2024-06-15", value: 307 },
//   { date: "2024-06-16", value: 371 },
//   { date: "2024-06-17", value: 475 },
//   { date: "2024-06-18", value: 107 },
//   { date: "2024-06-19", value: 341 },
//   { date: "2024-06-20", value: 408 },
//   { date: "2024-06-21", value: 169 },
//   { date: "2024-06-22", value: 317 },
//   { date: "2024-06-23", value: 480 },
//   { date: "2024-06-24", value: 132 },
//   { date: "2024-06-25", value: 141 },
//   { date: "2024-06-26", value: 434 },
//   { date: "2024-06-27", value: 448 },
//   { date: "2024-06-28", value: 149 },
//   { date: "2024-06-29", value: 103 },
//   { date: "2024-06-30", value: 446 },
// ];

const chartConfig = {
  value: {
    label: "Payments Routed (sats)",
    color: "hsl(var(--chart-1))",
  },
} satisfies ChartConfig;

export function RoutedChart({ chartData }: { chartData: AggregatedData[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Payments Routed</CardTitle>
        <CardDescription>
          Displaying payments routed in the last 30 days
        </CardDescription>
      </CardHeader>
      <CardContent className="px-2 sm:p-6">
        <ChartContainer
          config={chartConfig}
          className="aspect-auto h-[250px] w-full"
        >
          <BarChart
            accessibilityLayer
            data={chartData}
            margin={{
              left: 12,
              right: 12,
            }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              minTickGap={32}
              tickFormatter={(value) => {
                const date = new Date(value);
                return date.toLocaleDateString("en-US", {
                  month: "short",
                  day: "numeric",
                });
              }}
              hide
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  className="w-[150px]"
                  nameKey="views"
                  labelFormatter={(value) => {
                    return new Date(value).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    });
                  }}
                />
              }
            />
            <Bar dataKey={"value"} fill={`var(--color-value)`} radius={8}>
              <LabelList
                position="top"
                offset={12}
                className="fill-foreground"
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
