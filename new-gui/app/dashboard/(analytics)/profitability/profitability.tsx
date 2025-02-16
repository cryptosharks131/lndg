import { ProfitabilityStatsChart } from "@/components/dashboard/profitability/profitability-stats-chart";
import { ProfitabilityStats, Stat } from "@/lib/definitions";
import { ProfitabilityStat } from "@/components/dashboard/profitability/profitability-stat";
import { fetchProfitabilityData } from "@/lib/data";
import { DateRange } from "react-day-picker";




export default async function ProfitabilitySection({ dateRange }: { dateRange: DateRange }) {


  console.log(`fetching data from ${dateRange.from?.toDateString()} to ${dateRange.to?.toDateString()}`)
  // console.log(dateRange)a

  const profitabilityChartData: ProfitabilityStats[] = await fetchProfitabilityData(dateRange)
  // console.log(profitabilityChartData)
  const profitabilityStats: Stat[] =

    [{
      name: "Revenue",
      description: "Total Revenue (sats)",
      color: "hsl(var(--chart-1))",
      data: profitabilityChartData.map((stat) => ({
        date: stat.date,
        value: stat.revenue
      })),
      aggregationType: "sum"
    },
    {
      name: "On-Chain Costs",
      description: "Total On-Chain Costs (sats)",
      color: "hsl(var(--chart-3))",
      data: profitabilityChartData.map((stat) => ({
        date: stat.date,
        value: stat.onchainCosts
      })),
      aggregationType: "sum"

    },
    {
      name: "Off-Chain Costs",
      description: "Total Off-Chain Costs (sats)",
      color: "hsl(var(--chart-2))",
      data: profitabilityChartData.map((stat) => ({
        date: stat.date,
        value: stat.offchainCost
      })),
      aggregationType: "sum"

    },
    {
      name: "Profit",
      description: "Total Profit (sats)",
      color: "hsl(var(--chart-4))",
      data: profitabilityChartData.map((stat) => ({
        date: stat.date,
        value: stat.profit
      })),
      aggregationType: "sum"

    },
    {
      name: "Value Routed",
      description: "Total Value Routed (sats)",
      color: "hsl(var(--chart-5))",
      data: profitabilityChartData.map((stat) => ({
        date: stat.date,
        value: stat.valueRouted
      })),
      aggregationType: "sum"
    },
    {
      name: "Payments Routed",
      description: "Total Payments Routed",
      color: "hsl(var(--chart-3))",
      data: profitabilityChartData.map((stat) => ({
        date: stat.date,
        value: stat.paymentsRouted
      })),
      aggregationType: "sum"
    },
    {
      name: "Costs",
      description: "Total Costs (ppm)",
      color: "hsl(var(--chart-6))",
      data: profitabilityChartData.map((stat) => ({
        date: stat.date,
        value: stat.offchainCostPpm
      })),
      aggregationType: "sum"

    },
    {
      name: "Profitability",
      description: "Total Profitability (ppm)",
      color: "hsl(var(--chart-2))",
      data: profitabilityChartData.map((stat) => ({
        date: stat.date,
        value: stat.profitPpm
      })),
      aggregationType: "sum"

    },
    ]

  return (
    <>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12">
          <ProfitabilityStatsChart chartData={profitabilityChartData} />
        </div>
        {
          profitabilityStats.map((stat) => (
            <div className="col-span-6 lg:col-span-3" key={stat.name}>
              <ProfitabilityStat stat={stat}
              />
            </div>
          ))}

      </div>
    </>
  );
}
