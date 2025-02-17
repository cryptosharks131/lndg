'use client'

import {
    Sheet,
    SheetClose,
    SheetContent,
    SheetDescription,
    SheetFooter,
    SheetHeader,
    SheetTitle,
    SheetTrigger,
} from "@/components/ui/sheet"
import { Button } from "../ui/button"
import { Label } from "../ui/label"
import { DateRangePicker } from "../date-range-picker"
import { DateRange } from "react-day-picker"
import { subDays } from "date-fns"
import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useEffect, useState } from "react"
import ChannelSelector from "./channel-selector"


export default function AnalyticsFilterPane() {

    const searchParams = useSearchParams();
    const pathname = usePathname();
    const { replace } = useRouter();

    const [dateRange, setDateRange] = useState<DateRange>({
        from: subDays(new Date(), 7),
        to: new Date(),
    })

    useEffect(() => {
        const from = searchParams.get('from');
        const to = searchParams.get('to');
        if (from && to) {
            setDateRange({
                from: new Date(from),
                to: new Date(to),
            })
        }
    }, [searchParams])

    function handleDateChange(dateRange: DateRange | undefined) {
        if (!dateRange) {
            return null
        }
        setDateRange(dateRange)
        // console.log(dateRange)
        const params = new URLSearchParams(searchParams);

        if (dateRange?.from || dateRange?.to) {
            if (dateRange.from) {
                params.set('from', dateRange.from.toLocaleDateString());
            }
            if (dateRange.to) {
                params.set('to', dateRange.to.toLocaleDateString());
            }
        } else {
            params.delete('from');
            params.delete('to');
        }
        replace(`${pathname}?${params.toString()}`);
    }

    return (
        <Sheet>
            <SheetTrigger asChild>
                <Button variant="outline">Open</Button>
            </SheetTrigger>
            <SheetContent>
                <SheetHeader>
                    <SheetTitle>Filter Pane</SheetTitle>
                    <SheetDescription>
                        Filter data based on key attributes.
                    </SheetDescription>
                </SheetHeader>
                <div className="grid gap-4 py-4">
                    <div className="grid grid-cols-4 items-center gap-4">
                        <div>
                            <Label htmlFor="date" className="text-right">
                                Date Range
                            </Label>
                        </div>
                        <div className="col-span-3">
                            <DateRangePicker dateRange={dateRange} onDateChange={handleDateChange} />
                        </div>

                    </div>
                    <div className="grid grid-cols-4 items-center gap-4">
                        <div>
                            <Label htmlFor="date" className="text-right">
                                Select Channels
                            </Label>
                        </div>
                        <div className="col-span-3">
                            <ChannelSelector />
                        </div>

                    </div>
                </div>
                <SheetFooter>
                    {/* <SheetClose asChild>
                        <Button type="submit">Save changes</Button>
                    </SheetClose> */}
                </SheetFooter>
            </SheetContent>
        </Sheet>
    )

}
