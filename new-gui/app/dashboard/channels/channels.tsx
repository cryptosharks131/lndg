import { fetchOpenChannels, fetchPendingChannels } from "@/lib/channel-actions";
import { Channel } from "@/lib/definitions";
import ChannelCard from "@/components/channel-card";

export default async function Channels() {
    try {
        const channels: Channel[] = await fetchOpenChannels()
        const channelsPending = await fetchPendingChannels()


        console.log(channelsPending)

        if (!channels || channels.length === 0) {
            return <div>No channels available</div>;
        }

        return (
            <>
                <div className="grid grid-cols-1 gap-4">
                    {channels.map((channel) => (
                        <ChannelCard key={channel.chan_id} channel={channel} />
                    ))}
                </div>
                <h4>Pending Open</h4>
                <div className="grid grid-cols-1 gap-4">
                    {channelsPending.channelsPendingOpen?.map((channel) => (
                        <ChannelCard key={channel.remote_node_pub} channel={channel} />

                    ))}
                </div>
                <h4>Pending Close</h4>
                <div className="grid grid-cols-1 gap-4">
                    {channelsPending.channelsPendingClose?.map((channel) => (
                        // <p>{channel.remote_node_pub}</p>
                        <ChannelCard key={channel.remote_node_pub} channel={channel} />

                    ))}
                </div>
                <h4>Waiting to Close</h4>
                <div className="grid grid-cols-1 gap-4">
                    {channelsPending.channelsWaitingToClose?.map((channel) => (
                        <p key={channel.remote_node_pub} >{channel.remote_node_pub}</p>
                    ))}
                </div>
                <h4>Pending Close</h4>
                <div className="grid grid-cols-1 gap-4">
                    {channelsPending.channelsPendingForceClose?.map((channel) => (
                        // <p>{channel.remote_node_pub}</p>
                        <ChannelCard key={channel.remote_node_pub} channel={channel} />

                    ))}
                </div>
            </>

        )

    } catch (error) {
        console.error('Error fetching channels:', error);
        return <div>Error loading channels</div>;
    }
}