import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import {
  AggregatedData,
  DecodedPayloadType,
  Stat,
  UnaggregatedData,
} from "./definitions";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Decoding JWT without external libraries
export function jwtDecode(token: string) {
  const payload = token.split(".")[1];

  const decodedPayload: DecodedPayloadType = JSON.parse(
    Buffer.from(payload, "base64").toString("utf8"),
  );
  // console.log(decodedPayload)
  return decodedPayload;
}

export function AggregatedValueByDay(
  data: UnaggregatedData[],
): AggregatedData[] {
  const aggregated: { [date: string]: number } = {};

  // Loop through the results
  data.forEach((item) => {
    // Extract the date part (YYYY-MM-DD) from the ISO 8601 string
    const date = item.date.split("T")[0];

    // Aggregate the fees by date
    if (!aggregated[date]) {
      aggregated[date] = 0;
    }
    aggregated[date] += item.value;
  });

  // Convert the aggregated object into an array of AggregatedData
  return Object.entries(aggregated).map(([date, value]) => ({
    date,
    value,
  }));
}


export const getLastNumDays = (num: number) => {

  const Last7Days = Array.from({ length: num }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - i);
    return date.toISOString().split("T")[0];
  }
  )
  return Last7Days

}

export function getPastDate(daysAgo: number) {
  const pastDate = new Date();
  pastDate.setDate(pastDate.getDate() - daysAgo);
  return pastDate.toISOString().split('T')[0]; // Returns in "YYYY-MM-DD" format
}


export function aggregateStatData(stat: Stat): number {
  const values = stat.data.map(d => d.value);

  switch (stat.aggregationType) {
    case "min":
      return Math.min(...values);
    case "max":
      return Math.max(...values);
    case "sum":
      return values.reduce((acc, val) => acc + val, 0);
    case "avg":
      return values.length > 0 ? values.reduce((acc, val) => acc + val, 0) / values.length : 0;
    case "count":
      return values.length;
    default:
      throw new Error("Invalid aggregation type");
  }
}
