import { SkeletonChannelCard } from "@/components/ui/skeletons";

import { Suspense } from "react";
import Channels from "./channels";


export default async function ChannelsPage() {

  return (
    <Suspense fallback={<SkeletonChannelCard />}>
      <Channels />
    </Suspense>
  );

}


