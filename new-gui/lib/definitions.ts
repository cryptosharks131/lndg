import { z } from "zod";

export const SigninFormSchema = z.object({
  username: z
    .string()
    .min(2, { message: "Name must be at least 2 characters long." })
    .trim(),
  password: z
    .string()
    .min(8, { message: "Be at least 8 characters long" })
    .regex(/[a-zA-Z]/, { message: "Contain at least one letter." })
    .regex(/[0-9]/, { message: "Contain at least one number." })
    .regex(/[^a-zA-Z0-9]/, {
      message: "Contain at least one special character.",
    })
    .trim(),
});

export type FormState =
  | {
    errors?: {
      username?: string[];
      password?: string[];
    };
    message?: string;
  }
  | undefined;

export interface DecodedPayloadType {
  token_type: string;
  exp: number;
  iat: number;
  jti: string;
  user_id: number;
}

export interface SessionTokens {
  accessToken?: string;
  refreshToken?: string;
}

export interface BalancesApiData {
  total_balance: number;
  offchain_balance: number;
  onchain_balance: number;
  confirmed_balance: number;
  unconfirmed_balance: number;
}

export interface BalancesChartData {
  item?: string;
  value?: number;
  fill?: string;
}

export interface NodeInfoApiData {
  version: string;
  num_peers: number;
  synced_to_graph: boolean;
  synced_to_chain: boolean;
  num_active_channels: number;
  num_inactive_channels: number;
  chains: string[];
  block: {
    hash: string;
    height: number;
  };
  balance: {
    limbo: number;
    onchain: number;
    confirmed: number;
    unconfirmed: number;
    total: number;
  };
  pending_open: number | null | unknown;
  pending_closed: number | null | unknown;
  pending_force_closed: number | null | unknown;
  waiting_for_close: number | null | unknown;
  db_size: number;
}

export interface ChannelsDataApi {
  count: number;
  next: string | null;
  previous: string | null;
  results: Channel[];
}

export interface Channel {
  url: string;
  chan_id: string;
  remote_pubkey: string;
  funding_txid: string;
  output_index: number;
  capacity: number;
  local_balance: number; //outbound balance
  remote_balance: number; //inbound balance
  unsettled_balance: number;
  local_commit: number;
  local_chan_reserve: number;
  initiator: boolean;
  local_base_fee: number;
  local_fee_rate: number;
  remote_base_fee: number;
  remote_fee_rate: number;
  is_active: boolean;
  is_open: boolean;
  num_updates: number;
  local_disabled: boolean;
  remote_disabled: boolean;
  last_update: string; // ISO 8601 formatted string
  short_chan_id: string;
  total_sent: number;
  total_received: number;
  private: boolean;
  pending_outbound: number;
  pending_inbound: number;
  htlc_count: number;
  local_cltv: number;
  local_min_htlc_msat: number;
  local_max_htlc_msat: number;
  remote_cltv: number;
  remote_min_htlc_msat: number;
  remote_max_htlc_msat: number;
  alias: string;
  fees_updated: string; // ISO 8601 formatted string
  push_amt: number;
  close_address: string;
  opened_in: number;
  ar_max_cost: number;
  ar_amt_target: number;
  ar_out_target: number;
  ar_in_target: number;
  auto_fees: boolean;
  local_inbound_base_fee: number;
  local_inbound_fee_rate: number;
  remote_inbound_base_fee: number;
  remote_inbound_fee_rate: number;
  auto_rebalance: boolean;
  notes: string;
}

export interface ChannelsChartData {
  status: string;
  value: number;
  fill: string;
}

export interface LiquidityChartData {
  status: string;
  value: number;
  fill: string;
}

export interface ForwardData {
  url: string;
  id: number;
  forward_date: string; // ISO 8601 date
  chan_id_in: string;
  chan_id_out: string;
  chan_in_alias: string;
  chan_out_alias: string;
  amt_in_msat: number;
  amt_out_msat: number;
  fee: number;
  inbound_fee: number;
}

export interface UnaggregatedData {
  date: string; // Format: YYYY-MM-DD
  value: number;
}
export interface AggregatedData {
  date: string; // Format: YYYY-MM-DD
  value: number;
}

export interface ForwardsDataApi {
  count: number;
  next: string | null;
  previous: string | null;
  results: ForwardData[];
}

export interface OnChainTransaction {
  url: string;
  tx_hash: string;
  amount: number;
  block_hash: string;
  block_height: number;
  time_stamp: string; // ISO 8601 date
  fee: number;
  label: string;
}

export interface OnChainDataApi {
  count: number;
  next: string | null;
  previous: string | null;
  results: OnChainTransaction[];
}

export interface Payment {
  url: string;
  id: number;
  payment_hash: string;
  creation_date: string; // ISO 8601 date
  value: number;
  fee: number;
  status: number;
  index: number;
  chan_out: string;
  chan_out_alias: string;
  keysend_preimage: string | null;
  message: string | null;
  cleaned: boolean;
  rebal_chan: string | null;
}

export interface PaymentsDataApi {
  count: number;
  next: string | null;
  previous: string | null;
  results: Payment[];
}

export interface FeesChartData {
  date: string; // Format: YYYY-MM-DD
  earned: number;
  paid: number;
  onchain: number;
}

export interface ProfitabilityStats {
  date: string; // Format: YYYY-MM-DD
  paymentsRouted: number; // Number of payments routed
  valueRouted: number; // Total value routed
  revenue: number; // Total revenue generated
  onchainCosts: number; // Total on-chain costs
  offchainCost: number; // Total off-chain costs
  offchainCostPpm: number; // Off-chain cost per million
  percentCosts: number; // Percentage of costs relative to revenue
  profit: number; // Total profit
  profitPpm: number; // Profit per million
}