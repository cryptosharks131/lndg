
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import OverviewSection from "@/app/dashboard/overview";
import ProfitabilitySection from "@/app/dashboard/profitability"

import PerformanceSection from "./performance"


export default async function DashboardPage() {

  return (
    <Tabs defaultValue="profitability" className="">
      <TabsList className="grid w-full grid-cols-3 mb-4  place-self-center">
        <TabsTrigger value="overview">Overview</TabsTrigger>
        <TabsTrigger value="performance">Performance</TabsTrigger>
        <TabsTrigger value="profitability">Profitability</TabsTrigger>
      </TabsList>
      <TabsContent value="overview">
        <OverviewSection />
      </TabsContent>
      <TabsContent value="performance">
        <PerformanceSection />
      </TabsContent>
      <TabsContent value="profitability">
        <ProfitabilitySection />
      </TabsContent>
    </Tabs>
  );
}
