import { ActiveChannelsChart } from "@/components/overview/active-channels-chart";
import { BalancesChart } from "@/components/overview/balances-chart";
import { FeesChart } from "@/components/overview/fee-chart";
import { LiquidityChart } from "@/components/overview/liquidity-chart";
import { NodePerformanceChart } from "@/components/overview/node-performance-chart";
import { RoutedChart } from "@/components/overview/routed-chart";

import { fetchBalancesChartData } from "@/lib/data/data"
import { Suspense } from "react";


export default async function Page() {

    const balanceChartData = await fetchBalancesChartData()
    // console.log(balanceChartData)


    return (
        <div className="grid grid-cols-12 gap-5">
            <div className="col-span-4">
                <BalancesChart chartData={balanceChartData} />
            </div>
            <div className="col-span-4">
                <ActiveChannelsChart />
            </div>
            <div className="col-span-4">
                <LiquidityChart />
            </div>
            <div className="col-span-6">
                <NodePerformanceChart />
            </div>
            <div className="col-span-6">
                <FeesChart />
            </div>
            <div className="col-span-12">
                <RoutedChart />
            </div>
        </div>
    )
}
