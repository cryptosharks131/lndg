import { ProfitabilityChart } from "@/components/dashboard/profitability/profitability-chart";
import { ProfitabilityStats } from "@/components/dashboard/profitability/profitability-stats";

export default function ProfitabilitySection() {
  return (
    <div className="grid grid-cols-12 gap-4">
      <div className="col-span-12">
        <ProfitabilityChart />
      </div>
      <div className="col-span-12">
        <ProfitabilityStats />
      </div>
    </div>
  );
}
