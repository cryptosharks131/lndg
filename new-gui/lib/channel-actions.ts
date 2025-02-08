"use server";

import { verifySession } from "@/app/auth/sessions";
import { ToastActionElement } from "@/components/ui/toast";
import { Channel } from "./definitions";

type ToastData = { title: string; description?: string; variant?: "destructive" | "default"; action?: ToastActionElement; }

const API_URL = process.env.API_URL;

export const copyPublicKey = async (channelAlias: string, key: string): Promise<{ success: boolean; toast?: ToastData }> => {
    try {
        await navigator.clipboard.writeText(key);
        const toast: ToastData = {
            variant: "default",
            title: "Key Copied!",
            description: `Public Key ${key} for ${channelAlias} copied to clipboard`,
        };
        return { success: true, toast: toast }
    } catch (err) {
        const toast: ToastData = {
            variant: "destructive",
            title: "Uh oh! Something went wrong.",
            description: `Failed to copy public key for ${channelAlias}: ${String(err)}`,
        };
        return { success: false, toast: toast }

    }
};

// toggle rebalancer


export const closeChannel = async (channel: Channel, targetFee: number = 1, forceClose: boolean = false): Promise<{ success: boolean; toast?: ToastData }> => {
    try {
        // Add API call or state update logic here

        const { isAuth, accessToken } = await verifySession();

        if (!isAuth) {
            throw new Error("Unauthorized: No access token");
        }

        const chan_id = channel.short_chan_id
        const force = forceClose ? "on" : "off"
        const target_fee = targetFee

        const body = forceClose
            ? { chan_id, force }
            : { chan_id, target_fee };


        // fetch data 
        const response = await fetch(`${API_URL}/api/closechannel/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${accessToken}`,
            },
            body: JSON.stringify(body),
        });

        console.log(response)

        if (!response.ok) {
            const toast: ToastData = {
                variant: "destructive",
                title: "Uh oh! Something went wrong.",
                description: `Failed to close channel ${channel.alias}: ${response.statusText || "Unknown error"}`,
            };
            return { success: false, toast: toast }; // Exit function if request failed
        }

        // Success Toast Notification
        const toast: ToastData = {
            variant: "default",
            title: "Channel Closed!",
            description: `Channel ${channel.alias} with ${channel.short_chan_id} is scheduled for deletion`,
        };
        return { success: true, toast: toast };
    } catch (err) {
        console.error("Close channel error:", err);
        const toast: ToastData = {
            variant: "destructive",
            title: "Uh oh! Something went wrong.",
            description: `Failed to close channel ${channel.alias}: ${err instanceof Error ? err.message : String(err)}`,
        };
        return { success: false, toast: toast };
    }
};

// force close channel

// update outbound fees

// update liquidity targets
