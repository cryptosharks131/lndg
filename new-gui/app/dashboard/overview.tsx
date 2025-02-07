import { ActiveChannelsChart } from "@/components/dashboard/overview/active-channels-chart";
import { BalancesChart } from "@/components/dashboard/overview/balances-chart";
import { FeesChart } from "@/components/dashboard/overview/fee-chart";
import { LiquidityChart } from "@/components/dashboard/overview/liquidity-chart";
import { NodePerformanceChart } from "@/components/dashboard/overview/node-performance-chart";
import { RoutedChart } from "@/components/dashboard/overview/routed-chart";


import {
    fetchBalancesChartData,
    fetchChannelsChartData,
    fetchFeeChartData,
    fetchNodePerformanceChartData,
    fetchRoutedChartData
} from "@/lib/data";

export default async function OverviewSection() {
    const balanceChartData = await fetchBalancesChartData();
    const { ChannelsChartData, LiquidityChartData } = await fetchChannelsChartData();
    const feesChartData = await fetchFeeChartData();
    const routedChartData = await fetchRoutedChartData();
    const nodePerformanceChartData = await fetchNodePerformanceChartData();

    // console.log(nodePerformanceChartData)

    return (
        <div className="grid grid-cols-6 gap-5">
            <div className="col-span-6 lg:col-span-2">
                <BalancesChart chartData={balanceChartData} />
            </div>
            <div className="col-span-6 lg:col-span-2">
                <ActiveChannelsChart chartData={ChannelsChartData} />
            </div>
            <div className="col-span-6 lg:col-span-2">
                <LiquidityChart chartData={LiquidityChartData} />
            </div>
            <div className="col-span-6 lg:col-span-3">
                <NodePerformanceChart chartData={nodePerformanceChartData} />
            </div>
            <div className="col-span-6 lg:col-span-3">
                <FeesChart chartData={feesChartData} />
            </div>
            <div className="col-span-6 lg:col-span-6">
                <RoutedChart chartData={routedChartData} />
            </div>
        </div>
    )
}