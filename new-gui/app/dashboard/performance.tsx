import ChannelCard from "@/components/channel-card";
import { fetchChannelsData } from "@/lib/data";
import { Channel } from "@/lib/definitions";
import { Suspense } from "react";


export default async function PerformanceSection() {
  try {
    const channels: Channel[] = await fetchChannelsData()
    console.log(channels.length)

    if (!channels || channels.length === 0) {
      return <div>No channels available</div>;
    }

    return (
      <Suspense fallback={<div>Loading...</div>}>

        <div className="grid grid-cols-2 gap-4">
          {channels.map((channel) => (
            <ChannelCard key={channel.chan_id} channel={channel} />
          ))}
        </div>
      </Suspense>
    );
  } catch (error) {
    console.error('Error fetching channels:', error);
    return <div>Error loading channels</div>;
  }
}