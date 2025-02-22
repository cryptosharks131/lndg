"use client"

import { AggregatedData, Channel, Forward } from "@/lib/definitions";
import { Circle, CircleArrowOutDownRight, CircleArrowOutUpRight, CircleDashed, CircleDot, CircleDotDashed, CircleHelp, Orbit, Waypoints } from "lucide-react";


import {
    Label,
    PolarGrid,
    PolarRadiusAxis,
    RadialBar,
    RadialBarChart,
    Bar, BarChart, CartesianGrid, Cell, LabelList,
    XAxis,
    YAxis
} from "recharts"


import {
    ChartConfig, ChartContainer,
    ChartTooltip,
    ChartTooltipContent,
} from "@/components/ui/chart"

import { getDataFromApi } from "@/lib/data";
import { getLastNumDays } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";


export function ChannelInfo({ channel }: { channel: Channel }) {
    return (<>
        <div className="grid gap-1 justify-center sm:text-left pb-2 w-40 ">
            <div className="flex flex-col gap-1">
                <span className="font-medium">
                    {channel.alias ? channel.alias : channel.remote_pubkey.slice(0, 10) +
                        "..."}
                </span>
            </div>
            <div className="flex items-center gap-1 text-xs">
                <span className="text-muted-foreground">ChID</span>
                <span className="font-mono font-medium uppercase tabular-nums text-secondary-foreground">{channel.short_chan_id}</span>
                <ChannelStatusCodes channelActive={channel.is_active} channelOpen={channel.is_open} channelPendingClose={false} channelPendingOpen={false} />

            </div>
        </div>
    </>
    )
}

const ChannelStatusCodes = ({ channelActive,
    channelOpen,
    channelPendingOpen,
    channelPendingClose,
}: {
    channelActive: boolean,
    channelOpen: boolean,
    channelPendingOpen: boolean,
    channelPendingClose: boolean
}) => {
    const getChannelIcon = () => {
        switch (true) {
            case channelActive && channelOpen:
                return (
                    <div title="Channel Active">
                        <Orbit className="stroke-chart-2 cursor-pointer animate-pulse" size={16} strokeWidth={3} />
                    </div>
                );
            case !channelActive && channelOpen:
                return (
                    <div title="Channel Inactive">
                        <Orbit className="stroke-destructive cursor-pointer animate-pulse" size={16} strokeWidth={3} />
                    </div>
                );
            case channelOpen:
                return (
                    <div title="Channel Open">
                        <CircleDot className="stroke-chart-2 cursor-pointer animate-pulse" size={16} strokeWidth={3} />
                    </div>
                );
            case !channelOpen:
                return (
                    <div title="Channel Closed">
                        <Circle className="stroke-destructive cursor-pointer animate-pulse" size={16} strokeWidth={3} />
                    </div>
                );
            case channelPendingOpen:
                return (
                    <div title="Channel Pending Open">
                        <CircleDotDashed className="stroke-chart-4 cursor-pointer animate-pulse" size={16} strokeWidth={3} />
                    </div>
                );
            case channelPendingClose:
                return (
                    <div title="Channel Pending Closed">
                        <CircleDashed className="stroke-chart-4 cursor-pointer animate-pulse" size={16} strokeWidth={3} />
                    </div>
                );
            default:
                return null;
        }
    };
    return (
        <div className="flex items-center">
            {<>{getChannelIcon()}</>}
        </div>
    )

}

function LocalBalanceChart({ localBalance, remoteBalance }:
    { localBalance: number, remoteBalance: number }) {

    const percentLocalBalance = (localBalance / (localBalance + remoteBalance)) * 100
    // const percentLocalBalance = 123
    const fillColor =
        percentLocalBalance <= 5 ? "var(--color-drained)" :
            percentLocalBalance >= 95 ? "var(--color-surplus)" :
                "var(--color-good)";

    const chartData = [
        { browser: "safari", percentLocalBalance: percentLocalBalance, fill: fillColor },
    ]


    const chartConfig = {
        percentLocalBalance: {
            label: "percentLocalBalance",
        },
        drained: {
            label: "Safari",
            color: "hsl(var(--chart-3))",
        },
        good: {
            label: "Safari",
            color: "hsl(var(--chart-2))",
        },
        surplus: {
            label: "Safari",
            color: "hsl(var(--chart-1))",
        },
    } satisfies ChartConfig

    return (

        <ChartContainer
            config={chartConfig}
            className="mx-auto aspect-square w-10"
        >
            <RadialBarChart
                data={chartData}
                startAngle={0}
                endAngle={(percentLocalBalance * 3.6)}
                innerRadius={18}
                outerRadius={28}
            >
                <PolarGrid
                    gridType="circle"
                    radialLines={false}
                    stroke="none"
                    className="first:fill-muted last:fill-background"
                    polarRadius={[20, 16]}
                />
                <RadialBar dataKey="percentLocalBalance" cornerRadius={10} />
                <PolarRadiusAxis tick={false} tickLine={false} axisLine={false}>
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
                                            className="fill-foreground text-xs font-bold animate-pulse"
                                        >
                                            {chartData[0].percentLocalBalance.toFixed()}
                                        </tspan>
                                    </text>
                                )
                            }
                        }}
                    />
                </PolarRadiusAxis>
            </RadialBarChart>
        </ChartContainer>
    )
}


