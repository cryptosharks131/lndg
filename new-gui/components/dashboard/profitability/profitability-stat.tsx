"use client"

import { XAxis, Line, LineChart } from "recharts"

import {
    Card,
    CardContent,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import { ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { Stat } from "@/lib/definitions"
import { aggregateStatData } from "@/lib/utils"

export function ProfitabilityStat({ stat }: { stat: Stat }) {

    const chartConfig = {
        revenue: {
            label: stat.name,
            color: stat.color,
        }
    } satisfies ChartConfig

    // use aggregation type to aggregate correctly use reducer


    const aggregatedValue = aggregateStatData(stat);

    return (

        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-normal">{stat.description}</CardTitle>
            </CardHeader>
            <CardContent className="pb-0">
                <div className="text-2xl font-bold">{aggregatedValue.toLocaleString('en-US', { maximumFractionDigits: 0 })}</div>
                <ChartContainer config={chartConfig} className="h-[80px] w-full">

                    <LineChart
                        data={stat.data}
                        margin={{
                            top: 5,
                            right: 10,
                            left: 10,
                            bottom: 0,
                        }}
                    >
                        <XAxis
                            dataKey="date"
                            tickLine={false}
                            axisLine={false}
                            tick={false}
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
                                    indicator="dot"

                                />
                            }
                        />
                        <Line
                            type="natural"
                            strokeWidth={2}
                            dataKey="value"
                            stroke={stat.color}
                            dot={false}
                            name={stat.name}
                        />
                    </LineChart>
                </ChartContainer>
            </CardContent>
        </Card>

    )
}