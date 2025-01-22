
"use client"

import { Label, Pie, PieChart, } from "recharts"

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
import React from "react"
import { ChannelsChartData } from "@/lib/definitions"

// const chartData = [
//     { status: "activeChannels", value: 9, fill: "var(--color-activeChannels)" },
//     { status: "inactiveChannels", value: 1, fill: "var(--color-inactiveChannels)" }

// ]

const chartConfig = {
    inactiveChannels: {
        label: "Inactive Channels",
        color: "hsl(var(--chart-5))",
    },
    activeChannels: {
        label: "Active Channels",
        color: "hsl(var(--chart-1))",
    },
} satisfies ChartConfig

export function ActiveChannelsChart({ chartData }: { chartData: ChannelsChartData[] }) {
    const totalChannels = React.useMemo(() => {
        return chartData.reduce((acc, curr) => acc + curr.value, 0)
    }, [])

    return (

        <Card className="">
            <CardHeader className="">
                <CardTitle>Channel Overview</CardTitle>
                <CardDescription>Displaying channel counts by status</CardDescription>
            </CardHeader>
            <CardContent className="">
                <ChartContainer
                    config={chartConfig}
                    className=""
                >
                    <PieChart>
                        <ChartTooltip
                            cursor={false}
                            content={<ChartTooltipContent hideLabel />}
                        />
                        <ChartLegend content={<ChartLegendContent />} />

                        {/* <Legend layout="vertical" align="right" verticalAlign="middle" height={36} color="white" /> */}
                        <Pie
                            data={chartData}
                            dataKey="value"
                            nameKey="status"
                            innerRadius={60}
                            outerRadius={90}
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
                                                    {totalChannels.toLocaleString()}
                                                </tspan>
                                                <tspan
                                                    x={viewBox.cx}
                                                    y={(viewBox.cy || 0) + 24}
                                                    className="fill-foreground"
                                                >
                                                    Channels
                                                </tspan>
                                            </text>
                                        )
                                    }
                                }}
                            />
                        </Pie>
                    </PieChart>
                </ChartContainer>
            </CardContent>
        </Card>

    )
}

