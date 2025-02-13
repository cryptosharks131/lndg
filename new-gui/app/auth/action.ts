'use server'

import { refreshSessionTokens, isTokenExpiringSoon } from '../auth/sessions'
import { cookies } from "next/headers";

export async function handleTokenRefresh() {
    const cookieStore = await cookies();
    const accessToken = cookieStore.get("accessToken")?.value;
    const refreshToken = cookieStore.get("refreshToken")?.value;

    if (!accessToken || !refreshToken) {
        return { success: false, reason: 'no-tokens' };
    }

    const needsRefresh = await isTokenExpiringSoon(accessToken, 300); // 5 minute buffer

    if (needsRefresh) {
        const result = await refreshSessionTokens(refreshToken);
        return { success: !!result, reason: result ? 'refreshed' : 'refresh-failed' };
    }

    return { success: true, reason: 'no-refresh-needed' };
}