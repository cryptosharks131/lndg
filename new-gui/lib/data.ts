"use server";

import {
  BalancesChartData,
  BalancesApiData,
  ChannelsChartData,
  LiquidityChartData,
  FeesChartData,
  UnaggregatedData,
  AggregatedData,
  Channel,
  Payment,
  Forward,
  OnChainTransaction,
  NodePerformanceChartData,
  ProfitabilityStats,
  Closure
} from "./definitions";
import { verifySession } from "@/app/auth/sessions";
import { AggregatedValueByDay, getDaysFromDateRange, getLastNumDays, getPastDate } from "./utils";
import { DateRange } from "react-day-picker";
import { format } from "date-fns";


const API_URL = process.env.API_URL;

export async function getDataFromApi<T>(
  apiURL: string,
  limit: number = 100,
  offset: number = 0,
  accumulate: boolean = false,
  startDate: { attribute: string; date: string } | false = false,
  endDate: { attribute: string; date: string } | false = false,
  filters: Record<string, string | number | boolean> = {}, // Additional filters
  results: T[] = []
): Promise<T | T[]> {
  const { isAuth, accessToken } = await verifySession();

  if (!isAuth) {
    throw new Error("Unauthorized: No access token");
  }

  let nextUrl = `${apiURL}/?limit=${limit}&offset=${offset}`;

  if (startDate) {
    nextUrl += `&${startDate.attribute}__gte=${encodeURIComponent(startDate.date)}`;
  }
  if (endDate) {
    nextUrl += `&${endDate.attribute}__lte=${encodeURIComponent(endDate.date)}`;
  }

  // Append additional filters dynamically
  for (const [key, value] of Object.entries(filters)) {
    nextUrl += `&${key}=${encodeURIComponent(value)}`;
  }

  console.log(
    "api should be calling this url", nextUrl
  )

  const res = await fetch(nextUrl, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    throw new Error("Failed to fetch protected data");
  }

  const data = await res.json();

  // If data doesn't have results property, it's a single object response
  if (!data.results) {
    return data as T;
  }

  // Handle array results
  results.push(...data.results);

  if (accumulate && data.next) {
    return getDataFromApi(apiURL, limit, offset + limit, accumulate, startDate, endDate, filters, results);
  }

  return results;
}


export async function fetchBalancesChartData() {
  const data = await getDataFromApi<BalancesApiData>(`${API_URL}/balances`, 100, 0);
  // Check if data is valid and is an array with at least one element

  if (!Array.isArray(data) || data.length === 0 || !data[0]) {
    console.warn("No balance data available or invalid data received from API.");
    return []; // Return empty array gracefully
  }

  try {

    const balanceChartData: BalancesChartData[] = Object.entries(data[0]).map((item) => ({
      item: item[0],
      value: item[1],
      fill: `var(--color-${item[0]})`,
    }))

    return balanceChartData;

  } catch (error) {
    console.error("Error parsing balance data:", error);
    return [];
  }
}

export async function fetchChannelsChartData() {
  const channelsResponse = await getDataFromApi<Channel>(`${API_URL}/channels`, 100, 0, true);
  const channels = channelsResponse as Channel[];

  // Filter out active and open channels
  const activeChannels: Channel[] = channels.filter(
    (channel) => channel.is_active && channel.is_open,
  );

  const channelsChartData: ChannelsChartData[] = [
    {
      status: "activeChannels",
      value: channels.reduce(
        (count, channel) =>
          channel.is_active && channel.is_open ? count + 1 : count,
        0,
      ),
      fill: "var(--color-activeChannels)",
    },
    {
      status: "inactiveChannels",
      value: channels.reduce(
        (count, channel) =>
          !channel.is_active && channel.is_open ? count + 1 : count,
        0,
      ),
      fill: "var(--color-inactiveChannels)",
    },
  ];



  const liquidityChartData: LiquidityChartData[] = [
    {
      status: "outbound",
      value: activeChannels.reduce(
        (sum, channel) => sum + channel.local_balance,
        0,
      ),
      fill: "var(--color-outbound)",
    },
    {
      status: "inbound",
      value: activeChannels.reduce(
        (sum, channel) => sum + channel.remote_balance,
        0,
      ),
      fill: "var(--color-inbound)",
    },
    {
      status: "unsettled",
      value: activeChannels.reduce(
        (sum, channel) => sum + channel.unsettled_balance,
        0,
      ),
      fill: "var(--color-unsettled)",
    },
  ];

  return { channelsChartData, liquidityChartData };
}

