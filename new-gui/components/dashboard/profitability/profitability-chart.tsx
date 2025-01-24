"use client"

import * as React from "react"
import { Area, AreaChart, Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"

import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from "@/components/ui/card"
import {
    ChartConfig,
    ChartContainer,
    ChartLegend,
    ChartLegendContent,
    ChartTooltip,
    ChartTooltipContent,
} from "@/components/ui/chart"
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"


const chartData = [
    {
        "date": "2025-01-23",
        "revenue": 200,
        "offchainCosts": 100,
        "onchain": 500000
    },
    {
        "date": "2025-01-22",
        "revenue": 205,
        "offchainCosts": 103,
        "onchain": 499000
    },
    {
        "date": "2025-01-21",
        "revenue": 210,
        "offchainCosts": 106,
        "onchain": 498000
    },
    {
        "date": "2025-01-20",
        "revenue": 215,
        "offchainCosts": 109,
        "onchain": 497000
    },
    {
        "date": "2025-01-19",
        "revenue": 220,
        "offchainCosts": 112,
        "onchain": 496000
    },
    {
        "date": "2025-01-18",
        "revenue": 225,
        "offchainCosts": 115,
        "onchain": 495000
    },
    {
        "date": "2025-01-17",
        "revenue": 230,
        "offchainCosts": 118,
        "onchain": 494000
    },
    {
        "date": "2025-01-16",
        "revenue": 235,
        "offchainCosts": 100,
        "onchain": 493000
    },
    {
        "date": "2025-01-15",
        "revenue": 240,
        "offchainCosts": 103,
        "onchain": 492000
    },
    {
        "date": "2025-01-14",
        "revenue": 245,
        "offchainCosts": 106,
        "onchain": 491000
    },
    {
        "date": "2025-01-13",
        "revenue": 200,
        "offchainCosts": 109,
        "onchain": 490000
    },
    {
        "date": "2025-01-12",
        "revenue": 205,
        "offchainCosts": 112,
        "onchain": 489000
    },
    {
        "date": "2025-01-11",
        "revenue": 210,
        "offchainCosts": 115,
        "onchain": 488000
    },
    {
        "date": "2025-01-10",
        "revenue": 215,
        "offchainCosts": 118,
        "onchain": 487000
    },
    {
        "date": "2025-01-09",
        "revenue": 220,
        "offchainCosts": 100,
        "onchain": 486000
    },
    {
        "date": "2025-01-08",
        "revenue": 225,
        "offchainCosts": 103,
        "onchain": 485000
    },
    {
        "date": "2025-01-07",
        "revenue": 230,
        "offchainCosts": 106,
        "onchain": 484000
    },
    {
        "date": "2025-01-06",
        "revenue": 235,
        "offchainCosts": 109,
        "onchain": 483000
    },
    {
        "date": "2025-01-05",
        "revenue": 240,
        "offchainCosts": 112,
        "onchain": 482000
    },
    {
        "date": "2025-01-04",
        "revenue": 245,
        "offchainCosts": 115,
        "onchain": 481000
    },
    {
        "date": "2025-01-03",
        "revenue": 200,
        "offchainCosts": 118,
        "onchain": 480000
    },
    {
        "date": "2025-01-02",
        "revenue": 205,
        "offchainCosts": 100,
        "onchain": 479000
    },
    {
        "date": "2025-01-01",
        "revenue": 210,
        "offchainCosts": 103,
        "onchain": 478000
    },
    {
        "date": "2024-12-31",
        "revenue": 215,
        "offchainCosts": 106,
        "onchain": 477000
    },
    {
        "date": "2024-12-30",
        "revenue": 220,
        "offchainCosts": 109,
        "onchain": 476000
    },
    {
        "date": "2024-12-29",
        "revenue": 225,
        "offchainCosts": 112,
        "onchain": 475000
    },
    {
        "date": "2024-12-28",
        "revenue": 230,
        "offchainCosts": 115,
        "onchain": 474000
    },
    {
        "date": "2024-12-27",
        "revenue": 235,
        "offchainCosts": 118,
        "onchain": 473000
    },
    {
        "date": "2024-12-26",
        "revenue": 240,
        "offchainCosts": 100,
        "onchain": 472000
    },
    {
        "date": "2024-12-25",
        "revenue": 245,
        "offchainCosts": 103,
        "onchain": 471000
    },
    {
        "date": "2024-12-24",
        "revenue": 200,
        "offchainCosts": 106,
        "onchain": 500000
    },
    {
        "date": "2024-12-23",
        "revenue": 205,
        "offchainCosts": 109,
        "onchain": 499000
    },
    {
        "date": "2024-12-22",
        "revenue": 210,
        "offchainCosts": 112,
        "onchain": 498000
    },
    {
        "date": "2024-12-21",
        "revenue": 215,
        "offchainCosts": 115,
        "onchain": 497000
    },
    {
        "date": "2024-12-20",
        "revenue": 220,
        "offchainCosts": 118,
        "onchain": 496000
    },
    {
        "date": "2024-12-19",
        "revenue": 225,
        "offchainCosts": 100,
        "onchain": 495000
    },
    {
        "date": "2024-12-18",
        "revenue": 230,
        "offchainCosts": 103,
        "onchain": 494000
    },
    {
        "date": "2024-12-17",
        "revenue": 235,
        "offchainCosts": 106,
        "onchain": 493000
    },
    {
        "date": "2024-12-16",
        "revenue": 240,
        "offchainCosts": 109,
        "onchain": 492000
    },
    {
        "date": "2024-12-15",
        "revenue": 245,
        "offchainCosts": 112,
        "onchain": 491000
    },
    {
        "date": "2024-12-14",
        "revenue": 200,
        "offchainCosts": 115,
        "onchain": 490000
    },
    {
        "date": "2024-12-13",
        "revenue": 205,
        "offchainCosts": 118,
        "onchain": 489000
    },
    {
        "date": "2024-12-12",
        "revenue": 210,
        "offchainCosts": 100,
        "onchain": 488000
    },
    {
        "date": "2024-12-11",
        "revenue": 215,
        "offchainCosts": 103,
        "onchain": 487000
    },
    {
        "date": "2024-12-10",
        "revenue": 220,
        "offchainCosts": 106,
        "onchain": 486000
    },
    {
        "date": "2024-12-09",
        "revenue": 225,
        "offchainCosts": 109,
        "onchain": 485000
    },
    {
        "date": "2024-12-08",
        "revenue": 230,
        "offchainCosts": 112,
        "onchain": 484000
    },
    {
        "date": "2024-12-07",
        "revenue": 235,
        "offchainCosts": 115,
        "onchain": 483000
    },
    {
        "date": "2024-12-06",
        "revenue": 240,
        "offchainCosts": 118,
        "onchain": 482000
    },
    {
        "date": "2024-12-05",
        "revenue": 245,
        "offchainCosts": 100,
        "onchain": 481000
    },
    {
        "date": "2024-12-04",
        "revenue": 200,
        "offchainCosts": 103,
        "onchain": 480000
    },
    {
        "date": "2024-12-03",
        "revenue": 205,
        "offchainCosts": 106,
        "onchain": 479000
    },
    {
        "date": "2024-12-02",
        "revenue": 210,
        "offchainCosts": 109,
        "onchain": 478000
    },
    {
        "date": "2024-12-01",
        "revenue": 215,
        "offchainCosts": 112,
        "onchain": 477000
    },
    {
        "date": "2024-11-30",
        "revenue": 220,
        "offchainCosts": 115,
        "onchain": 476000
    },
    {
        "date": "2024-11-29",
        "revenue": 225,
        "offchainCosts": 118,
        "onchain": 475000
    },
    {
        "date": "2024-11-28",
        "revenue": 230,
        "offchainCosts": 100,
        "onchain": 474000
    },
    {
        "date": "2024-11-27",
        "revenue": 235,
        "offchainCosts": 103,
        "onchain": 473000
    },
    {
        "date": "2024-11-26",
        "revenue": 240,
        "offchainCosts": 106,
        "onchain": 472000
    },
    {
        "date": "2024-11-25",
        "revenue": 245,
        "offchainCosts": 109,
        "onchain": 471000
    },
    {
        "date": "2024-11-24",
        "revenue": 200,
        "offchainCosts": 112,
        "onchain": 500000
    },
    {
        "date": "2024-11-23",
        "revenue": 205,
        "offchainCosts": 115,
        "onchain": 499000
    },
    {
        "date": "2024-11-22",
        "revenue": 210,
        "offchainCosts": 118,
        "onchain": 498000
    },
    {
        "date": "2024-11-21",
        "revenue": 215,
        "offchainCosts": 100,
        "onchain": 497000
    },
    {
        "date": "2024-11-20",
        "revenue": 220,
        "offchainCosts": 103,
        "onchain": 496000
    },
    {
        "date": "2024-11-19",
        "revenue": 225,
        "offchainCosts": 106,
        "onchain": 495000
    },
    {
        "date": "2024-11-18",
        "revenue": 230,
        "offchainCosts": 109,
        "onchain": 494000
    },
    {
        "date": "2024-11-17",
        "revenue": 235,
        "offchainCosts": 112,
        "onchain": 493000
    },
    {
        "date": "2024-11-16",
        "revenue": 240,
        "offchainCosts": 115,
        "onchain": 492000
    },
    {
        "date": "2024-11-15",
        "revenue": 245,
        "offchainCosts": 118,
        "onchain": 491000
    },
    {
        "date": "2024-11-14",
        "revenue": 200,
        "offchainCosts": 100,
        "onchain": 490000
    },
    {
        "date": "2024-11-13",
        "revenue": 205,
        "offchainCosts": 103,
        "onchain": 489000
    },
    {
        "date": "2024-11-12",
        "revenue": 210,
        "offchainCosts": 106,
        "onchain": 488000
    },
    {
        "date": "2024-11-11",
        "revenue": 215,
        "offchainCosts": 109,
        "onchain": 487000
    },
    {
        "date": "2024-11-10",
        "revenue": 220,
        "offchainCosts": 112,
        "onchain": 486000
    },
    {
        "date": "2024-11-09",
        "revenue": 225,
        "offchainCosts": 115,
        "onchain": 485000
    },
    {
        "date": "2024-11-08",
        "revenue": 230,
        "offchainCosts": 118,
        "onchain": 484000
    },
    {
        "date": "2024-11-07",
        "revenue": 235,
        "offchainCosts": 100,
        "onchain": 483000
    },
    {
        "date": "2024-11-06",
        "revenue": 240,
        "offchainCosts": 103,
        "onchain": 482000
    },
    {
        "date": "2024-11-05",
        "revenue": 245,
        "offchainCosts": 106,
        "onchain": 481000
    },
    {
        "date": "2024-11-04",
        "revenue": 200,
        "offchainCosts": 109,
        "onchain": 480000
    },
    {
        "date": "2024-11-03",
        "revenue": 205,
        "offchainCosts": 112,
        "onchain": 479000
    },
    {
        "date": "2024-11-02",
        "revenue": 210,
        "offchainCosts": 115,
        "onchain": 478000
    },
    {
        "date": "2024-11-01",
        "revenue": 215,
        "offchainCosts": 118,
        "onchain": 477000
    },
    {
        "date": "2024-10-31",
        "revenue": 220,
        "offchainCosts": 100,
        "onchain": 476000
    },
    {
        "date": "2024-10-30",
        "revenue": 225,
        "offchainCosts": 103,
        "onchain": 475000
    },
    {
        "date": "2024-10-29",
        "revenue": 230,
        "offchainCosts": 106,
        "onchain": 474000
    },
    {
        "date": "2024-10-28",
        "revenue": 235,
        "offchainCosts": 109,
        "onchain": 473000
    },
    {
        "date": "2024-10-27",
        "revenue": 240,
        "offchainCosts": 112,
        "onchain": 472000
    },
    {
        "date": "2024-10-26",
        "revenue": 245,
        "offchainCosts": 115,
        "onchain": 471000
    },
    {
        "date": "2024-10-25",
        "revenue": 200,
        "offchainCosts": 118,
        "onchain": 500000
    },
    {
        "date": "2024-10-24",
        "revenue": 205,
        "offchainCosts": 100,
        "onchain": 499000
    },
    {
        "date": "2024-10-23",
        "revenue": 210,
        "offchainCosts": 103,
        "onchain": 498000
    },
    {
        "date": "2024-10-22",
        "revenue": 215,
        "offchainCosts": 106,
        "onchain": 497000
    },
    {
        "date": "2024-10-21",
        "revenue": 220,
        "offchainCosts": 109,
        "onchain": 496000
    },
    {
        "date": "2024-10-20",
        "revenue": 225,
        "offchainCosts": 112,
        "onchain": 495000
    },
    {
        "date": "2024-10-19",
        "revenue": 230,
        "offchainCosts": 115,
        "onchain": 494000
    },
    {
        "date": "2024-10-18",
        "revenue": 235,
        "offchainCosts": 118,
        "onchain": 493000
    },
    {
        "date": "2024-10-17",
        "revenue": 240,
        "offchainCosts": 100,
        "onchain": 492000
    },
    {
        "date": "2024-10-16",
        "revenue": 245,
        "offchainCosts": 103,
        "onchain": 491000
    },
    {
        "date": "2024-10-15",
        "revenue": 200,
        "offchainCosts": 106,
        "onchain": 490000
    },
    {
        "date": "2024-10-14",
        "revenue": 205,
        "offchainCosts": 109,
        "onchain": 489000
    },
    {
        "date": "2024-10-13",
        "revenue": 210,
        "offchainCosts": 112,
        "onchain": 488000
    },
    {
        "date": "2024-10-12",
        "revenue": 215,
        "offchainCosts": 115,
        "onchain": 487000
    },
    {
        "date": "2024-10-11",
        "revenue": 220,
        "offchainCosts": 118,
        "onchain": 486000
    },
    {
        "date": "2024-10-10",
        "revenue": 225,
        "offchainCosts": 100,
        "onchain": 485000
    },
    {
        "date": "2024-10-09",
        "revenue": 230,
        "offchainCosts": 103,
        "onchain": 484000
    },
    {
        "date": "2024-10-08",
        "revenue": 235,
        "offchainCosts": 106,
        "onchain": 483000
    },
    {
        "date": "2024-10-07",
        "revenue": 240,
        "offchainCosts": 109,
        "onchain": 482000
    },
    {
        "date": "2024-10-06",
        "revenue": 245,
        "offchainCosts": 112,
        "onchain": 481000
    },
    {
        "date": "2024-10-05",
        "revenue": 200,
        "offchainCosts": 115,
        "onchain": 480000
    },
    {
        "date": "2024-10-04",
        "revenue": 205,
        "offchainCosts": 118,
        "onchain": 479000
    },
    {
        "date": "2024-10-03",
        "revenue": 210,
        "offchainCosts": 100,
        "onchain": 478000
    },
    {
        "date": "2024-10-02",
        "revenue": 215,
        "offchainCosts": 103,
        "onchain": 477000
    },
    {
        "date": "2024-10-01",
        "revenue": 220,
        "offchainCosts": 106,
        "onchain": 476000
    },
    {
        "date": "2024-09-30",
        "revenue": 225,
        "offchainCosts": 109,
        "onchain": 475000
    },
    {
        "date": "2024-09-29",
        "revenue": 230,
        "offchainCosts": 112,
        "onchain": 474000
    },
    {
        "date": "2024-09-28",
        "revenue": 235,
        "offchainCosts": 115,
        "onchain": 473000
    },
    {
        "date": "2024-09-27",
        "revenue": 240,
        "offchainCosts": 118,
        "onchain": 472000
    },
    {
        "date": "2024-09-26",
        "revenue": 245,
        "offchainCosts": 100,
        "onchain": 471000
    },
    {
        "date": "2024-09-25",
        "revenue": 200,
        "offchainCosts": 103,
        "onchain": 500000
    },
    {
        "date": "2024-09-24",
        "revenue": 205,
        "offchainCosts": 106,
        "onchain": 499000
    },
    {
        "date": "2024-09-23",
        "revenue": 210,
        "offchainCosts": 109,
        "onchain": 498000
    },
    {
        "date": "2024-09-22",
        "revenue": 215,
        "offchainCosts": 112,
        "onchain": 497000
    },
    {
        "date": "2024-09-21",
        "revenue": 220,
        "offchainCosts": 115,
        "onchain": 496000
    },
    {
        "date": "2024-09-20",
        "revenue": 225,
        "offchainCosts": 118,
        "onchain": 495000
    },
    {
        "date": "2024-09-19",
        "revenue": 230,
        "offchainCosts": 100,
        "onchain": 494000
    },
    {
        "date": "2024-09-18",
        "revenue": 235,
        "offchainCosts": 103,
        "onchain": 493000
    },
    {
        "date": "2024-09-17",
        "revenue": 240,
        "offchainCosts": 106,
        "onchain": 492000
    },
    {
        "date": "2024-09-16",
        "revenue": 245,
        "offchainCosts": 109,
        "onchain": 491000
    },
    {
        "date": "2024-09-15",
        "revenue": 200,
        "offchainCosts": 112,
        "onchain": 490000
    },
    {
        "date": "2024-09-14",
        "revenue": 205,
        "offchainCosts": 115,
        "onchain": 489000
    },
    {
        "date": "2024-09-13",
        "revenue": 210,
        "offchainCosts": 118,
        "onchain": 488000
    },
    {
        "date": "2024-09-12",
        "revenue": 215,
        "offchainCosts": 100,
        "onchain": 487000
    },
    {
        "date": "2024-09-11",
        "revenue": 220,
        "offchainCosts": 103,
        "onchain": 486000
    },
    {
        "date": "2024-09-10",
        "revenue": 225,
        "offchainCosts": 106,
        "onchain": 485000
    },
    {
        "date": "2024-09-09",
        "revenue": 230,
        "offchainCosts": 109,
        "onchain": 484000
    },
    {
        "date": "2024-09-08",
        "revenue": 235,
        "offchainCosts": 112,
        "onchain": 483000
    },
    {
        "date": "2024-09-07",
        "revenue": 240,
        "offchainCosts": 115,
        "onchain": 482000
    },
    {
        "date": "2024-09-06",
        "revenue": 245,
        "offchainCosts": 118,
        "onchain": 481000
    },
    {
        "date": "2024-09-05",
        "revenue": 200,
        "offchainCosts": 100,
        "onchain": 480000
    },
    {
        "date": "2024-09-04",
        "revenue": 205,
        "offchainCosts": 103,
        "onchain": 479000
    },
    {
        "date": "2024-09-03",
        "revenue": 210,
        "offchainCosts": 106,
        "onchain": 478000
    },
    {
        "date": "2024-09-02",
        "revenue": 215,
        "offchainCosts": 109,
        "onchain": 477000
    },
    {
        "date": "2024-09-01",
        "revenue": 220,
        "offchainCosts": 112,
        "onchain": 476000
    },
    {
        "date": "2024-08-31",
        "revenue": 225,
        "offchainCosts": 115,
        "onchain": 475000
    },
    {
        "date": "2024-08-30",
        "revenue": 230,
        "offchainCosts": 118,
        "onchain": 474000
    },
    {
        "date": "2024-08-29",
        "revenue": 235,
        "offchainCosts": 100,
        "onchain": 473000
    },
    {
        "date": "2024-08-28",
        "revenue": 240,
        "offchainCosts": 103,
        "onchain": 472000
    },
    {
        "date": "2024-08-27",
        "revenue": 245,
        "offchainCosts": 106,
        "onchain": 471000
    },
    {
        "date": "2024-08-26",
        "revenue": 200,
        "offchainCosts": 109,
        "onchain": 500000
    },
    {
        "date": "2024-08-25",
        "revenue": 205,
        "offchainCosts": 112,
        "onchain": 499000
    },
    {
        "date": "2024-08-24",
        "revenue": 210,
        "offchainCosts": 115,
        "onchain": 498000
    },
    {
        "date": "2024-08-23",
        "revenue": 215,
        "offchainCosts": 118,
        "onchain": 497000
    },
    {
        "date": "2024-08-22",
        "revenue": 220,
        "offchainCosts": 100,
        "onchain": 496000
    },
    {
        "date": "2024-08-21",
        "revenue": 225,
        "offchainCosts": 103,
        "onchain": 495000
    },
    {
        "date": "2024-08-20",
        "revenue": 230,
        "offchainCosts": 106,
        "onchain": 494000
    },
    {
        "date": "2024-08-19",
        "revenue": 235,
        "offchainCosts": 109,
        "onchain": 493000
    },
    {
        "date": "2024-08-18",
        "revenue": 240,
        "offchainCosts": 112,
        "onchain": 492000
    },
    {
        "date": "2024-08-17",
        "revenue": 245,
        "offchainCosts": 115,
        "onchain": 491000
    },
    {
        "date": "2024-08-16",
        "revenue": 200,
        "offchainCosts": 118,
        "onchain": 490000
    },
    {
        "date": "2024-08-15",
        "revenue": 205,
        "offchainCosts": 100,
        "onchain": 489000
    },
    {
        "date": "2024-08-14",
        "revenue": 210,
        "offchainCosts": 103,
        "onchain": 488000
    },
    {
        "date": "2024-08-13",
        "revenue": 215,
        "offchainCosts": 106,
        "onchain": 487000
    },
    {
        "date": "2024-08-12",
        "revenue": 220,
        "offchainCosts": 109,
        "onchain": 486000
    },
    {
        "date": "2024-08-11",
        "revenue": 225,
        "offchainCosts": 112,
        "onchain": 485000
    },
    {
        "date": "2024-08-10",
        "revenue": 230,
        "offchainCosts": 115,
        "onchain": 484000
    },
    {
        "date": "2024-08-09",
        "revenue": 235,
        "offchainCosts": 118,
        "onchain": 483000
    },
    {
        "date": "2024-08-08",
        "revenue": 240,
        "offchainCosts": 100,
        "onchain": 482000
    },
    {
        "date": "2024-08-07",
        "revenue": 245,
        "offchainCosts": 103,
        "onchain": 481000
    },
    {
        "date": "2024-08-06",
        "revenue": 200,
        "offchainCosts": 106,
        "onchain": 480000
    },
    {
        "date": "2024-08-05",
        "revenue": 205,
        "offchainCosts": 109,
        "onchain": 479000
    },
    {
        "date": "2024-08-04",
        "revenue": 210,
        "offchainCosts": 112,
        "onchain": 478000
    },
    {
        "date": "2024-08-03",
        "revenue": 215,
        "offchainCosts": 115,
        "onchain": 477000
    },
    {
        "date": "2024-08-02",
        "revenue": 220,
        "offchainCosts": 118,
        "onchain": 476000
    },
    {
        "date": "2024-08-01",
        "revenue": 225,
        "offchainCosts": 100,
        "onchain": 475000
    },
    {
        "date": "2024-07-31",
        "revenue": 230,
        "offchainCosts": 103,
        "onchain": 474000
    },
    {
        "date": "2024-07-30",
        "revenue": 235,
        "offchainCosts": 106,
        "onchain": 473000
    },
    {
        "date": "2024-07-29",
        "revenue": 240,
        "offchainCosts": 109,
        "onchain": 472000
    },
    {
        "date": "2024-07-28",
        "revenue": 245,
        "offchainCosts": 112,
        "onchain": 471000
    }
].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime(),)