export function Liquidity({ channel }: { channel: Channel }) {

    return (


        <div className="flex gap-5">
            <div className="flex flex-col">

                <span className="text-foreground flex flex-row items-center gap-2 cursor-pointer w-24" title="Capacity">
                    <Waypoints className="stroke-chart-1" size={12} />
                    {/* <span className="text-muted-foreground">Remote Balance: </span> */}
                    <span className="font-medium">{channel.capacity.toLocaleString()}</span>
                </span>


                <span className="text-foreground flex flex-row items-center gap-2 cursor-pointer w-24" title="Unsettled Balance">
                    <CircleHelp className="stroke-chart-3" size={12} />
                    <span className="font-medium">{channel.unsettled_balance.toLocaleString()}</span>
                </span>



            </div>
            <div className="flex items-center gap-x-4">
                <div className="">
                    <LocalBalanceChart remoteBalance={channel.remote_balance} localBalance={channel.local_balance} />
                </div>
            </div>
            <div className="flex flex-col">
                <span className="text-foreground flex flex-row items-center gap-2 cursor-pointer" title="Remote Balance / Inbound Liquidity">
                    <CircleArrowOutDownRight className="stroke-chart-1" size={12} />
                    {/* <span className="text-muted-foreground">Remote Balance: </span> */}
                    <span className="font-medium">{channel.remote_balance.toLocaleString()}</span>
                </span>
                <span className="text-foreground flex flex-row items-center gap-2 cursor-pointer" title="Local Balance / Outbound Liquidity">
                    <CircleArrowOutUpRight className="stroke-chart-2" size={12} />
                    {/* <span className="text-muted-foreground">Local Balance: </span> */}
                    <span className="font-medium" >{channel.local_balance.toLocaleString()}</span>
                </span>

            </div>
        </div>
    )
}


export const InboundRate = ({ channel }: { channel: Channel }) => (
    <div className="flex items-center gap-4 grow">
        <CircleArrowOutDownRight className="stroke-chart-1" />
        <div className="flex flex-col gap-0">
            <span className="text-foreground">
                <span className="text-muted-foreground">Rate: </span>
                <span className="font-medium">{channel.remote_fee_rate} ppm</span>
            </span>
            <span className="text-foreground">
                <span className="text-muted-foreground">Base: </span>
                <span className="font-medium">{channel.remote_base_fee} msat</span>
            </span>
        </div>
    </div>
)

export const OutboundRate = ({ channel }: { channel: Channel }) => (
    <div className="flex items-center gap-4 grow">
        <CircleArrowOutUpRight className="stroke-chart-2" />
        <div className="flex flex-col gap-0">
            <span className="text-foreground">
                <span className="text-muted-foreground">Rate: </span>
                <span className="font-medium">{channel.local_fee_rate} ppm</span>
            </span>
            <span className="text-foreground">
                <span className="text-muted-foreground">Base: </span>
                <span className="font-medium">{channel.local_base_fee} msat</span>
            </span>
        </div>
    </div>
)

interface ChannelRoutesChartData {
    date: string;
    routedIn: number;
    routedOut: number;

}

