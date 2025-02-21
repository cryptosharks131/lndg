import { fetchOpenChannels, fetchPendingChannels } from "@/lib/channel-actions";
import { Channel, Forward } from "@/lib/definitions";
import ChannelCard from "@/components/channel-card";
import { channelColumns } from "@/components/dashboard/channels/columns";
import { ChannelsTable } from "@/components/dashboard/channels/data-table";
import { Liquidity } from "@/components/dashboard/channels/components";
import { fetchChannelForwardsIn, fetchRoutedChartData } from "@/lib/data";

export default async function Channels() {
    try {
        const channels: Channel[] = await fetchOpenChannels()
        // const channelsPending = await fetchPendingChannels()


        if (!channels || channels.length === 0) {
            return <div>No channels available</div>;
        }

        return (
            <>

                <ChannelsTable columns={channelColumns} data={channels} />
                <div className="grid grid-cols-1 gap-4">
                    {channels.map((channel) => (
                        <ChannelCard key={channel.chan_id} channel={channel} />
                    ))}
                </div>
            </>

        )

    } catch (error) {
        console.error('Error fetching channels:', error);
        return <div>Error loading channels</div>;
    }
}