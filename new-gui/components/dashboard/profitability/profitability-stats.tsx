import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { PerformanceStats } from "@/lib/definitions";

const statsData: PerformanceStats[] = [
    {
        lineItem: "Payments Routed",
        description: "Number of payments routed through the network",
        "1 Day": 2,
        "7 Day": 24,
        "30 Day": 24,
        "90 Day": 24,
        Lifetime: 24,
    },
    {
        lineItem: "Value Routed",
        description: "Total value in sats routed through the network",
        "1 Day": 2000000,
        "7 Day": 23000008,
        "30 Day": 23000008,
        "90 Day": 23000008,
        Lifetime: 23000008,
    },
    {
        lineItem: "Revenue Earned",
        description: "Total revenue in sats, and ppm earned from the network",
        "1 Day": { stats: 202, ppm: 101 },
        "7 Day": { stats: 2126, ppm: 92 },
        "30 Day": { stats: 2126, ppm: 92 },
        "90 Day": { stats: 2126, ppm: 92 },
        Lifetime: { stats: 2126, ppm: 92 },
    },
    {
        lineItem: "Onchain Costs",
        description: "Total costs in sats spent on on-chain transactions",
        "1 Day": 0,
        "7 Day": 546,
        "30 Day": 546,
        "90 Day": 546,
        Lifetime: 546,
    },
    {
        lineItem: "Offchain Costs",
        description: "Total costs in sats, and ppm spent off-chain",
        "1 Day": { stats: 2, ppm: 1 },
        "7 Day": { stats: 2, ppm: 1 },
        "30 Day": { stats: 2, ppm: 1 },
        "90 Day": { stats: 2, ppm: 1 },
        Lifetime: { stats: 2, ppm: 1 },
    },
    {
        lineItem: "Percent Cost",
        description: "Percent of revenue spent on off-chain costs",
        "1 Day": 0,
        "7 Day": 0.25,
        "30 Day": 0.25,
        "90 Day": 0.25,
        Lifetime: 0.25,
    },
    {
        lineItem: "Profits",
        description: "Total profits in sats, and ppm",
        "1 Day": { stats: 202, ppm: 101 },
        "7 Day": { stats: 1578, ppm: 68 },
        "30 Day": { stats: 1578, ppm: 68 },
        "90 Day": { stats: 1578, ppm: 68 },
        Lifetime: { stats: 1578, ppm: 68 },
    },
];


// export function ProfitabilityStats() {

//     const renderValue = (value: number | { stats: number; ppm: number }) => {
//         if (typeof value === "number") {
//             // Handle percentages
//             if (value > 0 && value <= 1) {
//                 return `${(value * 100).toFixed(2)}%`;
//             }
//             return value.toLocaleString(); // Format large numbers with commas
//         }

//         // Handle stats and ppm objects
//         return (
//             <span>
//                 {value.stats.toLocaleString()} sats <p className="border text-xs">{value.ppm} <sub>ppm</sub></p>
//             </span>
//         );
//     };

//     return (

//         <>
//             {statsData.map((item) => (



//                 <Card className="mb-4">
//                     <CardHeader className="flex items-center gap-2 space-y-0 border-b py-5 sm:flex-row">
//                         <div className="grid flex-1 gap-1 text-center sm:text-left">

//                             <CardTitle>{item.lineItem}</CardTitle>
//                             <CardDescription>
//                                 {item.description}
//                             </CardDescription>
//                         </div>
//                     </CardHeader>
//                     <CardContent key={item.lineItem} >
//                         <div className="flex h-5 items-center justify-evenly space-x-4 text-sm mt-4">
//                             <div className="text-center">
//                                 <p className="flex text-xl font-semibold tracking-tight flex-auto">
//                                     {renderValue(item["1 Day"])}
//                                 </p>
//                                 <h4 className="text-xs">
//                                     1 Day
//                                 </h4>
//                             </div>
//                             <Separator orientation="vertical" />
//                             <div className="text-center">
//                                 <p className="text-xl font-semibold tracking-tight">
//                                     {renderValue(item["1 Day"])}
//                                 </p>
//                                 <h4 className="text-xs">
//                                     1 Day
//                                 </h4>
//                             </div>
//                             <Separator orientation="vertical" />
//                             <div className="text-center">
//                                 <p className="text-xl font-semibold tracking-tight">
//                                     {renderValue(item["1 Day"])}
//                                 </p>
//                                 <h4 className="text-xs">
//                                     1 Day
//                                 </h4>
//                             </div>
//                             <Separator orientation="vertical" />
//                             <div className="text-center">
//                                 <p className="text-xl font-semibold tracking-tight">
//                                     {renderValue(item["1 Day"])}
//                                 </p>
//                                 <h4 className="text-xs">
//                                     1 Day
//                                 </h4>
//                             </div>
//                             <Separator orientation="vertical" />
//                             <div className="text-center">
//                                 <p className="text-xl font-semibold tracking-tight">
//                                     {renderValue(item["Lifetime"])}
//                                 </p>
//                                 <h4 className="text-xs">
//                                     Lifetime
//                                 </h4>
//                             </div>
//                         </div>
//                     </CardContent>
//                 </Card>
//             ))}

//         </>

//     )
// }


export const ProfitabilityStats: React.FC = () => {
    const renderValue = (value: number | { stats: number; ppm: number }) => {
        if (typeof value === "number") {
            // Handle percentages
            if (value > 0 && value <= 1) {
                return `${(value * 100).toFixed(2)}%`;
            }
            return value.toLocaleString(); // Format large numbers with commas
        }

        // Handle stats and ppm objects
        return (
            <span>
                {value.stats.toLocaleString()} sats ({value.ppm} ppm)
            </span>
        );
    };

    return (
        <table>
            <thead>
                <tr>
                    <th>Line Item</th>
                    <th>Description</th>
                    <th>1 Day</th>
                    <th>7 Day</th>
                    <th>30 Day</th>
                    <th>90 Day</th>
                    <th>Lifetime</th>
                </tr>
            </thead>
            <tbody>
                {statsData.map((item) => (
                    <tr key={item.lineItem}>
                        <td>{item.lineItem}</td>
                        <td>{item.description}</td>
                        <td>{renderValue(item["1 Day"])}</td>
                        <td>{renderValue(item["7 Day"])}</td>
                        <td>{renderValue(item["30 Day"])}</td>
                        <td>{renderValue(item["90 Day"])}</td>
                        <td>{renderValue(item.Lifetime)}</td>
                    </tr>
                ))}
            </tbody>
        </table>
    );
};
