"use server";

import {
  BalancesChartData,
  BalancesApiData,
  ChannelsChartData,
  LiquidityChartData,
  ChannelsDataApi,
  FeesChartData,
  UnaggregatedData,
  ForwardsDataApi,
  OnChainDataApi,
  PaymentsDataApi,
  AggregatedData,
} from "./definitions";
import { verifySession } from "@/app/auth/sessions";
import { AggregatedValueByDay, getLast7Days } from "./utils";

export async function getDataFromApi(apiEndPoint: string) {
  const API_URL = process.env.API_URL;

  const { isAuth, accessToken } = await verifySession();

  if (!isAuth) {
    throw new Error("Unauthorized: No access token");
  }

  const res = await fetch(`${API_URL}/api/${apiEndPoint}/`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    throw new Error("Failed to fetch protected data");
  }
  const data = await res.json();

  return data;
}

export async function fetchBalancesChartData() {
  const data = await getDataFromApi("balances");

  const balanceData: BalancesApiData = data.data;

  const balanceChartData: BalancesChartData[] = Object.entries(balanceData).map(
    ([key, value]) => ({
      item: key,
      value,
      fill: `var(--color-${key})`,
    }),
  );

  return balanceChartData;
}

export async function fetchChannelsChartData() {
  const data: ChannelsDataApi = await getDataFromApi("channels");

  const ChannelsChartData: ChannelsChartData[] = [
    {
      status: "activeChannels",
      value: data.results.reduce(
        (count, channel) =>
          channel.is_active && channel.is_open ? count + 1 : count,
        0,
      ),
      fill: "var(--color-activeChannels)",
    },
    {
      status: "inactiveChannels",
      value: data.results.reduce(
        (count, channel) =>
          !channel.is_active && channel.is_open ? count + 1 : count,
        0,
      ),
      fill: "var(--color-inactiveChannels)",
    },
  ];

  const LiquidityChartData: LiquidityChartData[] = [
    {
      status: "outbound",
      value: data.results.reduce(
        (sum, channel) => sum + channel.local_balance,
        0,
      ),
      fill: "var(--color-outbound)",
    },
    {
      status: "inbound",
      value: data.results.reduce(
        (sum, channel) => sum + channel.remote_balance,
        0,
      ),
      fill: "var(--color-inbound)",
    },
    {
      status: "unsettled",
      value: data.results.reduce(
        (sum, channel) => sum + channel.unsettled_balance,
        0,
      ),
      fill: "var(--color-unsettled)",
    },
  ];

  return { ChannelsChartData, LiquidityChartData };
}

export async function fetchFeeChartData() {
  // forwards api has all the "fees" earned so you can calculate the last 7 days worth of fees earned
  const forwardsData: ForwardsDataApi = await getDataFromApi("forwards");
  // onchain api has all the "fees" on chain so you can calculate the last 7 days worth of on chain fees

  const onchainData: OnChainDataApi = await getDataFromApi("onchain");
  // payments api has all the "fees" paid so you can calculate the last 7 days worth of fees paid
  const paymentsData: PaymentsDataApi = await getDataFromApi("payments");

  const forwardsDataRaw: UnaggregatedData[] = forwardsData.results.map(
    (forward) => ({
      date: forward.forward_date,
      value: forward.fee,
    }),
  );

  const forwardsByDay: AggregatedData[] = AggregatedValueByDay(forwardsDataRaw);

  const onchainDataRaw: UnaggregatedData[] = onchainData.results.map(
    (onchain) => ({
      date: onchain.time_stamp,
      value: onchain.fee,
    }),
  );

  const onchainByDay: AggregatedData[] = AggregatedValueByDay(onchainDataRaw);

  const paymentsDataRaw: UnaggregatedData[] = paymentsData.results.map(
    (payment) => ({
      date: payment.creation_date,
      value: payment.fee,
    }),
  );

  const paymentsByDay: AggregatedData[] = AggregatedValueByDay(paymentsDataRaw);


  const feesChartDataDict: { [date: string]: FeesChartData } = {};

  for (const date of getLast7Days()) {
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
      feesChartDataDict[entry.date][key] = entry.value ?? 0; // Use value for all datasets
    });
  };

  // Merge each dataset into the combined object
  mergeData(forwardsByDay, "earned");
  mergeData(paymentsByDay, "paid");
  mergeData(onchainByDay, "onchain");

  const feesChartData = Object.values(feesChartDataDict).sort(
    (a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),
  );

  return feesChartData;
}

// all the money made = revenue
// all the money spent = cost
// all profit = revenue - cost (Profit (sats))
// all outbound (sat)
// profit (ppm) = all profit/all outbound

// total routed / outbound = outbound util

// http://localhost:8000/api/forwards/
// http://localhost:8000/api/payments/
// http://localhost:8000/api/onchain/
// http://localhost:8000/api/closures/
// http://localhost:8000/api/invoices/
