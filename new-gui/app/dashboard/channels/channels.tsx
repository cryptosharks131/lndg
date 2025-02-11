import { fetchChannelsData } from "@/lib/data";
import { Channel } from "@/lib/definitions";
import ChannelCard from "@/components/channel-card";

export default async function Channels() {
    try {
        const channels: Channel[] = await fetchChannelsData()

        if (!channels || channels.length === 0) {
            return <div>No channels available</div>;
        }

        return (

            <div className="grid grid-cols-1 gap-4">
                {channels.map((channel) => (
                    <ChannelCard key={channel.chan_id} channel={channel} />
                ))}
            </div>
        )

    } catch (error) {
        console.error('Error fetching channels:', error);
        return <div>Error loading channels</div>;
    }
}