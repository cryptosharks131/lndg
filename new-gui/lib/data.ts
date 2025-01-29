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
  NodePerformanceChartData
} from "./definitions";
import { verifySession } from "@/app/auth/sessions";
import { AggregatedValueByDay, getLastNumDays, getPastDate } from "./utils";


const API_URL = process.env.API_URL + "/api";

export async function getDataFromApi(
  apiURL: string, limit: number = 100, offset: number = 0, accumulate: boolean = false, startDate: { attribute: string, date: string } | false = false, endDate: { attribute: string, date: string } | false = false, results: any[] = []) {

  const { isAuth, accessToken } = await verifySession();

  if (!isAuth) {
    throw new Error("Unauthorized: No access token");
  }

  let nextUrl = `${apiURL}/?limit=${limit}&offset=${offset}`;
  if (startDate) {
    nextUrl += `&${startDate.attribute}__gt=${encodeURIComponent(startDate.date)}`;
  }
  if (endDate) {
    nextUrl += `&${endDate.attribute}__lt=${encodeURIComponent(endDate.date)}`;
  }

  const res = await fetch(nextUrl, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    throw new Error("Failed to fetch protected data");
  }

  const data = await res.json();
  results = [...results, ...data.results];

  if (accumulate && data.next) {
    return getDataFromApi(apiURL, limit, offset + limit, accumulate, startDate, endDate, results);
  }

  return results;
}



export async function fetchBalancesChartData() {
  const data: BalancesApiData[] = await getDataFromApi(`${API_URL}/balances`, 100, 0);

  const balanceChartData: BalancesChartData[] = Object.entries(data[0]).map((item) => ({
    item: item[0],
    value: item[1],
    fill: `var(--color-${item[0]})`,
  }))



  return balanceChartData;
}

export async function fetchChannelsChartData() {
  const channels: Channel[] = await getDataFromApi(`${API_URL}/channels`, 100, 0, true);

  // Filter out active and open channels
  const activeChannels = channels.filter(
    (channel) => channel.is_active && channel.is_open,
  );

  const ChannelsChartData: ChannelsChartData[] = [
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



  const LiquidityChartData: LiquidityChartData[] = [
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

  return { ChannelsChartData, LiquidityChartData };
}

export async function fetchFeeChartData() {

  const sevenDaysAgo = getPastDate(7)

  // forwards api has all the "fees" earned so you can calculate the last 7 days worth of fees earned
  const forwardsData: Forward[] = await getDataFromApi(`${API_URL}/forwards`, 100, 0, true, { attribute: "forward_date", date: sevenDaysAgo });
  // onchain api has all the "fees" on chain so you can calculate the last 7 days worth of on chain fees

  const onchainData: OnChainTransaction[] = await getDataFromApi(`${API_URL}/onchain`, 100, 0, true, { attribute: "time_stamp", date: sevenDaysAgo });
  // payments api has all the "fees" paid so you can calculate the last 7 days worth of fees paid
  const paymentsData: Payment[] = await getDataFromApi(`${API_URL}/payments`, 100, 0, true, { attribute: "creation_date", date: sevenDaysAgo });

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

  const forwardsData: Forward[] = await getDataFromApi(`${API_URL}/forwards`, 100, 0, true, { attribute: "forward_date", date: thirtyDaysAgo });




  const forwardsDataRaw: UnaggregatedData[] = forwardsData.map(
    (forward) => ({
      date: forward.forward_date,
      value: forward.amt_out_msat,
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

  const forwardsData: Forward[] = await getDataFromApi(`${API_URL}/forwards`, 100, 0, true, { attribute: "forward_date", date: sevenDaysAgo });

  const onchainData: OnChainTransaction[] = await getDataFromApi(`${API_URL}/onchain`, 100, 0, true, { attribute: "time_stamp", date: sevenDaysAgo });

  const paymentsData: Payment[] = await getDataFromApi(`${API_URL}/payments`, 100, 0, true, { attribute: "creation_date", date: sevenDaysAgo });

  const balanceChartData = await fetchBalancesChartData();

  const total_outbound = balanceChartData.find((item) => item.item === "offchain_balance")?.value ?? 1;

  const earned: UnaggregatedData[] = forwardsData.map((forward) => ({ date: forward.forward_date, value: forward.fee }));
  const earnedByDay: AggregatedData[] = AggregatedValueByDay(earned);

  const offchain: UnaggregatedData[] = paymentsData.map((payment) => ({ date: payment.creation_date, value: payment.fee }));
  const offchainByDay: AggregatedData[] = AggregatedValueByDay(offchain);

  const onchain: UnaggregatedData[] = onchainData.map((onchain) => ({ date: onchain.time_stamp, value: onchain.fee }));

  const costs: UnaggregatedData[] = [...offchain, ...onchain];
  const costsByDay: AggregatedData[] = AggregatedValueByDay(costs);




  const nodePerformanceChartData: NodePerformanceChartData[] = getLastNumDays(7).map((date) => {
    const earnedValue = earnedByDay.find((entry) => entry.date === date)?.value ?? 0;
    const offchainValue = offchainByDay.find((entry) => entry.date === date)?.value ?? 0;
    const onchainValue = costsByDay.find((entry) => entry.date === date)?.value ?? 0;

    return {
      date,
      profit: (earnedValue - offchainValue) * 1000000 / total_outbound,
      profitOnChain: (earnedValue - onchainValue) * 1000000 / total_outbound,
      utilization: earnedValue * 1000000 / total_outbound,
    };
  });

  // sort ascending date 
  nodePerformanceChartData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());

  return nodePerformanceChartData

}


// export async function fetchNodePerformanceChartData() {

//   const forwardsData: ForwardsDataApi = await getDataFromApi("forwards");

//   const onchainData: OnChainDataApi = await getDataFromApi("onchain");

//   const paymentsData: PaymentsDataApi = await getDataFromApi("payments");


// } 


// earned = forwards (in + out)
// offchain fee = payments 
// costs = offchain + onchain 

// all the money made = revenue
// byId(`profit_per_outbound_${ d }d`).innerHTML = '⚡${((earned - offchain.fee) * 1000000 / total_outbound).intcomma()}ₚₚₘ</span>
// ⛓️${((earned - costs) * 1000000 / total_outbound).intcomma()}ₚₚₘ</span>`
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
