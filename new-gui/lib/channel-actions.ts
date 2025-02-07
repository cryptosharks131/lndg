
type ToastFunction = (options: { title: string; description?: string; variant?: "destructive" | "default"; action?: React.ReactNode }) => void;

export const copyPublicKey = async (channelAlias: string, key: string, toast: ToastFunction): Promise<void> => {
    try {
        await navigator.clipboard.writeText(key);
        toast({
            variant: "default",
            title: "Key Copied!",
            description: `Public Key for ${channelAlias} copied to clipboard`,
        });
    } catch (err) {
        toast({
            variant: "destructive",
            title: "Uh oh! Something went wrong.",
            description: `Failed to copy public key for ${channelAlias}: ${String(err)}`,
        });
    }
};

// toggle rebalancer

// close channel

// force close channel

// update outbound fees

// update liquidity targets
