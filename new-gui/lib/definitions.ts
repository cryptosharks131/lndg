import { z } from 'zod'
 
export const SigninFormSchema = z.object({
  username: z
    .string()
    .min(2, { message: 'Name must be at least 2 characters long.' })
    .trim(),
  password: z
    .string()
    .min(8, { message: 'Be at least 8 characters long' })
    .regex(/[a-zA-Z]/, { message: 'Contain at least one letter.' })
    .regex(/[0-9]/, { message: 'Contain at least one number.' })
    .regex(/[^a-zA-Z0-9]/, {
      message: 'Contain at least one special character.',
    })
    .trim(),
})
 
export type FormState =
  | {
      errors?: {
        username?: string[]
        password?: string[]
      }
      message?: string
    }
  | undefined



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

