import { ActiveChannelsChart } from "@/components/dashboard/overview/active-channels-chart";
import { BalancesChart } from "@/components/dashboard/overview/balances-chart";
import { FeesChart } from "@/components/dashboard/overview/fee-chart";
import { LiquidityChart } from "@/components/dashboard/overview/liquidity-chart";
import { NodePerformanceChart } from "@/components/dashboard/overview/node-performance-chart";
import { RoutedChart } from "@/components/dashboard/overview/routed-chart";
import { SkeletonBalancesChart, SkeletonActiveChannelsChart, SkeletonLiquidityChart, SkeletonNodePerformanceChart, SkeletonFeesChart, SkeletonRoutedChart } from "@/components/ui/skeletons";


import {
    fetchBalancesChartData,
    fetchChannelsChartData,
    fetchFeeChartData,
    fetchNodePerformanceChartData,
    fetchRoutedChartData
} from "@/lib/data";
import { Suspense } from "react";

export default async function OverviewSection() {


    return (
        <div className="grid grid-cols-6 gap-5">
            <div className="col-span-6 lg:col-span-2">
                <Suspense fallback={<SkeletonBalancesChart />}>
                    <_BalancesChart />
                </Suspense>
            </div>
            <div className="col-span-6 lg:col-span-2">
                <Suspense fallback={<SkeletonActiveChannelsChart />}>
                    <_ActiveChannelsChart />
                </Suspense>

            </div>
            <div className="col-span-6 lg:col-span-2">
                <Suspense fallback={<SkeletonLiquidityChart />}>
                    <_LiquidityChart />
                </Suspense>

            </div>
            <div className="col-span-6 lg:col-span-3">
                <Suspense fallback={<SkeletonNodePerformanceChart />}>
                    <_NodePerformanceChart />
                </Suspense>
            </div>
            <div className="col-span-6 lg:col-span-3">
                <Suspense fallback={<SkeletonFeesChart />}>
                    <_FeesChart />
                </Suspense>
            </div>
            <div className="col-span-6 lg:col-span-6">
                <Suspense fallback={<SkeletonRoutedChart />}>
                    <_RoutedChart />
                </Suspense>
            </div>
        </div>
    )
}

async function _BalancesChart() {

    const balanceChartData = await fetchBalancesChartData();

    return (
        <BalancesChart chartData={balanceChartData} />

    )
}

async function _ActiveChannelsChart() {

    const chartData = await fetchChannelsChartData();

    return (
        <ActiveChannelsChart chartData={chartData.channelsChartData} />

    )
}

async function _LiquidityChart() {

    const chartData = await fetchChannelsChartData();

    return (
        <LiquidityChart chartData={chartData.liquidityChartData} />

    )
}

async function _NodePerformanceChart() {
    const chartData = await fetchNodePerformanceChartData();

    return (
        <NodePerformanceChart chartData={chartData} />


    )
}

async function _FeesChart() {

    const chartData = await fetchFeeChartData();

    return (
        <FeesChart chartData={chartData} />

    )
}

async function _RoutedChart() {

    const chartData = await fetchRoutedChartData();


    return (
        <RoutedChart chartData={chartData} />

    )
}