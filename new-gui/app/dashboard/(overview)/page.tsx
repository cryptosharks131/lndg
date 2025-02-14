
import { Suspense } from "react";
import OverviewSection from "@/app/dashboard/(overview)/overview";


export default async function DashboardPage() {

  return (


    <Suspense fallback={<>Loading ...</>}>
      <OverviewSection />
    </Suspense>

  );
}