const chartConfig = {
    visitors: {
        label: "Visitors",
    },
    revenue: {
        label: "Revenue (sats)",
        color: "hsl(var(--chart-2))",
    },
    offchainCosts: {
        label: "Off-Chain Costs (sats)",
        color: "hsl(var(--chart-5))",
    },
    onchain: {
        label: "On-Chain (stats)",
        color: "hsl(var(--chart-1))",
    },
} satisfies ChartConfig

export function ProfitabilityChart() {
    const [timeRange, setTimeRange] = React.useState("90d")

    const filteredData = chartData.filter((item) => {
        const date = new Date(item.date)
        const referenceDate = new Date()
        let daysToSubtract = 180
        if (timeRange === "90d") {
            daysToSubtract = 90
        } else if (timeRange === "60d") {
            daysToSubtract = 60
        } else if (timeRange === "30d") {
            daysToSubtract = 30
        } else if (timeRange === "7d") {
            daysToSubtract = 7
        }
        const startDate = new Date(referenceDate)
        startDate.setDate(startDate.getDate() - daysToSubtract)
        return date >= startDate
    })

    return (
        <Card>
            <CardHeader className="flex items-center gap-2 space-y-0 border-b py-5 sm:flex-row">
                <div className="grid flex-1 gap-1 text-center sm:text-left">
                    <CardTitle>Area Chart - Interactive</CardTitle>
                    <CardDescription>
                        Showing total visitors for the last 6 months
                    </CardDescription>
                </div>
                <Select value={timeRange} onValueChange={setTimeRange}>
                    <SelectTrigger
                        className="w-[160px] rounded-lg sm:ml-auto"
                        aria-label="Select a value"
                    >
                        <SelectValue placeholder="Last 6 months" />
                    </SelectTrigger>
                    <SelectContent className="rounded-xl">
                        <SelectItem value="180d" className="rounded-lg">
                            Last 6 months
                        </SelectItem>
                        <SelectItem value="90d" className="rounded-lg">
                            Last 90 days
                        </SelectItem>
                        <SelectItem value="60d" className="rounded-lg">
                            Last 60 days
                        </SelectItem>
                        <SelectItem value="30d" className="rounded-lg">
                            Last 30 days
                        </SelectItem>
                        <SelectItem value="7d" className="rounded-lg">
                            Last 7 days
                        </SelectItem>
                    </SelectContent>
                </Select>
            </CardHeader>
            <CardContent className="px-2 pt-4 sm:px-6 sm:pt-6">
                <ChartContainer
                    config={chartConfig}
                    className="aspect-auto h-96 w-full"
                >
                    <BarChart accessibilityLayer data={filteredData} >

                        <CartesianGrid vertical={false} />
                        <YAxis yAxisId="left" orientation="left" hide />
                        <YAxis yAxisId="right" orientation="right" hide />

                        <XAxis
                            dataKey="date"
                            tickLine={false}
                            axisLine={false}
                            tickMargin={8}
                            minTickGap={32}
                            tickFormatter={(value) => {
                                const date = new Date(value)
                                return date.toLocaleDateString("en-US", {
                                    month: "short",
                                    day: "numeric",
                                })
                            }}
                        />
                        <ChartTooltip
                            cursor={false}
                            content={
                                <ChartTooltipContent
                                    labelFormatter={(value) => {
                                        return new Date(value).toLocaleDateString("en-US", {
                                            year: "numeric",
                                            month: "long",
                                            day: "numeric",
                                        })
                                    }}
                                    indicator="dot"
                                />
                            }
                        />
                        <ChartLegend content={<ChartLegendContent />} />
                        <Bar
                            dataKey="onchain"
                            type="linear"
                            fill="var(--color-onchain)"
                            yAxisId="left"
                            radius={10}
                        />
                        <Bar
                            dataKey="offchainCosts"
                            type="linear"
                            fill="var(--color-offchainCosts)"
                            stroke="var(--color-offchainCosts)"
                            yAxisId="right"
                            radius={10}
                        />
                        <Bar
                            dataKey="revenue"
                            type="linear"
                            fill="var(--color-revenue)"
                            stroke="var(--color-revenue)"
                            yAxisId="right"
                            radius={10}

                        />

                        <ChartLegend content={<ChartLegendContent />} />
                    </BarChart>
                </ChartContainer>
            </CardContent>
        </Card>
    )
}
