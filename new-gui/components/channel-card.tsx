'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import SankeyChart from "@/components/dashboard/performance/sankey-chart";
import ChannelCardInformation from "@/components/dashboard/performance/channel-card-information";
import {
    Accordion,
    AccordionContent,
    AccordionItem,
    AccordionTrigger,
} from "@/components/ui/accordion"
import { fetchChannelsData } from "@/lib/data";
import { Channel } from "@/lib/definitions";


const data0 = {
    "nodes": [
        {
            "name": "alice",
        },
        {
            "name": "susan"
        },
        {
            "name": "dave"
        },
        {
            "name": "carl"
        },
        {
            "name": "erin"
        }
    ],
    "links": [
        {
            "source": 0,
            "target": 1,
            "value": 3728.3,
        },
        {
            "source": 0,
            "target": 2,
            "value": 354170
        },
        {
            "source": 0,
            "target": 3,
            "value": 62429
        },
        {
            "source": 0,
            "target": 4,
            "value": 291741
        }
    ],
};

export default function ChannelCard({ channel }: { channel: Channel }) {
    // console.log(channels)
    return (
        <>
            <Card key={channel.chan_id}>
                <CardContent className="py-4">
                    <Accordion type="multiple">
                        <ChannelCardInformation
                            channelAlias={channel.alias}
                            channelPubkey={channel.remote_pubkey}
                            channelChannelId={channel.short_chan_id}
                            channelActive={channel.is_active && channel.is_open}
                            channelInboundLiquidity={channel.local_balance}
                            channelOutboundLiquidity={channel.remote_balance}
                            channelCapacity={channel.capacity}
                            iRate={channel.local_fee_rate}
                            oRate={channel.remote_fee_rate}
                            iBase={channel.local_base_fee}
                            oBase={channel.remote_base_fee}
                            iTargetPercent={channel.ar_in_target}
                            oTargetPercent={channel.ar_out_target}
                            autoRebalance={channel.auto_rebalance}
                            unsettledBalance={channel.unsettled_balance}
                        />
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
                    </Accordion>

                </CardContent >
            </Card >
        </>

    );
}