export async function fetchFeeChartData() {

  const sevenDaysAgo = getPastDate(7)

  // forwards api has all the "fees" earned so you can calculate the last 7 days worth of fees earned
  const forwardsResponse = await getDataFromApi<Forward>(`${API_URL}/forwards`, 100, 0, true, { attribute: "forward_date", date: sevenDaysAgo });
  const forwardsData = forwardsResponse as Forward[];
  // onchain api has all the "fees" on chain so you can calculate the last 7 days worth of on chain fees

  const onchainDataResponse = await getDataFromApi<OnChainTransaction>(`${API_URL}/onchain`, 100, 0, true, { attribute: "time_stamp", date: sevenDaysAgo });
  const onchainData = onchainDataResponse as OnChainTransaction[];

  // payments api has all the "fees" paid so you can calculate the last 7 days worth of fees paid
  const paymentsDataResponse = await getDataFromApi<Payment>(`${API_URL}/payments`, 100, 0, true, { attribute: "creation_date", date: sevenDaysAgo });
  const paymentsData = paymentsDataResponse as Payment[];


  const forwardsDataRaw: UnaggregatedData[] = forwardsData.map(
    (forward) => ({
      date: forward.forward_date,
      value: forward.fee,
    }),
  );

  const forwardsByDay: AggregatedData[] = AggregatedValueByDay(forwardsDataRaw);

  const onchainDataRaw: UnaggregatedData[] = onchainData.map(
    (onchain) => ({
      date: onchain.time_stamp,
      value: onchain.fee,
    }),
  );

  const onchainByDay: AggregatedData[] = AggregatedValueByDay(onchainDataRaw);

  const paymentsDataRaw: UnaggregatedData[] = paymentsData.map(
    (payment) => ({
      date: payment.creation_date,
      value: payment.fee,
    }),
  );

  const paymentsByDay: AggregatedData[] = AggregatedValueByDay(paymentsDataRaw);


  const feesChartDataDict: { [date: string]: FeesChartData } = {};

  for (const date of getLastNumDays(7)) {
    feesChartDataDict[date] = {
      date,
      earned: 0,
      paid: 0,
      onchain: 0,
    };
  }


  const mergeData = (
    data: AggregatedData[],
    key: "earned" | "paid" | "onchain",
  ) => {
    data.forEach((entry) => {
      if (entry.date in feesChartDataDict) {
        feesChartDataDict[entry.date][key] = entry.value ?? 0;
      }
    });
  };


  mergeData(forwardsByDay, "earned");
  mergeData(paymentsByDay, "paid");
  mergeData(onchainByDay, "onchain");

  const feesChartData = Object.values(feesChartDataDict).sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  );

  return feesChartData;
}


export async function fetchRoutedChartData() {

  const thirtyDaysAgo = getPastDate(30)

  const forwardsResponse = await getDataFromApi<Forward>(`${API_URL}/forwards`, 100, 0, true, { attribute: "forward_date", date: thirtyDaysAgo });
  const forwardsData = forwardsResponse as Forward[];




  const forwardsDataRaw: UnaggregatedData[] = forwardsData.map(
    (forward) => ({
      date: forward.forward_date,
      value: forward.amt_out_msat / 1000,
    }),
  );


  const forwardsByDay: AggregatedData[] = AggregatedValueByDay(forwardsDataRaw);


  const routedChartData: AggregatedData[] = getLastNumDays(30).map((date) => {
    const routed = forwardsByDay.find((forward) => forward.date === date)?.value ?? 0;
    return (
      { date: date, value: routed }
    )
  });


  routedChartData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());


  return routedChartData

}


export async function fetchNodePerformanceChartData() {


  const sevenDaysAgo = getPastDate(7)

  // forwards api has all the "fees" earned so you can calculate the last 7 days worth of fees earned
  const forwardsResponse = await getDataFromApi<Forward>(`${API_URL}/forwards`, 100, 0, true, { attribute: "forward_date", date: sevenDaysAgo });
  const forwardsData = forwardsResponse as Forward[];
  // onchain api has all the "fees" on chain so you can calculate the last 7 days worth of on chain fees

  const onchainDataResponse = await getDataFromApi<OnChainTransaction>(`${API_URL}/onchain`, 100, 0, true, { attribute: "time_stamp", date: sevenDaysAgo });
  const onchainData = onchainDataResponse as OnChainTransaction[];

  // payments api has all the "fees" paid so you can calculate the last 7 days worth of fees paid
  const paymentsDataResponse = await getDataFromApi<Payment>(`${API_URL}/payments`, 100, 0, true, { attribute: "creation_date", date: sevenDaysAgo });
  const paymentsData = paymentsDataResponse as Payment[];
  const balanceChartData = await fetchBalancesChartData();

  const total_outbound = balanceChartData.find((item) => item.item === "offchain_balance")?.value ?? 1;

  const revenue: UnaggregatedData[] = forwardsData.map((forward) => ({ date: forward.forward_date, value: forward.fee }));
  const revenueByDay: AggregatedData[] = AggregatedValueByDay(revenue);

  const offchain: UnaggregatedData[] = paymentsData.map((payment) => ({ date: payment.creation_date, value: payment.fee }));
  const offchainByDay: AggregatedData[] = AggregatedValueByDay(offchain);

  const onchain: UnaggregatedData[] = onchainData.map((onchain) => ({ date: onchain.time_stamp, value: onchain.fee }));

  const costs: UnaggregatedData[] = [...offchain, ...onchain];
  const costsByDay: AggregatedData[] = AggregatedValueByDay(costs);




  const nodePerformanceChartData: NodePerformanceChartData[] = getLastNumDays(7).map((date) => {
    const revenueValue = revenueByDay.find((entry) => entry.date === date)?.value ?? 0;
    const offchainValue = offchainByDay.find((entry) => entry.date === date)?.value ?? 0;
    const onchainValue = costsByDay.find((entry) => entry.date === date)?.value ?? 0;

    return {
      date,
      profit: (revenueValue - offchainValue) * 1000000 / total_outbound,
      profitOnChain: (revenueValue - onchainValue) * 1000000 / total_outbound,
      utilization: revenueValue * 1000000 / total_outbound,
    };
  });

  // sort ascending date 
  nodePerformanceChartData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  return nodePerformanceChartData

}

