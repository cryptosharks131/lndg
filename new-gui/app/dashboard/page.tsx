import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs"
import OverviewSection from "@/app/dashboard/overview";
import ProfitabilitySection from "@/app/dashboard/profitability"
import PerformanceSection from "@/app/dashboard/performance"


export default async function DashboardPage() {

  return (
    <Tabs defaultValue="overview">
      <TabsList className="grid w-full grid-cols-3 mb-4">
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
