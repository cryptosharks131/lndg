import AnalyticsFilterPane from "@/components/dashboard/analytics-filter-pane";
import ProfitabilitySection from "./profitability";
import { subDays } from "date-fns";
import { DateRange } from "react-day-picker";
import { Suspense } from "react";
import { SkeletonProfitabilityChartSection } from "@/components/ui/skeletons";



export default async function ProfitabilityPage(props: {
    searchParams?: Promise<{
        to?: string;
        from?: string;
    }>;
}) {
    const searchParams = await props.searchParams;

    const from = searchParams?.from ? new Date(searchParams?.from) : subDays(new Date(), 7);
    const to = searchParams?.to ? new Date(searchParams?.to) : new Date();

    const dateRange = {
        from: new Date(from),
        to: new Date(to),
    }


    return <>
        <AnalyticsFilterPane />
        <Suspense key={to.toDateString() + from.toDateString()} fallback={<SkeletonProfitabilityChartSection />}>
            <ProfitabilitySection dateRange={dateRange} />
        </Suspense>
    </>
}
