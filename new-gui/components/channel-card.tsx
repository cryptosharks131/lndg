'use client'

import { Card, CardContent } from "@/components/ui/card";
import ChannelCardInformation from "@/components/dashboard/performance/channel-card-information";
import { Channel } from "@/lib/definitions";


import { MenuItem, CustomContextMenu } from "@/components/custom-context-menu"
import { ArrowBigDownDash, ArrowBigUpDash, Bitcoin, Bot, Copy, Scale, TrendingUpDown, ZapOff } from "lucide-react";
import { closeChannel, ToastData } from "@/lib/channel-actions";
import { useToast } from "@/hooks/use-toast";

const copyPublicKey = async (channelAlias: string, key: string) => {
    try {
        console.log(channelAlias, key)
        await navigator.clipboard.writeText(key);
        const toast: ToastData = {
            variant: "default",
            title: "Key Copied!",
            description: `Public Key ${key} for ${channelAlias} copied to clipboard`,
        };
        return { toast: toast }
    } catch (err) {
        console.log(err)
        const toast: ToastData = {
            variant: "destructive",
            title: "Uh oh! Something went wrong.",
            description: `Failed to copy public key for ${channelAlias}: ${String(err)}`,
        };
        return { toast: toast }


    }
}

export default function ChannelCard({ channel }: { channel: Channel }) {
    // console.log(channels)
    const { toast } = useToast()

    const menuItems = (channel: Channel, toast: ReturnType<typeof useToast>["toast"]): MenuItem[] => [
        {
            label: "Copy Public Key",
            icon: <Copy size={14} />,
            onClick: async () => {
                const copy = await copyPublicKey(channel.alias, channel.remote_pubkey)
                toast({ ...copy.toast });
            }
            ,
        },
        { separator: true },
        {
            label: "Liquidity Management",
            subItems: [
                { icon: <Bot size={14} />, label: "Toggle AR", onClick: () => console.log("Increasing fees...") },
                { separator: true },
                { icon: <TrendingUpDown size={14} />, label: "Show Movement", onClick: () => console.log("Show Movement...") },
                { icon: <Scale size={14} />, label: "Rebalance", onClick: () => console.log("Rebalancing...") },
                { label: "Loop Out", onClick: () => console.log("Looping Out...") },
                { label: "Loop In", onClick: () => console.log("Looping In...") }
            ]
        },
        {
            label: "Fee Management",
            icon: <Bitcoin size={14} />,
            subItems: [
                { icon: <ArrowBigUpDash size={14} />, label: "Increase Fees", onClick: () => console.log("Increasing fees...") },
                { icon: <ArrowBigDownDash size={14} />, label: "Decrease Fees", onClick: () => console.log("Decreasing fees...") }
            ]
        },
        { separator: true },
        {
            icon: <ZapOff size={14} />, label: "Close Channel", onClick: async () => {
                const response = await closeChannel(channel, 1, false);
                toast({ ...response.toast });
            }
        },
        {
            icon: <ZapOff size={14} className="stroke-destructive" />, label: "Force Close", onClick: async () => {
                const response = await closeChannel(channel, 1, true);
                toast({ ...response.toast });
            }
        },
        { separator: true },
    ];

    return (
        <>
            <Card key={channel.chan_id}>
                <CustomContextMenu
                    trigger={
                        <>
                            <CardContent className="py-4 w-full">
                                <ChannelCardInformation
                                    channelAlias={channel.alias}
                                    channelChannelId={channel.short_chan_id}
                                    channelPubkey={channel.remote_pubkey}
                                    channelActive={channel.is_active}
                                    channelInboundLiquidity={channel.remote_balance}
                                    channelOutboundLiquidity={channel.local_balance}
                                    channelCapacity={channel.capacity}
                                    unsettledBalance={channel.unsettled_balance}
                                    oRate={channel.local_fee_rate}
                                    oBase={channel.local_base_fee}
                                    iRate={channel.remote_fee_rate}
                                    iBase={channel.remote_base_fee}
                                    oTargetPercent={channel.ar_out_target}
                                    iTargetPercent={channel.ar_in_target}
                                    autoRebalance={channel.auto_rebalance}
                                />

                            </CardContent >
                        </>

                    }
                    menuItems={menuItems(channel, toast)}
                />
            </Card >
            {/* <Accordion type="multiple">
                <AccordionItem value="item-1">
                    <AccordionTrigger>Volume Routed</AccordionTrigger>
                    <AccordionContent>
                        <SankeyChart chartData={data0} />
                    </AccordionContent>
                </AccordionItem>
                <AccordionItem value="item-2">
                    <AccordionTrigger>Rebalancing Costs</AccordionTrigger>
                    <AccordionContent>
                        <SankeyChart chartData={data0} />
                    </AccordionContent>
                </AccordionItem>
            </Accordion> */}

        </>

    );
}
