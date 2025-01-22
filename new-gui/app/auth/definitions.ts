import { z } from 'zod';

export const LoginFormSchema = z.object({
  username: z.string().min(2, { message: 'Name must be at least 2 characters long.' }),
  password: z.string().min(1, { message: 'Password field must not be empty.' }),
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

export type SessionPayload = {
  accessToken: string;
  refreshToken: string;
};