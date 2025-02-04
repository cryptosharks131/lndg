
import { Separator } from "@/components/ui/separator"
import ChannelBalanceChart from "@/components/channel-balance-progress"
import { Bot, BotOff, CircleArrowOutDownRight, CircleArrowOutUpRight, CircleHelp, ClipboardCopyIcon, Copy } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useToast } from "@/hooks/use-toast"


export default function ChannelCardInformation({
    channelAlias,
    channelChannelId,
    channelPubkey,
    channelActive,
    channelInboundLiquidity,
    channelOutboundLiquidity,
    channelCapacity,
    unsettledBalance,
    oRate,
    oBase,
    iRate,
    iBase,
    oTargetPercent,
    iTargetPercent,
    autoRebalance,
}
    : {
        channelAlias: string,
        channelChannelId: string,
        channelPubkey: string,
        channelActive: boolean,
        channelInboundLiquidity: number,
        channelOutboundLiquidity: number,
        channelCapacity: number
        unsettledBalance: number,
        oRate: number,
        oBase: number,
        iRate: number,
        iBase: number,
        oTargetPercent: number,
        iTargetPercent: number,
        autoRebalance: boolean,
    }
) {

    const { toast } = useToast()
    return (
        <div className="my-4">
            <div className="flex items-center justify-around">
                {channelActive
                    ? <div className="bg-green-500 rounded-full w-2 h-2 mr-4 cursor-pointer flex-none" title="Channel is Active" />
                    : <div className="bg-red-500 rounded-full w-2 h-2 mr-4 cursor-pointer flex-none" title="Channel is Inactive" />}
                <Separator orientation="vertical" />
                <div className="grid gap-1 text-center sm:text-left grow">
                    <div className="font-bold items-center text-base">{channelAlias}
                        <Button
                            variant={"ghost"}
                            title="Copy Public Key"
                            onClick={() => {
                                navigator.clipboard.writeText(channelPubkey);
                                toast({
                                    title: "Key Copied!",
                                    description: `Public Key for ${channelAlias} copied to clipboard`,
                                });
                            }}
                            className="w-4 h-4"
                        >
                            <Copy size={28} />
                        </Button>
                    </div>
                    <div className="text-small">
                        {channelChannelId}

                    </div>
                </div>
                <Separator orientation="vertical" />
                <div className="grow">

                    <ChannelBalanceChart channelInbound={channelInboundLiquidity} channelOutbound={channelOutboundLiquidity} channelCapacity={channelCapacity} />
                </div>
                <Separator orientation="vertical" />
                <div className="flex items-center gap-4 grow">
                    <CircleHelp className="stroke-chart-3" />
                    <p className="font-xs text-muted-foreground">Unsettled Balance: {unsettledBalance}</p>
                </div>
                <Separator orientation="vertical" />
                <div className="flex items-center gap-4 grow">
                    <CircleArrowOutUpRight className="stroke-chart-2" />
                    <div className="grid grid-cols-1">
                        <p className="text-xs text-muted-foreground">Outbound Rate: {oRate} ppm</p>
                        <p className="text-xs text-muted-foreground">Base: {oBase} msat</p>
                    </div>
                </div>
                <Separator orientation="vertical" />
                <div className="flex items-center gap-4 grow">
                    <CircleArrowOutDownRight className="stroke-chart-1" />
                    <div className="grid grid-cols-1">
                        <p className="text-xs text-muted-foreground">Inbound Rate: {iRate} ppm</p>
                        <p className="text-xs text-muted-foreground">Base: {iBase} msat</p>
                    </div>
                </div>
                <Separator orientation="vertical" />
                <div className="flex items-center gap-4 grow">
                    <div className="grid grid-cols-1">
                        <div className="text-xs text-muted-foreground">Outbound Target: {oTargetPercent}%</div>
                        <div className="text-xs text-muted-foreground">Inbound Target: {iTargetPercent}%</div>
                    </div>
                </div>
                <Separator orientation="vertical" />
                <div className="text-xs text-muted-foreground flex-none" title="Auto Rebalance"> {autoRebalance ? <Bot className="stroke-green-500" /> : <BotOff className="stroke-red-500" />}</div>
            </div>
        </div >

    )
}
