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
    fetchRoutedChartData
} from "@/lib/data";

export default async function OverviewSection() {
    const balanceChartData = await fetchBalancesChartData();
    const { ChannelsChartData, LiquidityChartData } = await fetchChannelsChartData();
    const feesChartData = await fetchFeeChartData();
    const routedChartData = await fetchRoutedChartData();
    return (
        <div className="grid grid-cols-12 gap-5">
            <div className="col-span-4">
                <BalancesChart chartData={balanceChartData} />
            </div>
            <div className="col-span-4">
                <ActiveChannelsChart chartData={ChannelsChartData} />
            </div>
            <div className="col-span-4">
                <LiquidityChart chartData={LiquidityChartData} />
            </div>
            <div className="col-span-6">
                <NodePerformanceChart />
            </div>
            <div className="col-span-6">
                <FeesChart chartData={feesChartData} />
            </div>
            <div className="col-span-12">
                <RoutedChart chartData={routedChartData} />
            </div>
        </div>
    )
}