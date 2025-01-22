
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { AggregatedData, DecodedPayloadType, UnaggregatedData } from "./definitions";
import { verifySession } from "@/app/auth/sessions";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// Decoding JWT without external libraries
export function jwtDecode(token: string) {
  const [header, payload, signature] = token.split('.');
  const decodedPayload:DecodedPayloadType = JSON.parse(Buffer.from(payload, 'base64').toString('utf8'));
  // console.log(decodedPayload)
  return decodedPayload;
}


export function AggregatedValueByDay(data: UnaggregatedData[]): AggregatedData[] {
  const aggregated: { [date: string]: number } = {};

  // Loop through the results
  data.forEach((item) => {
    // Extract the date part (YYYY-MM-DD) from the ISO 8601 string
    const date = item.date.split('T')[0];

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
