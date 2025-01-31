"use client"

import { useState } from "react";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

import { ChartConfig, ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import { formatNumber } from "@/lib/formatter";
import { ProfitabilityStats } from "@/lib/definitions";


const chartConfig = {
    paymentsRouted: { label: "Payments Routed (count)", color: "hsl(var(--chart-3))", axis: "left" },
    valueRouted: { label: "Value Routed (sats)", color: "hsl(var(--chart-5))", axis: "right" },
    revenue: { label: "Revenue (sats)", color: "hsl(var(--chart-1))", axis: "left" },
    onchainCosts: { label: "On-Chain Costs (sats)", color: "hsl(var(--chart-3))", axis: "left" },
    offchainCost: { label: "Off-Chain Costs (sats)", color: "hsl(var(--chart-2))", axis: "left" },
    offchainCostPpm: { label: "Off-Chain Costs (ppm)", color: "hsl(var(--chart-6))", axis: "left" },
    percentCosts: { label: "Percent Costs (%)", color: "hsl(var(--chart-1))", axis: "left" },
    profit: { label: "Profit (sats)", color: "hsl(var(--chart-4))", axis: "left" },
    profitPpm: { label: "Profit (ppm)", color: "hsl(var(--chart-2))", axis: "left" },
} satisfies ChartConfig

export function ProfitabilityStatsChartAgg({ chartData }: { chartData: ProfitabilityStats[] }) {



    return (

        <>
            <Card className="mb-4">
                <CardHeader className="flex items-center gap-2 space-y-0 border-b py-5 sm:flex-row">
                    <div className="grid flex-1 gap-1 text-center sm:text-left">

                        <CardTitle>Profitability Stats</CardTitle>
                        <CardDescription>
                            Profitability Stats highlighted over various periods of time.
                        </CardDescription>
                    </div>
                    {/* <Select value={timeRange} onValueChange={setTimeRange}>
                        <SelectTrigger
                            className="w-[160px] rounded-lg sm:ml-auto"
                            aria-label="Select a value"
                        >
                            <SelectValue placeholder="Last 6 months" />
                        </SelectTrigger>
                        <SelectContent className="rounded-xl">
                            <SelectItem value="180d" className="rounded-lg">
                                Last 6 months
                            </SelectItem>
                            <SelectItem value="90d" className="rounded-lg">
                                Last 90 days
                            </SelectItem>
                            <SelectItem value="60d" className="rounded-lg">
                                Last 60 days
                            </SelectItem>
                            <SelectItem value="30d" className="rounded-lg">
                                Last 30 days
                            </SelectItem>
                            <SelectItem value="7d" className="rounded-lg">
                                Last 7 days
                            </SelectItem>
                        </SelectContent>
                    </Select> */}
                </CardHeader>
                <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
                    <ChartContainer
                        config={chartConfig}
                        className="aspect-auto h-96 w-full"
                    >
                        <LineChart accessibilityLayer data={chartData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>

                            <CartesianGrid vertical={false} />
                            <YAxis
                                yAxisId="left"
                                orientation="left"
                                tickLine={false}
                                axisLine={false}
                                tickMargin={0}
                                tickCount={10}
                                minTickGap={32}
                                label={{ value: 'On-Chain (sats)', angle: -90, position: "left", style: { textAnchor: 'middle' } }}
                                tickFormatter={formatNumber}
                            />
                            <YAxis
                                yAxisId="right"
                                orientation="right"
                                tickLine={false}
                                axisLine={false}
                                tickMargin={0}
                                tickCount={10}
                                minTickGap={32}
                                label={{ value: 'Revenue and Off-Chain Costs (sats)', angle: 90, position: "right", style: { textAnchor: 'middle' } }}
                                tickFormatter={formatNumber}
                            />


                            <XAxis
                                dataKey="date"
                                tickLine={false}
                                axisLine={false}
                                tickMargin={8}
                                minTickGap={32}
                                tickFormatter={(value) => {
                                    const date = new Date(value)
                                    return date.toLocaleDateString("en-US", {
                                        month: "short",
                                        day: "numeric",
                                    })
                                }}
                            />
                            <ChartTooltip
                                cursor={false}
                                content={
                                    <ChartTooltipContent
                                        labelFormatter={(value) => {
                                            return new Date(value).toLocaleDateString("en-US", {
                                                year: "numeric",
                                                month: "long",
                                                day: "numeric",
                                            })
                                        }}
                                        indicator="dashed"
                                    />
                                }
                            />
                            <ChartLegend content={<ChartLegendContent />} />


                            {Object.entries(chartConfig).map(([dataKey, { color, axis }]) => (
                                <Line
                                    key={dataKey}
                                    dataKey={dataKey}
                                    type="monotone"
                                    yAxisId={axis}
                                    stroke={color}
                                    dot={false}
                                // dot={{
                                //     fill: color,
                                // }}
                                />
                            ))
                            }

                        </LineChart>
                    </ChartContainer>
                </CardContent>
            </Card>

        </>

    )
}


// export const ProfitabilityStats: React.FC = () => {
//     const renderValue = (value: number | { stats: number; ppm: number }) => {
//         if (typeof value === "number") {
//             // Handle percentages
//             if (value > 0 && value <= 1) {
//                 return `${(value * 100).toFixed(2)}%`;
//             }
//             return value.toLocaleString(); // Format large numbers with commas
//         }

//         // Handle stats and ppm objects
//         return (
//             <span>
//                 {value.stats.toLocaleString()} sats ({value.ppm} ppm)
//             </span>
//         );
//     };

//     return (
//         <table>
//             <thead>
//                 <tr>
//                     <th>Line Item</th>
//                     <th>Description</th>
//                     <th>1 Day</th>
//                     <th>7 Day</th>
//                     <th>30 Day</th>
//                     <th>90 Day</th>
//                     <th>Lifetime</th>
//                 </tr>
//             </thead>
//             <tbody>
//                 {statsData.map((item) => (
//                     <tr key={item.lineItem}>
//                         <td>{item.lineItem}</td>
//                         <td>{item.description}</td>
//                         <td>{renderValue(item["1 Day"])}</td>
//                         <td>{renderValue(item["7 Day"])}</td>
//                         <td>{renderValue(item["30 Day"])}</td>
//                         <td>{renderValue(item["90 Day"])}</td>
//                         <td>{renderValue(item.Lifetime)}</td>
//                     </tr>
//                 ))}
//             </tbody>
//         </table>
//     );
// };
