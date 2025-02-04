

import { Layer, Rectangle, Sankey, Tooltip } from "recharts";


import SankeyChartNode from "@/components/dashboard/performance/sankey-chart-node"
import SankeyChartLink from "@/components/dashboard/performance/sankey-chart-link"

import { ChartConfig, ChartContainer, ChartTooltip } from "@/components/ui/chart";
import { ChannelPerformanceSankeyChartData } from "@/lib/definitions";

const chartConfig = {
} satisfies ChartConfig





export default function SankeyChart({ chartData }: { chartData: ChannelPerformanceSankeyChartData }) {
    return (
        <ChartContainer
            config={chartConfig}
            className="aspect-auto h-72 w-full"
        >
            <Sankey
                width={960}
                height={900}
                margin={{ top: 20, bottom: 20 }}
                data={chartData}
                nodeWidth={10}
                nodePadding={40}
                linkCurvature={0.61}
                iterations={64}
                link={<SankeyChartLink />}
                node={<SankeyChartNode containerWidth={60} />}
            >
                <defs>
                    <linearGradient id={"linkGradient"}>
                        <stop offset="0%" stopColor="rgba(41, 100, 163, 0.5)" />
                        <stop offset="100%" stopColor="rgba(67, 157, 89, 0.3)" />
                    </linearGradient>
                </defs>
                <Tooltip />
            </Sankey>
        </ChartContainer>
    )
}