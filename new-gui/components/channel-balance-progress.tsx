"use client"
import { useState, useEffect } from "react"
import { Progress } from "@/components/ui/progress"
import { CircleArrowOutDownRight, CircleArrowOutUpRight, } from "lucide-react"

export default function ChannelBalanceChart({ channelInbound, channelOutbound, channelCapacity }:
    { channelInbound: number, channelOutbound: number, channelCapacity: number }
) {

    const [progress, setProgress] = useState(0)
    useEffect(() => {
        const timer = setTimeout(() => setProgress(channelInbound / (channelInbound + channelOutbound) * 100), 500)
        return () => clearTimeout(timer)
    }, [progress, channelInbound, channelOutbound])

    return (
        <>
            <div className="grid grid-cols-12 gap-2 w-auto place-content-between">
                <div className="col-span-4 flex gap-1 place-self-start self-center  cursor-pointer" title="Inbound Liquidity">
                    <CircleArrowOutDownRight size={14} className="stroke-chart-1" />
                    <p className="text-chart-1 text-xs">
                        {channelInbound.toLocaleString()}
                    </p>
                </div>
                <div className="col-span-4 self-center cursor-pointer" title="Total Channel Balance">
                    <p className="text-card-foreground text-xs text-center">
                        Channel Capacity
                    </p>
                </div>
                <div className="col-span-4 flex gap-1 place-self-end self-center cursor-pointer" title="Outbound Liquidity">
                    <p className="text-chart-2 text-xs">
                        {channelOutbound.toLocaleString()}
                    </p>
                    <CircleArrowOutUpRight size={14} className="stroke-chart-2" />
                </div>
                <Progress value={progress} className="col-span-12" />
                <div className="col-span-4 gap-1 place-self-start self-center  cursor-pointer" title="% Inbound Liquidity">
                    <p className="text-chart-1 text-xs">
                        {(channelInbound / channelCapacity).toLocaleString("en-US", { style: "percent", maximumFractionDigits: 2 })}
                    </p>
                </div>
                <div className="col-span-4 self-center cursor-pointer" title="Total Channel Balance">
                    <p className="text-card-foreground text-sm font-medium text-center">

                        {channelCapacity.toLocaleString()}
                    </p>
                </div>
                <div className="col-span-4 gap-1 place-self-end self-center  cursor-pointer" title="% Outbound Liquidity">
                    <p className="text-chart-2 text-xs ">
                        {(channelOutbound / channelCapacity).toLocaleString("en-US", { style: "percent", maximumFractionDigits: 2 })}
                    </p>
                </div>
            </div>

        </>
    )


}