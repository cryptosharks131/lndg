import { Skeleton } from "@/components/ui/skeleton"

export function SkeletonChannelCard() {
    return (
        <>
            <div className="flex flex-col space-y-3">
                <Skeleton className="h-36 w-full rounded-xl" />
            </div>
        </>
    )
}

export function SkeletonBalancesChart() {
    return (
        <div className="flex flex-col space-y-3">
            <div className="space-y-2">
                <Skeleton className="h-4 w-[200px]" />
                <Skeleton className="h-4 w-[250px]" />
            </div>
            <Skeleton className="h-80 w-full rounded-xl" />
        </div>
    )

}
export function SkeletonActiveChannelsChart() {
    return (
        <div className="flex flex-col space-y-3">
            <div className="space-y-2">
                <Skeleton className="h-4 w-[200px]" />
                <Skeleton className="h-4 w-[250px]" />
            </div>
            <Skeleton className="h-80 w-full rounded-xl" />
        </div>
    )

}

export function SkeletonLiquidityChart() {
    return (
        <div className="flex flex-col space-y-3">
            <div className="space-y-2">
                <Skeleton className="h-4 w-[200px]" />
                <Skeleton className="h-4 w-[250px]" />
            </div>
            <Skeleton className="h-80 w-full rounded-xl" />
        </div>
    )

}

export function SkeletonNodePerformanceChart() {
    return (
        <div className="flex flex-col space-y-3">
            <div className="space-y-2">
                <Skeleton className="h-4 w-[250px]" />
                <Skeleton className="h-4 w-[200px]" />
            </div>
            <Skeleton className="h-[460px] w-full rounded-xl" />
        </div>
    )

}

export function SkeletonFeesChart() {
    return (
        <div className="flex flex-col space-y-3">
            <div className="space-y-2">
                <Skeleton className="h-4 w-[250px]" />
                <Skeleton className="h-4 w-[200px]" />
            </div>
            <Skeleton className="h-[460px] w-full rounded-xl" />
        </div>
    )

}

export function SkeletonRoutedChart() {
    return (
        <div className="flex flex-col space-y-3">
            <div className="space-y-2">
                <Skeleton className="h-4 w-[250px]" />
                <Skeleton className="h-4 w-[200px]" />
            </div>
            <Skeleton className="h-[460px] w-full rounded-xl" />
        </div>
    )

}

export function SkeletonProfitabilityChartSection() {
    return (
        <>
            <div className="flex flex-col space-y-3">
                <div className="space-y-2">
                    <Skeleton className="h-4 w-[200px]" />
                    <Skeleton className="h-4 w-[300px]" />
                </div>
                <Skeleton className="h-[500px] w-full rounded-xl" />
            </div>

        </>
    )
} 