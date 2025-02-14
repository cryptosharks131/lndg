
import { Separator } from "@/components/ui/separator"
import ChannelBalanceChart from "@/components/channel-balance-progress"
import { Bot, BotOff, Circle, CircleArrowOutDownRight, CircleArrowOutUpRight, CircleDashed, CircleDot, CircleDotDashed, CircleHelp, Orbit, Target } from "lucide-react"




export default function ChannelCardInformation({
    channelAlias,
    channelChannelId,
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
    return (
        <div className="w-full">
            <ChannelDescriptionContent channelAlias={channelAlias} channelChannelId={channelChannelId} channelActive={channelActive} channelInboundLiquidity={channelInboundLiquidity} channelOutboundLiquidity={channelOutboundLiquidity} channelCapacity={channelCapacity} />
            <Separator orientation="horizontal" className="mb-2" />
            <div className="flex items-center justify-around">

                <Separator orientation="vertical" />
                <UnsettledBalance unsettledBalance={unsettledBalance} />
                <Separator orientation="vertical" />
                <OutboundRate oRate={oRate} oBase={oBase} />
                <Separator orientation="vertical" />
                <InboundRate iRate={iRate} iBase={iBase} />
                <Separator orientation="vertical" />
                <Targets oTargetPercent={oTargetPercent} iTargetPercent={iTargetPercent} />
                <Separator orientation="vertical" />
                <AutoRebalance autoRebalance={autoRebalance} />
            </div>
        </div >

    )
}



const UnsettledBalance = ({ unsettledBalance }: { unsettledBalance: number }) =>
(
    <div className="flex items-center gap-4 grow">
        <CircleHelp className="stroke-chart-3" />
        <p className="font-xs text-muted-foreground">Unsettled Balance: {unsettledBalance}</p>
    </div>
)

const OutboundRate = ({ oRate, oBase }: { oRate: number, oBase: number }) => (
    <div className="flex items-center gap-4 grow">
        <CircleArrowOutUpRight className="stroke-chart-2" />
        <div className="grid grid-cols-1">
            <p className="text-xs text-muted-foreground">Outbound Rate: {oRate} ppm</p>
            <p className="text-xs text-muted-foreground">Base: {oBase} msat</p>
        </div>
    </div>
)

const InboundRate = ({ iRate, iBase }: { iRate: number, iBase: number }) => (
    <div className="flex items-center gap-4 grow">
        <CircleArrowOutDownRight className="stroke-chart-1" />
        <div className="grid grid-cols-1">
            <p className="text-xs text-muted-foreground">Inbound Rate: {iRate} ppm</p>
            <p className="text-xs text-muted-foreground">Base: {iBase} msat</p>
        </div>
    </div>
)

const AutoRebalance = ({ autoRebalance }: { autoRebalance: boolean }) => (
    <div className="text-xs text-muted-foreground flex-none" title="Auto Rebalance"> {autoRebalance ? <Bot className="stroke-primary" /> : <BotOff className="stroke-muted-foreground" />}</div>

)

const Targets = ({ oTargetPercent, iTargetPercent }: { oTargetPercent: number, iTargetPercent: number }) => (
    <div className="flex items-center gap-4 grow">
        <Target className="stroke-chart-5" />
        <div className="grid grid-cols-1">
            <div className="text-xs text-muted-foreground">Outbound Target: {oTargetPercent}%</div>
            <div className="text-xs text-muted-foreground">Inbound Target: {iTargetPercent}%</div>
        </div>
    </div>
)


const ChannelDescriptionContent = ({ channelAlias, channelChannelId, channelInboundLiquidity, channelOutboundLiquidity, channelCapacity, channelActive }: {
    channelAlias: string,
    channelChannelId: string,
    channelInboundLiquidity: number,
    channelOutboundLiquidity: number,
    channelCapacity: number
    channelActive: boolean
}) => (
    <div className="flex items-center justify-center">
        <div className="grid gap-1 text-center sm:text-left pb-2 w-40 ">
            <div className="font-bold items-center text-base">
                {channelAlias}
            </div>
            <div className="text-small">
                {channelChannelId}
            </div>
        </div>
        <div className="mx-8 grow">
            <ChannelBalanceChart channelInbound={channelInboundLiquidity} channelOutbound={channelOutboundLiquidity} channelCapacity={channelCapacity} />
        </div>
        <ChannelStatusCodes channelActive={channelActive} />
    </div>
)

const ChannelStatusCodes = ({ channelActive }: { channelActive: boolean }) => {
    return (

        <div className="flex items-center">
            {channelActive
                ?
                (<div title="Channel Active">
                    <Orbit className="stroke-chart-2 cursor-pointer" />
                </div>)
                : (<div title="Channel Inactive">
                    <Orbit className="stroke-destructive cursor-pointer" />
                </div>)
            }
            <div title="Channel Pending Open">
                <CircleDotDashed className="stroke-chart-4 cursor-pointer" />
            </div>
            <div title="Channel Open">
                <CircleDot className="stroke-chart-2 cursor-pointer" />
            </div>
            <div title="Channel Pending Closed">
                <CircleDashed className="stroke-chart-4 cursor-pointer" />
            </div>
            <div title="Channel Closed">
                <Circle className="stroke-destructive cursor-pointer" />
            </div>
        </div>
    )
}
