"use server";

import { verifySession } from "@/app/auth/sessions";
import { ToastActionElement } from "@/components/ui/toast";
import { Channel, OpenChannelFormState, OpenChannelFormSchema, OpenChannelFormData } from "./definitions";

export type ToastData = { title: string; description?: string; variant?: "destructive" | "default"; action?: ToastActionElement; }

const API_URL = process.env.API_URL;

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


        // close channel 
        const response = await fetch(`${API_URL}/api/closechannel/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${accessToken}`,
            },
            body: JSON.stringify(body),
        });

        // console.log(response)

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


// open channel

export async function openChannel(
    state: OpenChannelFormState,
    formData: FormData,
): Promise<OpenChannelFormState> {

    // 1. validate the data

    try {
        const rawData: OpenChannelFormData = {
            publicKey: formData.get("publicKey") as string,
            capacity: Number(formData.get("capacity")) || 0,
            fee: Number(formData.get("fee")) || 0,
        };


        const validatedData = OpenChannelFormSchema.safeParse(rawData)
        // console.log("formData:", formData)
        // console.log("validatedData:", validatedData)
        const errorMessage = { message: "Invalid Open Channel Form Data." }

        if (!validatedData.success) {
            return {
                success: false,
                errors: validatedData.error.flatten().fieldErrors,
                inputs: rawData,
                ...errorMessage,
            }
        }
        //2. check if user is authenticated
        const { isAuth, accessToken } = await verifySession();

        if (!isAuth) {
            throw new Error("Unauthorized: No access token");
        }


        const { publicKey, capacity, fee } = validatedData.data;

        const body = { peer_pubkey: publicKey, local_amt: capacity, sat_per_byte: fee };

        // open channel 
        // console.log(JSON.stringify(body))

        const response = await fetch(`${API_URL}/api/openchannel/`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${accessToken}`,
            },
            body: JSON.stringify(body),
        });

        // console.log(response)

        if (!response.ok) {
            return errorMessage;
        }

        // Parse response body and check for error
        const responseBody = await response.json();

        // Check if there's an "error" field in the response
        if (responseBody.error) {
            return { success: false, message: responseBody.error, inputs: rawData };
        }

        // 6. If no error, return success
        return { success: true, message: "Channel opened successfully!" };
    } catch (err) {
        console.error("Open channel error:", err);
        return { success: false, message: "Unexpected error occurred. Please try again." };
    }

}

// force close channel

// update outbound fees

// update liquidity targets
