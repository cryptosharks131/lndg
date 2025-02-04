'use client'

import { subDays } from "date-fns"

import { ProfitabilityStatsChartAgg } from "@/components/dashboard/profitability/profitability-stats-agg";
import { DateRangePicker } from "@/components/date-range-picker";
import { useState, useEffect } from "react";
import { DateRange } from "react-day-picker";
import { ProfitabilityStats, Stat } from "@/lib/definitions";
import { fetchProfitabilityData } from "@/lib/data";
import { ProfitabilityStat } from "@/components/dashboard/profitability/profitability-stat";




export default function ProfitabilitySection() {
  // State for date range
  const [dateRange, setDateRange] = useState<DateRange>({
    from: subDays(new Date(), 7),
    to: new Date(),
  });

  // State to store fetched profitability data
  const [profitabilityChartData, setProfitabilityChartData] = useState<ProfitabilityStats[]>([]);

  // Fetch data when dateRange changes
  useEffect(() => {
    const fetchData = async () => {
      if (!dateRange.from || !dateRange.to) return; // Prevent fetching if dates are missing

      const data = await fetchProfitabilityData(dateRange);
      setProfitabilityChartData(data);
    };

    fetchData();
  }, [dateRange]); // Runs when dateRange updates

  // Handle date change
  const handleDateChange = (range: DateRange | undefined) => {
    setDateRange(range ?? { from: subDays(new Date(), 7), to: new Date() });
  };


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
      <div className="flex flex-row-reverse p-4">
        <DateRangePicker date={dateRange}
          onDateChange={handleDateChange} />
      </div>
      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12">
          <ProfitabilityStatsChartAgg chartData={profitabilityChartData} />
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