export function ChannelRoutesChart({ forwardsIn, forwardsOut }: { forwardsIn: AggregatedData[], forwardsOut: AggregatedData[] }) {

    const chartDataDict: { [date: string]: ChannelRoutesChartData } = {};

    for (const date of getLastNumDays(7)) {
        chartDataDict[date] = {
            date,
            routedIn: 0,
            routedOut: 0,
        };
    }

    const mergeData = (
        data: AggregatedData[],
        key: "routedIn" | "routedOut",
    ) => {
        data.forEach((entry) => {
            if (entry.date in chartDataDict) {
                key === "routedIn" ?
                    chartDataDict[entry.date][key] = entry.value ?? 0 : chartDataDict[entry.date][key] = (entry.value ?? 0) * 1;
            }
        });
    };


    mergeData(forwardsIn, "routedIn");
    mergeData(forwardsOut, "routedOut");

    const chartData = Object.values(chartDataDict).sort(
        (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
    );

    const chartConfig = {
        routedIn: {
            label: "Routed In",
            color: "hsl(var(--chart-1))",
        },
        routedOut: {
            label: "Routed Out",
            color: "hsl(var(--chart-2))",
        },
    } satisfies ChartConfig

    return (
        <div className="flex gap-4 place-items-center">

            <ChartContainer config={chartConfig} className="h-9 w-40">
                <BarChart accessibilityLayer data={chartData}>
                    <XAxis
                        dataKey="date"
                        tickLine={false}
                        tickMargin={1}
                        axisLine={false}
                        tickFormatter={(value) => {
                            const date = new Date(value)
                            return date.toLocaleDateString("en-US", {
                                day: "numeric",
                            })
                        }}
                        hide
                    />
                    <ChartTooltip
                        cursor={false}
                        content={<ChartTooltipContent indicator="dashed" />}
                    />
                    <Bar dataKey="routedIn" fill="var(--color-routedIn)" radius={4} />
                    <Bar dataKey="routedOut" fill="var(--color-routedOut)" radius={4} />
                </BarChart>
            </ChartContainer>

            <div className="grid grid-cols-2 gap-1">

                <RoutingBadges forwardsIn={forwardsIn} forwardsOut={forwardsOut} />

            </div>

        </div>


    )
}


const RoutingBadges = ({ forwardsIn, forwardsOut }: { forwardsIn: AggregatedData[], forwardsOut: AggregatedData[] }) => {
    const formatNumberToTruncatedValues = (num: number) => {
        if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(1) + "B"; // Billion
        if (num >= 1_000_000) return (num / 1_000_000).toFixed(1) + "M"; // Million
        if (num >= 1_000) return (num / 1_000).toFixed(1) + "K"; // Thousand
        return num.toString(); // Less than 1K
    };
    return (
        <>
            {formatNumberToTruncatedValues(forwardsIn.at(-1)?.value ?? 0) !== "0" && formatNumberToTruncatedValues(forwardsIn.at(-1)?.value ?? 0) !== "0.00" && (
                <Badge variant="outline" className="col-span-1">
                    <CircleArrowOutDownRight className="stroke-chart-1" size={8} />
                    <span className="pl-2">
                        1d:
                    </span>
                    <span className="pl-2">
                        {formatNumberToTruncatedValues(forwardsIn.at(-1)?.value ?? 0)}
                    </span>
                </Badge>
            )}
            {
                formatNumberToTruncatedValues(forwardsIn.reduce((sum, entry) => sum + entry.value, 0)) !== "0" && formatNumberToTruncatedValues(forwardsIn.reduce((sum, entry) => sum + entry.value, 0)) !== "0.00" && (
                    <Badge variant="outline" className="col-span-1">
                        <CircleArrowOutDownRight className="stroke-chart-1" size={8} />
                        <span className="pl-2">
                            7d:
                        </span>
                        <span className="pl-2">
                            {formatNumberToTruncatedValues(forwardsIn.reduce((sum, entry) => sum + entry.value, 0))}
                        </span>

                    </Badge>
                )
            }
            {
                formatNumberToTruncatedValues(forwardsOut.at(-1)?.value ?? 0) !== "0" && formatNumberToTruncatedValues(forwardsOut.at(-1)?.value ?? 0) !== "0.00" && (
                    <Badge variant="outline" className="col-span-1">
                        <CircleArrowOutUpRight className="stroke-chart-2" size={8} />
                        <span className="pl-2">
                            1d:
                        </span>
                        <span className="pl-2">
                            {formatNumberToTruncatedValues(forwardsOut.at(-1)?.value ?? 0)}
                        </span>
                    </Badge>
                )
            }
            {
                formatNumberToTruncatedValues(forwardsOut.reduce((sum, entry) => sum + entry.value, 0)) !== "0" && formatNumberToTruncatedValues(forwardsOut.reduce((sum, entry) => sum + entry.value, 0)) !== "0.00" && (
                    <Badge variant="outline" className="col-span-1">
                        <CircleArrowOutUpRight className="stroke-chart-2" size={8} />
                        <span className="pl-2">
                            7d:
                        </span>
                        <span className="pl-2">
                            {formatNumberToTruncatedValues(forwardsOut.reduce((sum, entry) => sum + entry.value, 0))}
                        </span>
                    </Badge>
                )
            }
        </>
    )
}

