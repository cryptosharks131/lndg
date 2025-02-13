// app/components/TokenRefreshProvider.tsx
'use client';

import React, { createContext, useContext, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { handleTokenRefresh } from '@/app/auth/action';

type TokenRefreshContextType = {
    refreshToken: () => Promise<void>;
};

const TokenRefreshContext = createContext<TokenRefreshContextType | null>(null);

export function useTokenRefresh() {
    const context = useContext(TokenRefreshContext);
    if (!context) {
        throw new Error('useTokenRefresh must be used within a TokenRefreshProvider');
    }
    return context;
}

type Props = {
    children: React.ReactNode;
    refreshIntervalSeconds?: number;
    apiUrl?: string;
};

export function TokenRefreshProvider({
    children,
    refreshIntervalSeconds = 240, // 4 minutes default
}: Props) {
    const router = useRouter();
    // Initialize the ref with null since there's no timeout when the component first mounts
    const refreshTimeoutRef = useRef<NodeJS.Timeout | null>(null);

    const checkAndRefreshToken = async () => {
        try {
            const result = await handleTokenRefresh();

            if (!result.success) {
                if (result.reason === 'no-tokens') {
                    router.push('/login');
                    return;
                }
                // Handle other failure cases if needed
            }

            // Schedule next check
            scheduleNextRefresh();
        } catch (error) {
            console.error('Token refresh check failed:', error);
            scheduleNextRefresh(); // Still schedule next check on error
        }
    };

    const scheduleNextRefresh = () => {
        if (refreshTimeoutRef.current) {
            clearTimeout(refreshTimeoutRef.current);
        }

        refreshTimeoutRef.current = setTimeout(
            checkAndRefreshToken,
            refreshIntervalSeconds * 1000
        );
    };

    // Set up initial token check and refresh cycle
    useEffect(() => {
        checkAndRefreshToken();

        // Cleanup function to clear timeout when component unmounts
        return () => {
            if (refreshTimeoutRef.current) {
                clearTimeout(refreshTimeoutRef.current);
            }
        };
    }, []);

    // Handle tab visibility changes
    useEffect(() => {
        const handleVisibilityChange = () => {
            if (document.visibilityState === 'visible') {
                checkAndRefreshToken();
            }
        };

        document.addEventListener('visibilitychange', handleVisibilityChange);

        // Cleanup function to remove event listener
        return () => {
            document.removeEventListener('visibilitychange', handleVisibilityChange);
        };
    }, []);

    return (
        <TokenRefreshContext.Provider value={{ refreshToken: checkAndRefreshToken }}>
            {children}
        </TokenRefreshContext.Provider>
    );
}