import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

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

export interface DecodedPayloadType {
  token_type: string;
  exp: number;
  iat: number;
  jti: string;
  user_id: number;
}