export async function fetchProfitabilityData(dateRange: DateRange) {

  if (!dateRange.from || !dateRange.to) {
    return []
  }

  verifySession()

  // Helper function to format date as 'YYYY-MM-DD'
  const formatDate = (date: Date) => {
    try {
      const formattedDate = format(date, "yyyy-MM-dd")
      return formattedDate
    } catch {
      console.log("date conversion error", date)
    }
  };

  // console.log(dateRange)

  const forwardsDataApiResponse = await getDataFromApi<Forward>(
    `${API_URL}/forwards`,
    1000,
    0,
    true,
    { attribute: "forward_date", date: dateRange.from?.toISOString().split('T')[0] },
    { attribute: "forward_date", date: dateRange.to?.toISOString().split('T')[0] }
  );
  // console.log(forwardsDataApi)
  const forwardsDataApi = forwardsDataApiResponse as Forward[]
  const forwardsDataRaw = forwardsDataApi.map(
    (forward) => ({
      date: formatDate(new Date(forward.forward_date)),
      revenue: forward.fee,
      valueRouted: forward.amt_out_msat / 1000
    }),
  );


  const onChainDataApiResponse = await getDataFromApi<OnChainTransaction>(
    `${API_URL}/onchain`,
    1000,
    0,
    true,
    { attribute: "time_stamp", date: dateRange.from?.toISOString().split('T')[0] },
    { attribute: "time_stamp", date: dateRange.to?.toISOString().split('T')[0] }
  );

  const onChainDataApi = onChainDataApiResponse as OnChainTransaction[]
  // console.log(onChainDataApi)
  const onChainDataRaw = onChainDataApi.map(
    (onchain) => ({
      date: formatDate(new Date(onchain.time_stamp)),
      onchainCosts: onchain.fee
    }),
  );

  const paymentsDataApiResponse = await getDataFromApi<Payment>(
    `${API_URL}/payments`,
    1000,
    0,
    true,
    { attribute: "creation_date", date: dateRange.from?.toISOString().split('T')[0] },
    { attribute: "creation_date", date: dateRange.to?.toISOString().split('T')[0] },
    { status: 2 }
  );

  const paymentsDataApi = paymentsDataApiResponse as Payment[]


  const paymentsDataRaw = paymentsDataApi.map(
    (payment) => ({
      date: formatDate(new Date(payment.creation_date)),
      offchainCost: payment.fee
    }),
  );

  const closuresDataApiResponse = await getDataFromApi<Closure>(
    `${API_URL}/closures`,
    1000,
    0,
    true,
    { attribute: "closure_date", date: dateRange.from?.toISOString().split('T')[0] },
    { attribute: "closure_date", date: dateRange.to?.toISOString().split('T')[0] }
  );

  const closuresDataApi = closuresDataApiResponse as Closure[]

  const closuresDataRaw = closuresDataApi.map(
    (closure) => ({
      date: formatDate(new Date(closure.closure_date)),
      closingCost: closure.closing_costs
    }),
  );


  const profitabilityStatsData: ProfitabilityStats[] = getDaysFromDateRange(dateRange).map((date) => {
    const revenue = forwardsDataRaw.filter((forward) => forward.date === date).reduce((acc, forward) => acc + forward.revenue, 0);
    const valueRouted = forwardsDataRaw.filter((forward) => forward.date === date).reduce((acc, forward) => acc + forward.valueRouted, 0);
    const onchainCosts = onChainDataRaw.filter((onchain) => onchain.date === date).reduce((acc, onchain) => acc + onchain.onchainCosts, 0) + closuresDataRaw.filter((closure) => closure.date === date).reduce((acc, closure) => acc + closure.closingCost, 0);
    const offchainCost = paymentsDataRaw.filter((payment) => payment.date === date).reduce((acc, payment) => acc + payment.offchainCost, 0);
    const offchainCostPpm = valueRouted ? offchainCost * 1000000 / valueRouted : 0;
    const percentCosts = revenue ? (onchainCosts + offchainCost) / revenue : 0;
    // const profit = revenue - onchainCosts - offchainCost;
    const profit = revenue - offchainCost;
    const profitPpm = valueRouted ? profit * 1000000 / valueRouted : 0;

    return {
      date,
      paymentsRouted: forwardsDataRaw.filter((forward) => forward.date === date).length,
      valueRouted,
      revenue,
      onchainCosts,
      offchainCost,
      offchainCostPpm,
      percentCosts,
      profit,
      profitPpm
    };
  });

  profitabilityStatsData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());


  return profitabilityStatsData

}

