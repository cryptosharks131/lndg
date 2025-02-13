import "server-only";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import type { SessionPayload } from "@/app/auth/definitions";
import { jwtDecode } from "@/lib/utils";
import { SessionTokens } from "@/lib/definitions";

const API_URL = process.env.API_URL;

export async function getSession(): Promise<SessionTokens> {
  const cookieStore = await cookies();
  // console.log("accessToken:", cookieStore.get("accessToken")?.value)
  // console.log("refreshToken:", cookieStore.get("refreshToken")?.value)

  return {
    accessToken: cookieStore.get("accessToken")?.value,
    refreshToken: cookieStore.get("refreshToken")?.value
  };
}


// New function just for setting tokens without redirect
export async function updateSessionTokens(sessionPayload: SessionPayload) {
  const cookieStore = await cookies();

  if (!sessionPayload?.accessToken || !sessionPayload?.refreshToken) {
    throw new Error("Invalid session payload");
  }

  const accessDecoded = jwtDecode(sessionPayload.accessToken);
  const refreshDecoded = jwtDecode(sessionPayload.refreshToken);

  cookieStore.set("accessToken", sessionPayload.accessToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    expires: new Date(accessDecoded.exp * 1000),
    sameSite: "lax",
    path: "/",
  });

  cookieStore.set("refreshToken", sessionPayload.refreshToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    expires: new Date(refreshDecoded.exp * 1000),
    sameSite: "lax",
    path: "/",
  });
}


export async function createSession(sessionPayload: SessionPayload) {
  await updateSessionTokens(sessionPayload);
  redirect("/dashboard");  // Only redirect on initial login
}


export async function refreshSessionTokens(refreshToken: string) {
  try {
    const res = await fetch(`${API_URL}/api/token/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    if (!res.ok) return null;

    const { access } = await res.json();

    // Use updateSessionTokens instead of directly setting cookies
    await updateSessionTokens({
      accessToken: access,
      refreshToken: refreshToken  // Keep existing refresh token
    });

    return { access };
  } catch (error) {
    console.error("Token refresh failed:", error);
    return null;
  }
}

export async function verifySession() {
  const accessToken = (await cookies()).get("accessToken")?.value;
  const refreshToken = (await cookies()).get("refreshToken")?.value;

  if (!accessToken) {
    redirect("/login");
  }

  const accessDecoded = jwtDecode(accessToken);
  const isAccessTokenExpired = accessDecoded.exp < Date.now() / 1000;

  if (isAccessTokenExpired && refreshToken) {
    refreshSessionTokens(refreshToken)
  }
  else if (isAccessTokenExpired && !refreshToken) {
    redirect("/login");
  }

  return { isAuth: true, accessToken: accessToken };
}

export async function deleteSession() {
  const cookieStore = await cookies();
  cookieStore.delete("accessToken");
  cookieStore.delete("refreshToken");
}


export async function isTokenExpiringSoon(token: string, bufferSeconds: number = 60): Promise<boolean> {
  try {
    const { exp } = jwtDecode(token);
    const now = Date.now() / 1000;
    // console.log(exp, now, exp - now < bufferSeconds)
    return exp - now < bufferSeconds;
  } catch {
    return true;
  }
}