"use client"

import { AggregatedData, Channel } from "@/lib/definitions"
import { ColumnDef } from "@tanstack/react-table"

import { ChannelInfo, ChannelRoutesChart, InboundRate, Liquidity, OutboundRate } from "./components"
import { fetchChannelForwardsIn, fetchChannelForwardsOut } from "@/lib/data"
import { useEffect, useState } from "react"
import { SkeletonChannelRoutedStats } from "@/components/ui/skeletons"
import { Bot } from "lucide-react"
import { Switch } from "@/components/ui/switch"

import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import { InboundFeesForm } from "./inbound-fee-form"
import { OutboundFeesForm } from "./outbound-fee-form"


export const channelColumns: ColumnDef<Channel>[] = [
    {
        accessorKey: "channelName",
        header: () => <div className="text-left">Channel</div>,
        cell: ({ row }) => {
            const channel = row.original
            return <ChannelInfo channel={channel} />
        },
    },
    {
        accessorKey: "capacity",
        header: () => <div className="text-left">Capacity and Balances</div>,
        cell: ({ row }) => {
            const channel = row.original
            return (<Liquidity channel={channel} />)
        },
    },
    {
        accessorKey: "inBound",
        header: () => <div className="text-left">Inbound Fees</div>,
        cell: ({ row }) => {
            const channel = row.original
            return (
                <Popover>
                    <PopoverTrigger>
                        <InboundRate channel={channel} />
                    </PopoverTrigger>
                    <PopoverContent className="w-80">
                        <InboundFeesForm channel={channel} />
                    </PopoverContent>
                </Popover>

            )
        },
    },
    {
        accessorKey: "routed",
        header: () => <div className="text-left">Routed</div>,
        cell: ({ row }) => {
            const channel = row.original
            const [forwardsIn, setForwardsIn] = useState<AggregatedData[]>([]);
            const [forwardsOut, setForwardsOut] = useState<AggregatedData[]>([]);
            const [loading, setLoading] = useState(true);

            useEffect(() => {
                const fetchData = async () => {
                    try {
                        const forwardsIn = await fetchChannelForwardsIn(channel, 7);
                        setForwardsIn(forwardsIn);
                        const forwardsOut = await fetchChannelForwardsOut(channel, 7)
                        setForwardsOut(forwardsOut);
                    } catch (error) {
                        console.error("Error fetching forwards:", error);
                    } finally {
                        setLoading(false);
                    }
                };
                fetchData();
            }, [channel]);


            if (loading) return <SkeletonChannelRoutedStats />;

            console.log(`${channel.chan_id} forwards in ${forwardsIn}`)
            console.log(`${channel.chan_id} forwards out ${forwardsOut}`)

            return (<ChannelRoutesChart forwardsIn={forwardsIn} forwardsOut={forwardsOut} />)
        },
    },
    {
        accessorKey: "outBound",
        header: () => <div className="text-left">Outbound Fees</div>,
        cell: ({ row }) => {
            const channel = row.original
            return (<Popover>
                <PopoverTrigger>
                    <OutboundRate channel={channel} />
                </PopoverTrigger>
                <PopoverContent className="w-80">
                    <OutboundFeesForm channel={channel} />
                </PopoverContent>
            </Popover>)
        },
    },
    {
        accessorKey: "autoRebalancer",
        header: () => <div className="text-left flex gap-2" title="Auto Rebalancer"><Bot size={18} />AR</div>,
        cell: ({ row }) => {
            const channel = row.original
            return (<Switch id="auto-rebalancer" />)
        },
    },
]



