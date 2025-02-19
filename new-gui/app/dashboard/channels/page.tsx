import { SkeletonChannelCard } from "@/components/ui/skeletons";

import { Suspense } from "react";
import Channels from "./channels";
import ChannelsHeader from "./channels-headers";


export default async function ChannelsPage() {

  return (
    <Suspense fallback={<SkeletonChannelCard />}>
      <ChannelsHeader />
      <Channels />
    </Suspense>
  );

}


