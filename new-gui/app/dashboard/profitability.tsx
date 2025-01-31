'use client'

import { addDays, format, subDays } from "date-fns"

import { ProfitabilityStatsChartAgg } from "@/components/dashboard/profitability/profitability-stats-agg";
import { DateRangePicker } from "@/components/date-range-picker";
import { useState, useEffect } from "react";
import { DateRange } from "react-day-picker";
import { ProfitabilityStats } from "@/lib/definitions";
import { fetchProfitabilityData } from "@/lib/data";




export default function ProfitabilitySection() {
  // State for date range
  const [dateRange, setDateRange] = useState<DateRange>({
    from: subDays(new Date(), 30),
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
    setDateRange(range ?? { from: subDays(new Date(), 30), to: new Date() });
  };

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
      </div>
    </>
  );
}
