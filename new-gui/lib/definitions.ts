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

export const LoginFormSchema = z.object({
  username: z
    .string()
    .min(2, { message: "Name must be at least 2 characters long." }),
  password: z.string().min(1, { message: "Password field must not be empty." }),
});

export type LoginFormState =
  | {
    errors?: {
      username?: string[];
      password?: string[];
    };
    message?: string;
  }
  | undefined;

export type SessionPayload = {
  accessToken: string;
  refreshToken: string;
};

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
  pending_open: ChannelPendingOpen[] | null;
  pending_closed: ChannelPendingClose[] | null;
  pending_force_closed: ChannelPendingForceClose[] | null;
  waiting_for_close: ChannelWaitingToClose[] | null;
  db_size: number;
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

export interface ChannelWaitingToClose {
  remote_node_pub: string;
  channel_point: string;
  capacity: number;
  local_balance: number;
  remote_balance: number;
  local_chan_reserve_sat: number;
  remote_chan_reserve_sat: number;
  initiator: number;
  commitment_type: number;
  local_commit_fee_sat: number;
  limbo_balance: number;
  closing_txid: string;
  short_chan_id: string;
  chan_id: string;
  alias: string;
}

export interface ChannelPendingOpen {
  alias: string;
  remote_node_pub: string;
  channel_point: string;
  funding_txid: string;
  output_index: string; // provided as a string (e.g. "0"); convert to number if needed
  capacity: number;
  local_balance: number;
  remote_balance: number;
  local_chan_reserve_sat: number;
  remote_chan_reserve_sat: number;
  initiator: number;
  commitment_type: number;
  commit_fee: number;
  commit_weight: number;
  fee_per_kw: number;
  local_base_fee: string;
  local_fee_rate: string;
  local_cltv: string;
  auto_rebalance: boolean;
  ar_amt_target: number;
  ar_in_target: number;
  ar_out_target: number;
  ar_max_cost: number;
  auto_fees: boolean;
}

export interface ChannelPendingClose {
  remote_node_pub: string;
  channel_point: string;
  capacity: number;
  local_balance: number;
  remote_balance: number;
  local_chan_reserve_sat: number;
  remote_chan_reserve_sat: number;
  initiator: number;
  commitment_type: number;
  local_commit_fee_sat: number;
  limbo_balance: number;
  closing_txid: string;
}

export interface ChannelPendingForceClose {
  remote_node_pub: string;
  channel_point: string;
  capacity: number;
  local_balance: number;
  remote_balance: number;
  initiator: number;
  commitment_type: number;
  closing_txid: string;
  limbo_balance: number;
  maturity_height: number;
  blocks_til_maturity: number;
  maturity_datetime: string; // ISO 8601 formatted date string
  short_chan_id: string;
  chan_id: string;
  alias: string;
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

export interface Forward {
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

export interface NodePerformanceChartData {
  date: string;
  profit: number;
  profitOnChain: number;
  utilization: number;

}

export interface Stat {
  name: string;
  description: string;
  color: string;
  data: AggregatedData[]
  aggregationType: "min" | "max" | "sum" | "avg" | "count"
}

interface Node {
  name: string;
}

interface Link {
  source: number;
  target: number;
  value: number;
  color?: string; // Optional since not all links have a color
}

export interface ChannelPerformanceSankeyChartData {
  nodes: Node[];
  links: Link[];
}

export interface Closure {
  url: string;
  id: number;
  closure_date: string;
  chan_id: string;
  funding_txid: string;
  funding_index: number;
  closing_tx: string;
  remote_pubkey: string;
  capacity: number;
  close_height: number;
  settled_balance: number;
  time_locked_balance: number;
  close_type: number;
  open_initiator: number;
  close_initiator: number;
  resolution_count: number;
  closing_costs: number;
}


export const OpenChannelFormSchema = z.object({
  publicKey: z
    .string()
    .min(66, { message: "Public Key must be at least 66 characters long." })
    .max(66, { message: "Public Key must be no longer than 66 characters" })
    .regex(
      /^[a-fA-F0-9]{66}$/,
      "Invalid format. Expected a 66-character hexadecimal string."
    ),
  capacity: z.number().min(1, { message: "Capacity must not be empty" }),
  fee: z.number().min(1, { message: "Fee must not be empty" }),
});

export interface OpenChannelFormData {
  publicKey: string;
  capacity: number;
  fee: number;
}

export type OpenChannelFormState =
  | {
    errors?: {
      success?: boolean;
      publicKey?: string[];
      capacity?: string[];
      fee?: string[];
    };
    success?: boolean;
    message?: string;
    inputs?: OpenChannelFormData;
  }
  | undefined;


export const UpdateChannelInboundFeesFormSchema = z.object({
  chanId: z
    .string()
    .min(1, { message: "Channel Id must be at least 1 characters long." })
    .max(20, { message: "Channel Id must be no longer than 20 characters" })
    .regex(
      /^([1-9]?[0-9]{1,18}|[1-9][0-9]{18,18}|1844674407370955161[0-5])$/,
      "Invalid format. Expected a 19-character hexadecimal string."
    ),
  baseFee: z.number().max(0, { message: "Base Fee must be negative" }),
  feeRate: z.number().max(0, { message: "Fee Rate must be negative" }),
});

export interface UpdateChannelInboundFeesFormData {
  chanId: Channel["chan_id"];
  baseFee: Channel["local_inbound_base_fee"];
  feeRate: Channel["local_inbound_fee_rate"];
}

export type UpdateChannelInboundFeesState =
  | {
    errors?: {
      success?: boolean;
      chanId?: string[];
      baseFee?: string[];
      feeRate?: string[];
    };
    success?: boolean;
    message?: string;
    inputs?: UpdateChannelInboundFeesFormData;

  }


export const UpdateChannelOutboundFeesFormSchema = z.object({
  chanId: z
    .string()
    .min(1, { message: "Channel Id must be at least 1 characters long." })
    .max(20, { message: "Channel Id must be no longer than 20 characters" })
    .regex(
      /^([1-9]?[0-9]{1,18}|[1-9][0-9]{18,18}|1844674407370955161[0-5])$/,
      "Invalid format. Expected a 19-character hexadecimal string."
    ),
  baseFee: z.number().min(0, { message: "Base Fee must be negative" }),
  feeRate: z.number().min(0, { message: "Fee Rate must be negative" }),
});

export interface UpdateChannelOutboundFeesFormData {
  chanId: Channel["chan_id"];
  baseFee: Channel["local_base_fee"];
  feeRate: Channel["local_fee_rate"];
}

export type UpdateChannelOutboundFeesState =
  | {
    errors?: {
      success?: boolean;
      chanId?: string[];
      baseFee?: string[];
      feeRate?: string[];
    };
    success?: boolean;
    message?: string;
    inputs?: UpdateChannelInboundFeesFormData;

  }

