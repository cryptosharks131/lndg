"use client"

import { CartesianGrid, LabelList, Line, LineChart, XAxis, YAxis } from "recharts"

import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    ChartConfig,
    ChartContainer,
    ChartLegend,
    ChartLegendContent,
    ChartTooltip,
    ChartTooltipContent,
} from "@/components/ui/chart"
import { formatNumber } from "@/lib/formatter"
const chartData = [
    { date: "01/13", earned: 111, paid: 33, onchain: 0 },
    { date: "01/14", earned: 121, paid: 78, onchain: 0 },
    { date: "01/15", earned: 114, paid: 77, onchain: 5010 },
    { date: "01/16", earned: 411, paid: 99, onchain: 0 },
    { date: "01/17", earned: 188, paid: 58, onchain: 0 },
    { date: "01/18", earned: 255, paid: 111, onchain: 0 },
]

const chartConfig = {
    earned: {
        label: "Fees Earned (ppm)",
        color: "hsl(var(--chart-1))",
    },
    paid: {
        label: "Fees Paid (ppm)",
        color: "hsl(var(--chart-2))",
    },
    onchain: {
        label: "On-Chain Fees (%)",
        color: "hsl(var(--chart-3))",
    },
} satisfies ChartConfig

export function FeesChart() {
    return (
        <Card>
            <CardHeader>
                <CardTitle>Node Performance</CardTitle>
                <CardDescription>Node Outbound Utilization and Profit/Outbound for last 7 days</CardDescription>
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
                            dataKey="earned"
                            type="linear"
                            stroke="var(--color-earned)"
                            strokeWidth={2}
                            dot={{
                                fill: "var(--color-earned)",
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
                            dataKey="paid"
                            type="linear"
                            stroke="var(--color-paid)"
                            strokeWidth={2}
                            dot={{
                                fill: "var(--color-paid)",
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
                            dataKey="onchain"
                            type="linear"
                            stroke="var(--color-onchain)"
                            strokeWidth={2}
                            dot={{
                                fill: "var(--color-onchain)",
                            }}
                            activeDot={{
                                r: 6,
                            }}
                            yAxisId="right"
                            name="onchain"
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
    )
}
