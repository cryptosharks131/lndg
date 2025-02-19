"use server";

import { LoginFormState, LoginFormSchema } from '@/lib/definitions'
import { createSession, deleteSession } from "./sessions";
import { redirect } from "next/navigation";

const API_URL = process.env.API_URL;

export async function login(
  state: LoginFormState,
  formData: FormData,
): Promise<LoginFormState> {
  // 1. Validate form fields

  const validatedFields = LoginFormSchema.safeParse({
    username: formData.get("username"),
    password: formData.get("password"),
  });

  const errorMessage = { message: "Invalid login credentials." };

  if (!validatedFields.success) {
    return {
      errors: validatedFields.error.flatten().fieldErrors,
      ...errorMessage,
    };
  }

  // 2. Authenticate user

  const { username, password } = validatedFields.data;

  const res = await fetch(`${API_URL}/api/token/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  // console.log(res)
  if (!res.ok) {
    return errorMessage;
  }

  const { access, refresh } = await res.json();
  // console.log(accessToken, refreshToken)

  await createSession({ accessToken: access, refreshToken: refresh });
}

export async function logout() {
  deleteSession();
  redirect("/login");
}
