import { ProfitabilityChart } from "@/components/dashboard/profitability/profitability-chart";
import { ProfitabilityStatsChart } from "@/components/dashboard/profitability/profitability-stats";
import { ProfitabilityStatsChartAgg } from "@/components/dashboard/profitability/profitability-stats-agg";

export default function ProfitabilitySection() {
  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12">
        <ProfitabilityChart />
      </div>
      <div className="col-span-12">
        <ProfitabilityStatsChart />
      </div>
      <div className="col-span-12">
        <ProfitabilityStatsChartAgg />
      </div>
    </div>
  );
}
