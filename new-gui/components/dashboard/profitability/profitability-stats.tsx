"use client"

import { useState } from "react";

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ChartConfig, ChartContainer, ChartLegend, ChartLegendContent, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart";
import { CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts";
import { formatNumber } from "@/lib/formatter";
import { ProfitabilityStats } from "@/lib/definitions";

const statsData: ProfitabilityStats[] = [
    {
        "date": "2024-07-29",
        "paymentsRouted": 8,
        "valueRouted": 70692,
        "revenue": 2826.61,
        "onchainCosts": 431.0,
        "offchainCost": 288.53,
        "offchainCostPpm": 4081.49,
        "percentCosts": 0.2546,
        "profit": 2107.09,
        "profitPpm": 29806.57
    },
    {
        "date": "2024-07-30",
        "paymentsRouted": 1,
        "valueRouted": 149290,
        "revenue": 3250.61,
        "onchainCosts": 446.5,
        "offchainCost": 253.04,
        "offchainCostPpm": 1694.97,
        "percentCosts": 0.2152,
        "profit": 2551.07,
        "profitPpm": 17088.03
    },
    {
        "date": "2024-07-31",
        "paymentsRouted": 8,
        "valueRouted": 37785,
        "revenue": 868.12,
        "onchainCosts": 211.85,
        "offchainCost": 133.53,
        "offchainCostPpm": 3534.05,
        "percentCosts": 0.3979,
        "profit": 522.74,
        "profitPpm": 13834.49
    },
    {
        "date": "2024-08-01",
        "paymentsRouted": 8,
        "valueRouted": 195364,
        "revenue": 2628.95,
        "onchainCosts": 430.06,
        "offchainCost": 166.36,
        "offchainCostPpm": 851.53,
        "percentCosts": 0.2269,
        "profit": 2032.53,
        "profitPpm": 10403.78
    },
    {
        "date": "2024-08-02",
        "paymentsRouted": 18,
        "valueRouted": 49618,
        "revenue": 1050.94,
        "onchainCosts": 123.01,
        "offchainCost": 39.66,
        "offchainCostPpm": 799.21,
        "percentCosts": 0.1548,
        "profit": 888.28,
        "profitPpm": 17902.4
    },
    {
        "date": "2024-08-03",
        "paymentsRouted": 8,
        "valueRouted": 20667,
        "revenue": 515.7,
        "onchainCosts": 345.07,
        "offchainCost": 287.99,
        "offchainCostPpm": 13934.89,
        "percentCosts": 1.2276,
        "profit": -117.37,
        "profitPpm": -5679.16
    },
    {
        "date": "2024-08-04",
        "paymentsRouted": 18,
        "valueRouted": 173472,
        "revenue": 5379.64,
        "onchainCosts": 82.83,
        "offchainCost": 273.89,
        "offchainCostPpm": 1578.88,
        "percentCosts": 0.0663,
        "profit": 5022.91,
        "profitPpm": 28955.18
    },
    {
        "date": "2024-08-05",
        "paymentsRouted": 16,
        "valueRouted": 92982,
        "revenue": 4488.99,
        "onchainCosts": 305.22,
        "offchainCost": 74.27,
        "offchainCostPpm": 798.73,
        "percentCosts": 0.0845,
        "profit": 4109.51,
        "profitPpm": 44196.81
    },
    {
        "date": "2024-08-06",
        "paymentsRouted": 8,
        "valueRouted": 68542,
        "revenue": 2231.29,
        "onchainCosts": 436.7,
        "offchainCost": 21.62,
        "offchainCostPpm": 315.43,
        "percentCosts": 0.2054,
        "profit": 1772.97,
        "profitPpm": 25866.91
    },
    {
        "date": "2024-08-07",
        "paymentsRouted": 8,
        "valueRouted": 89345,
        "revenue": 4027.52,
        "onchainCosts": 283.76,
        "offchainCost": 208.62,
        "offchainCostPpm": 2334.94,
        "percentCosts": 0.1223,
        "profit": 3535.14,
        "profitPpm": 39567.33
    },
    {
        "date": "2024-08-08",
        "paymentsRouted": 2,
        "valueRouted": 34148,
        "revenue": 457.28,
        "onchainCosts": 118.66,
        "offchainCost": 45.29,
        "offchainCostPpm": 1326.19,
        "percentCosts": 0.3585,
        "profit": 293.33,
        "profitPpm": 8590.1
    },
    {
        "date": "2024-08-09",
        "paymentsRouted": 7,
        "valueRouted": 147112,
        "revenue": 3655.96,
        "onchainCosts": 164.18,
        "offchainCost": 13.85,
        "offchainCostPpm": 94.13,
        "percentCosts": 0.0487,
        "profit": 3477.94,
        "profitPpm": 23641.42
    },
    {
        "date": "2024-08-10",
        "paymentsRouted": 8,
        "valueRouted": 165783,
        "revenue": 2950.85,
        "onchainCosts": 272.33,
        "offchainCost": 169.92,
        "offchainCostPpm": 1024.98,
        "percentCosts": 0.1499,
        "profit": 2508.59,
        "profitPpm": 15131.79
    },
    {
        "date": "2024-08-11",
        "paymentsRouted": 5,
        "valueRouted": 40218,
        "revenue": 752.84,
        "onchainCosts": 317.92,
        "offchainCost": 88.47,
        "offchainCostPpm": 2199.66,
        "percentCosts": 0.5398,
        "profit": 346.45,
        "profitPpm": 8614.41
    },
    {
        "date": "2024-08-12",
        "paymentsRouted": 4,
        "valueRouted": 50356,
        "revenue": 517.46,
        "onchainCosts": 463.84,
        "offchainCost": 28.77,
        "offchainCostPpm": 571.33,
        "percentCosts": 0.952,
        "profit": 24.85,
        "profitPpm": 493.45
    },
    {
        "date": "2024-08-13",
        "paymentsRouted": 5,
        "valueRouted": 112850,
        "revenue": 5121.53,
        "onchainCosts": 64.1,
        "offchainCost": 53.06,
        "offchainCostPpm": 470.2,
        "percentCosts": 0.0229,
        "profit": 5004.37,
        "profitPpm": 44345.31
    },
    {
        "date": "2024-08-14",
        "paymentsRouted": 7,
        "valueRouted": 33371,
        "revenue": 1332.7,
        "onchainCosts": 178.79,
        "offchainCost": 263.62,
        "offchainCostPpm": 7899.56,
        "percentCosts": 0.332,
        "profit": 890.3,
        "profitPpm": 26678.74
    },
    {
        "date": "2024-08-15",
        "paymentsRouted": 6,
        "valueRouted": 65206,
        "revenue": 1521.55,
        "onchainCosts": 381.03,
        "offchainCost": 71.4,
        "offchainCostPpm": 1094.96,
        "percentCosts": 0.2973,
        "profit": 1069.12,
        "profitPpm": 16396.06
    },
    {
        "date": "2024-08-16",
        "paymentsRouted": 15,
        "valueRouted": 178768,
        "revenue": 3568.99,
        "onchainCosts": 143.25,
        "offchainCost": 289.01,
        "offchainCostPpm": 1616.67,
        "percentCosts": 0.1211,
        "profit": 3136.73,
        "profitPpm": 17546.38
    },
    {
        "date": "2024-08-17",
        "paymentsRouted": 3,
        "valueRouted": 192622,
        "revenue": 8989.69,
        "onchainCosts": 86.11,
        "offchainCost": 24.62,
        "offchainCostPpm": 127.84,
        "percentCosts": 0.0123,
        "profit": 8878.96,
        "profitPpm": 46095.24
    },
    {
        "date": "2024-08-18",
        "paymentsRouted": 15,
        "valueRouted": 98237,
        "revenue": 4696.0,
        "onchainCosts": 60.55,
        "offchainCost": 102.1,
        "offchainCostPpm": 1039.37,
        "percentCosts": 0.0346,
        "profit": 4533.34,
        "profitPpm": 46147.01
    },
    {
        "date": "2024-08-19",
        "paymentsRouted": 16,
        "valueRouted": 193690,
        "revenue": 5270.94,
        "onchainCosts": 292.52,
        "offchainCost": 206.4,
        "offchainCostPpm": 1065.6,
        "percentCosts": 0.0947,
        "profit": 4772.02,
        "profitPpm": 24637.41
    },
    {
        "date": "2024-08-20",
        "paymentsRouted": 10,
        "valueRouted": 136929,
        "revenue": 2511.07,
        "onchainCosts": 178.8,
        "offchainCost": 88.4,
        "offchainCostPpm": 645.58,
        "percentCosts": 0.1064,
        "profit": 2243.87,
        "profitPpm": 16387.13
    },
    {
        "date": "2024-08-21",
        "paymentsRouted": 7,
        "valueRouted": 162239,
        "revenue": 5783.19,
        "onchainCosts": 117.17,
        "offchainCost": 217.72,
        "offchainCostPpm": 1341.98,
        "percentCosts": 0.0579,
        "profit": 5448.29,
        "profitPpm": 33581.89
    },
    {
        "date": "2024-08-22",
        "paymentsRouted": 20,
        "valueRouted": 55825,
        "revenue": 2043.3,
        "onchainCosts": 326.7,
        "offchainCost": 210.03,
        "offchainCostPpm": 3762.3,
        "percentCosts": 0.2627,
        "profit": 1506.57,
        "profitPpm": 26987.41
    },
    {
        "date": "2024-08-23",
        "paymentsRouted": 15,
        "valueRouted": 37298,
        "revenue": 939.53,
        "onchainCosts": 344.19,
        "offchainCost": 245.24,
        "offchainCostPpm": 6575.2,
        "percentCosts": 0.6274,
        "profit": 350.1,
        "profitPpm": 9386.58
    },
    {
        "date": "2024-08-24",
        "paymentsRouted": 19,
        "valueRouted": 187082,
        "revenue": 8486.25,
        "onchainCosts": 101.84,
        "offchainCost": 274.12,
        "offchainCostPpm": 1465.26,
        "percentCosts": 0.0443,
        "profit": 8110.28,
        "profitPpm": 43351.47
    },
    {
        "date": "2024-08-25",
        "paymentsRouted": 10,
        "valueRouted": 9592,
        "revenue": 170.31,
        "onchainCosts": 360.59,
        "offchainCost": 73.4,
        "offchainCostPpm": 7652.36,
        "percentCosts": 2.5483,
        "profit": -263.68,
        "profitPpm": -27489.84
    },
    {
        "date": "2024-08-26",
        "paymentsRouted": 9,
        "valueRouted": 103877,
        "revenue": 4828.24,
        "onchainCosts": 195.35,
        "offchainCost": 289.39,
        "offchainCostPpm": 2785.89,
        "percentCosts": 0.1004,
        "profit": 4343.5,
        "profitPpm": 41813.84
    },
    {
        "date": "2024-08-27",
        "paymentsRouted": 17,
        "valueRouted": 160000,
        "revenue": 3336.05,
        "onchainCosts": 422.43,
        "offchainCost": 243.02,
        "offchainCostPpm": 1518.89,
        "percentCosts": 0.1995,
        "profit": 2670.6,
        "profitPpm": 16691.23
    },
    {
        "date": "2024-08-28",
        "paymentsRouted": 2,
        "valueRouted": 157238,
        "revenue": 2995.52,
        "onchainCosts": 355.89,
        "offchainCost": 258.31,
        "offchainCostPpm": 1642.81,
        "percentCosts": 0.205,
        "profit": 2381.32,
        "profitPpm": 15144.67
    },
    {
        "date": "2024-08-29",
        "paymentsRouted": 4,
        "valueRouted": 13275,
        "revenue": 534.96,
        "onchainCosts": 299.07,
        "offchainCost": 297.59,
        "offchainCostPpm": 22417.11,
        "percentCosts": 1.1153,
        "profit": -61.7,
        "profitPpm": -4647.83
    },
    {
        "date": "2024-08-30",
        "paymentsRouted": 4,
        "valueRouted": 11153,
        "revenue": 222.59,
        "onchainCosts": 105.12,
        "offchainCost": 259.0,
        "offchainCostPpm": 23222.05,
        "percentCosts": 1.6358,
        "profit": -141.52,
        "profitPpm": -12689.05
    },
    {
        "date": "2024-08-31",
        "paymentsRouted": 2,
        "valueRouted": 184251,
        "revenue": 7172.09,
        "onchainCosts": 326.73,
        "offchainCost": 262.91,
        "offchainCostPpm": 1426.89,
        "percentCosts": 0.0822,
        "profit": 6582.45,
        "profitPpm": 35725.47
    },
    {
        "date": "2024-09-01",
        "paymentsRouted": 15,
        "valueRouted": 127998,
        "revenue": 4722.63,
        "onchainCosts": 174.87,
        "offchainCost": 294.83,
        "offchainCostPpm": 2303.42,
        "percentCosts": 0.0995,
        "profit": 4252.92,
        "profitPpm": 33226.48
    },
    {
        "date": "2024-09-02",
        "paymentsRouted": 10,
        "valueRouted": 149646,
        "revenue": 6127.08,
        "onchainCosts": 333.42,
        "offchainCost": 141.05,
        "offchainCostPpm": 942.59,
        "percentCosts": 0.0774,
        "profit": 5652.6,
        "profitPpm": 37773.13
    },
    {
        "date": "2024-09-03",
        "paymentsRouted": 11,
        "valueRouted": 109307,
        "revenue": 4308.46,
        "onchainCosts": 220.27,
        "offchainCost": 46.3,
        "offchainCostPpm": 423.62,
        "percentCosts": 0.0619,
        "profit": 4041.89,
        "profitPpm": 36977.37
    },
    {
        "date": "2024-09-04",
        "paymentsRouted": 8,
        "valueRouted": 40664,
        "revenue": 1443.16,
        "onchainCosts": 158.44,
        "offchainCost": 139.5,
        "offchainCostPpm": 3430.45,
        "percentCosts": 0.2064,
        "profit": 1145.23,
        "profitPpm": 28163.19
    },
    {
        "date": "2024-09-05",
        "paymentsRouted": 6,
        "valueRouted": 29343,
        "revenue": 691.54,
        "onchainCosts": 80.51,
        "offchainCost": 243.38,
        "offchainCostPpm": 8294.42,
        "percentCosts": 0.4684,
        "profit": 367.65,
        "profitPpm": 12529.48
    },
    {
        "date": "2024-09-06",
        "paymentsRouted": 1,
        "valueRouted": 186479,
        "revenue": 3263.51,
        "onchainCosts": 271.24,
        "offchainCost": 171.6,
        "offchainCostPpm": 920.2,
        "percentCosts": 0.1357,
        "profit": 2820.66,
        "profitPpm": 15125.9
    },
    {
        "date": "2024-09-07",
        "paymentsRouted": 13,
        "valueRouted": 186677,
        "revenue": 6700.79,
        "onchainCosts": 194.11,
        "offchainCost": 220.46,
        "offchainCostPpm": 1180.96,
        "percentCosts": 0.0619,
        "profit": 6286.22,
        "profitPpm": 33674.33
    },
    {
        "date": "2024-09-08",
        "paymentsRouted": 12,
        "valueRouted": 32114,
        "revenue": 837.36,
        "onchainCosts": 319.76,
        "offchainCost": 259.84,
        "offchainCostPpm": 8091.08,
        "percentCosts": 0.6922,
        "profit": 257.76,
        "profitPpm": 8026.51
    },
    {
        "date": "2024-09-09",
        "paymentsRouted": 14,
        "valueRouted": 80244,
        "revenue": 3624.85,
        "onchainCosts": 329.12,
        "offchainCost": 71.49,
        "offchainCostPpm": 890.93,
        "percentCosts": 0.1105,
        "profit": 3224.24,
        "profitPpm": 40180.5
    },
    {
        "date": "2024-09-10",
        "paymentsRouted": 7,
        "valueRouted": 112434,
        "revenue": 3158.55,
        "onchainCosts": 381.83,
        "offchainCost": 237.54,
        "offchainCostPpm": 2112.74,
        "percentCosts": 0.1961,
        "profit": 2539.18,
        "profitPpm": 22583.73
    },
    {
        "date": "2024-09-11",
        "paymentsRouted": 11,
        "valueRouted": 71394,
        "revenue": 714.05,
        "onchainCosts": 254.47,
        "offchainCost": 114.97,
        "offchainCostPpm": 1610.36,
        "percentCosts": 0.5174,
        "profit": 344.61,
        "profitPpm": 4826.85
    },
    {
        "date": "2024-09-12",
        "paymentsRouted": 14,
        "valueRouted": 10838,
        "revenue": 493.37,
        "onchainCosts": 403.04,
        "offchainCost": 133.09,
        "offchainCostPpm": 12279.78,
        "percentCosts": 1.0867,
        "profit": -42.75,
        "profitPpm": -3944.88
    },
    {
        "date": "2024-09-13",
        "paymentsRouted": 17,
        "valueRouted": 145381,
        "revenue": 2590.97,
        "onchainCosts": 217.96,
        "offchainCost": 245.37,
        "offchainCostPpm": 1687.74,
        "percentCosts": 0.1788,
        "profit": 2127.65,
        "profitPpm": 14634.97
    },
    {
        "date": "2024-09-14",
        "paymentsRouted": 7,
        "valueRouted": 118989,
        "revenue": 5240.18,
        "onchainCosts": 176.01,
        "offchainCost": 249.9,
        "offchainCostPpm": 2100.23,
        "percentCosts": 0.0813,
        "profit": 4814.27,
        "profitPpm": 40459.78
    },
    {
        "date": "2024-09-15",
        "paymentsRouted": 13,
        "valueRouted": 19408,
        "revenue": 665.0,
        "onchainCosts": 56.16,
        "offchainCost": 252.15,
        "offchainCostPpm": 12992.04,
        "percentCosts": 0.4636,
        "profit": 356.69,
        "profitPpm": 18378.72
    },
    {
        "date": "2024-09-16",
        "paymentsRouted": 7,
        "valueRouted": 18971,
        "revenue": 290.15,
        "onchainCosts": 260.01,
        "offchainCost": 60.45,
        "offchainCostPpm": 3186.64,
        "percentCosts": 1.1045,
        "profit": -30.32,
        "profitPpm": -1598.08
    },
    {
        "date": "2024-09-17",
        "paymentsRouted": 11,
        "valueRouted": 100719,
        "revenue": 3991.74,
        "onchainCosts": 283.66,
        "offchainCost": 131.83,
        "offchainCostPpm": 1308.85,
        "percentCosts": 0.1041,
        "profit": 3576.25,
        "profitPpm": 35507.19
    },
    {
        "date": "2024-09-18",
        "paymentsRouted": 14,
        "valueRouted": 120767,
        "revenue": 3778.66,
        "onchainCosts": 443.2,
        "offchainCost": 20.72,
        "offchainCostPpm": 171.56,
        "percentCosts": 0.1228,
        "profit": 3314.74,
        "profitPpm": 27447.41
    },
    {
        "date": "2024-09-19",
        "paymentsRouted": 15,
        "valueRouted": 161337,
        "revenue": 7995.03,
        "onchainCosts": 412.02,
        "offchainCost": 241.96,
        "offchainCostPpm": 1499.71,
        "percentCosts": 0.0818,
        "profit": 7341.05,
        "profitPpm": 45501.35
    },
    {
        "date": "2024-09-20",
        "paymentsRouted": 15,
        "valueRouted": 169563,
        "revenue": 5285.43,
        "onchainCosts": 231.32,
        "offchainCost": 125.72,
        "offchainCostPpm": 741.41,
        "percentCosts": 0.0676,
        "profit": 4928.4,
        "profitPpm": 29065.3
    },
    {
        "date": "2024-09-21",
        "paymentsRouted": 6,
        "valueRouted": 6456,
        "revenue": 119.26,
        "onchainCosts": 266.75,
        "offchainCost": 151.65,
        "offchainCostPpm": 23490.51,
        "percentCosts": 3.5085,
        "profit": -299.15,
        "profitPpm": -46336.58
    },
    {
        "date": "2024-09-22",
        "paymentsRouted": 19,
        "valueRouted": 127769,
        "revenue": 2700.98,
        "onchainCosts": 220.12,
        "offchainCost": 59.78,
        "offchainCostPpm": 467.89,
        "percentCosts": 0.1036,
        "profit": 2421.08,
        "profitPpm": 18948.87
    },
    {
        "date": "2024-09-23",
        "paymentsRouted": 16,
        "valueRouted": 95244,
        "revenue": 1613.91,
        "onchainCosts": 352.47,
        "offchainCost": 38.28,
        "offchainCostPpm": 401.92,
        "percentCosts": 0.2421,
        "profit": 1223.16,
        "profitPpm": 12842.39
    },
    {
        "date": "2024-09-24",
        "paymentsRouted": 8,
        "valueRouted": 96846,
        "revenue": 4600.35,
        "onchainCosts": 279.17,
        "offchainCost": 285.26,
        "offchainCostPpm": 2945.48,
        "percentCosts": 0.1227,
        "profit": 4035.92,
        "profitPpm": 41673.54
    },
    {
        "date": "2024-09-25",
        "paymentsRouted": 8,
        "valueRouted": 136446,
        "revenue": 3467.96,
        "onchainCosts": 449.45,
        "offchainCost": 143.0,
        "offchainCostPpm": 1048.0,
        "percentCosts": 0.1708,
        "profit": 2875.51,
        "profitPpm": 21074.36
    },
    {
        "date": "2024-09-26",
        "paymentsRouted": 9,
        "valueRouted": 124583,
        "revenue": 3416.27,
        "onchainCosts": 198.02,
        "offchainCost": 175.08,
        "offchainCostPpm": 1405.36,
        "percentCosts": 0.1092,
        "profit": 3043.17,
        "profitPpm": 24426.87
    },
    {
        "date": "2024-09-27",
        "paymentsRouted": 1,
        "valueRouted": 128584,
        "revenue": 5441.99,
        "onchainCosts": 129.35,
        "offchainCost": 79.49,
        "offchainCostPpm": 618.18,
        "percentCosts": 0.0384,
        "profit": 5233.15,
        "profitPpm": 40698.32
    },
    {
        "date": "2024-09-28",
        "paymentsRouted": 10,
        "valueRouted": 79462,
        "revenue": 3322.66,
        "onchainCosts": 113.95,
        "offchainCost": 121.56,
        "offchainCostPpm": 1529.78,
        "percentCosts": 0.0709,
        "profit": 3087.14,
        "profitPpm": 38850.57
    },
    {
        "date": "2024-09-29",
        "paymentsRouted": 13,
        "valueRouted": 66337,
        "revenue": 2794.65,
        "onchainCosts": 330.58,
        "offchainCost": 211.89,
        "offchainCostPpm": 3194.19,
        "percentCosts": 0.1941,
        "profit": 2252.18,
        "profitPpm": 33950.55
    },
    {
        "date": "2024-09-30",
        "paymentsRouted": 15,
        "valueRouted": 41448,
        "revenue": 1154.72,
        "onchainCosts": 146.67,
        "offchainCost": 22.12,
        "offchainCostPpm": 533.69,
        "percentCosts": 0.1462,
        "profit": 985.93,
        "profitPpm": 23787.21
    },
    {
        "date": "2024-10-01",
        "paymentsRouted": 11,
        "valueRouted": 41573,
        "revenue": 1918.12,
        "onchainCosts": 284.55,
        "offchainCost": 156.53,
        "offchainCostPpm": 3765.08,
        "percentCosts": 0.23,
        "profit": 1477.05,
        "profitPpm": 35528.97
    },
    {
        "date": "2024-10-02",
        "paymentsRouted": 4,
        "valueRouted": 137380,
        "revenue": 5312.76,
        "onchainCosts": 375.14,
        "offchainCost": 228.53,
        "offchainCostPpm": 1663.47,
        "percentCosts": 0.1136,
        "profit": 4709.1,
        "profitPpm": 34277.89
    },
    {
        "date": "2024-10-03",
        "paymentsRouted": 9,
        "valueRouted": 68867,
        "revenue": 3091.67,
        "onchainCosts": 439.49,
        "offchainCost": 64.44,
        "offchainCostPpm": 935.65,
        "percentCosts": 0.163,
        "profit": 2587.75,
        "profitPpm": 37576.03
    },
    {
        "date": "2024-10-04",
        "paymentsRouted": 9,
        "valueRouted": 21741,
        "revenue": 770.5,
        "onchainCosts": 185.9,
        "offchainCost": 74.55,
        "offchainCostPpm": 3428.84,
        "percentCosts": 0.338,
        "profit": 510.05,
        "profitPpm": 23460.15
    },
    {
        "date": "2024-10-05",
        "paymentsRouted": 16,
        "valueRouted": 38710,
        "revenue": 857.64,
        "onchainCosts": 217.64,
        "offchainCost": 76.39,
        "offchainCostPpm": 1973.34,
        "percentCosts": 0.3428,
        "profit": 563.61,
        "profitPpm": 14559.88
    },
    {
        "date": "2024-10-06",
        "paymentsRouted": 15,
        "valueRouted": 163749,
        "revenue": 7492.64,
        "onchainCosts": 255.17,
        "offchainCost": 90.79,
        "offchainCostPpm": 554.42,
        "percentCosts": 0.0462,
        "profit": 7146.68,
        "profitPpm": 43644.11
    },
    {
        "date": "2024-10-07",
        "paymentsRouted": 5,
        "valueRouted": 87609,
        "revenue": 2206.77,
        "onchainCosts": 160.31,
        "offchainCost": 21.1,
        "offchainCostPpm": 240.85,
        "percentCosts": 0.0822,
        "profit": 2025.36,
        "profitPpm": 23118.19
    },
    {
        "date": "2024-10-08",
        "paymentsRouted": 1,
        "valueRouted": 144565,
        "revenue": 2351.98,
        "onchainCosts": 189.74,
        "offchainCost": 232.55,
        "offchainCostPpm": 1608.61,
        "percentCosts": 0.1795,
        "profit": 1929.69,
        "profitPpm": 13348.26
    },
    {
        "date": "2024-10-09",
        "paymentsRouted": 4,
        "valueRouted": 110268,
        "revenue": 5247.97,
        "onchainCosts": 131.97,
        "offchainCost": 50.33,
        "offchainCostPpm": 456.44,
        "percentCosts": 0.0347,
        "profit": 5065.67,
        "profitPpm": 45939.63
    },
    {
        "date": "2024-10-10",
        "paymentsRouted": 14,
        "valueRouted": 61049,
        "revenue": 2922.3,
        "onchainCosts": 352.2,
        "offchainCost": 193.23,
        "offchainCostPpm": 3165.13,
        "percentCosts": 0.1866,
        "profit": 2376.87,
        "profitPpm": 38933.83
    },
    {
        "date": "2024-10-11",
        "paymentsRouted": 11,
        "valueRouted": 15101,
        "revenue": 460.21,
        "onchainCosts": 238.76,
        "offchainCost": 175.87,
        "offchainCostPpm": 11646.04,
        "percentCosts": 0.901,
        "profit": 45.58,
        "profitPpm": 3018.51
    },
    {
        "date": "2024-10-12",
        "paymentsRouted": 11,
        "valueRouted": 57126,
        "revenue": 2529.34,
        "onchainCosts": 156.08,
        "offchainCost": 226.05,
        "offchainCostPpm": 3957.01,
        "percentCosts": 0.1511,
        "profit": 2147.21,
        "profitPpm": 37587.24
    },
    {
        "date": "2024-10-13",
        "paymentsRouted": 10,
        "valueRouted": 199157,
        "revenue": 8028.39,
        "onchainCosts": 224.73,
        "offchainCost": 234.29,
        "offchainCostPpm": 1176.4,
        "percentCosts": 0.0572,
        "profit": 7569.38,
        "profitPpm": 38007.09
    },
    {
        "date": "2024-10-14",
        "paymentsRouted": 14,
        "valueRouted": 13924,
        "revenue": 240.34,
        "onchainCosts": 221.65,
        "offchainCost": 170.49,
        "offchainCostPpm": 12244.32,
        "percentCosts": 1.6316,
        "profit": -151.79,
        "profitPpm": -10901.53
    },
    {
        "date": "2024-10-15",
        "paymentsRouted": 11,
        "valueRouted": 61087,
        "revenue": 2868.94,
        "onchainCosts": 468.77,
        "offchainCost": 39.19,
        "offchainCostPpm": 641.55,
        "percentCosts": 0.1771,
        "profit": 2360.99,
        "profitPpm": 38649.56
    },
    {
        "date": "2024-10-16",
        "paymentsRouted": 4,
        "valueRouted": 7398,
        "revenue": 189.57,
        "onchainCosts": 77.06,
        "offchainCost": 296.79,
        "offchainCostPpm": 40118.0,
        "percentCosts": 1.9721,
        "profit": -184.29,
        "profitPpm": -24910.27
    },
    {
        "date": "2024-10-17",
        "paymentsRouted": 10,
        "valueRouted": 193429,
        "revenue": 4600.28,
        "onchainCosts": 173.22,
        "offchainCost": 263.44,
        "offchainCostPpm": 1361.96,
        "percentCosts": 0.0949,
        "profit": 4163.61,
        "profitPpm": 21525.29
    },
    {
        "date": "2024-10-18",
        "paymentsRouted": 3,
        "valueRouted": 117189,
        "revenue": 3167.59,
        "onchainCosts": 55.1,
        "offchainCost": 144.94,
        "offchainCostPpm": 1236.78,
        "percentCosts": 0.0632,
        "profit": 2967.56,
        "profitPpm": 25322.85
    },
    {
        "date": "2024-10-19",
        "paymentsRouted": 16,
        "valueRouted": 24661,
        "revenue": 1067.75,
        "onchainCosts": 304.62,
        "offchainCost": 135.87,
        "offchainCostPpm": 5509.49,
        "percentCosts": 0.4125,
        "profit": 627.26,
        "profitPpm": 25435.4
    },
    {
        "date": "2024-10-20",
        "paymentsRouted": 16,
        "valueRouted": 72334,
        "revenue": 2762.99,
        "onchainCosts": 161.16,
        "offchainCost": 160.47,
        "offchainCostPpm": 2218.42,
        "percentCosts": 0.1164,
        "profit": 2441.37,
        "profitPpm": 33751.31
    },
    {
        "date": "2024-10-21",
        "paymentsRouted": 5,
        "valueRouted": 9833,
        "revenue": 101.55,
        "onchainCosts": 315.5,
        "offchainCost": 245.1,
        "offchainCostPpm": 24926.56,
        "percentCosts": 5.5204,
        "profit": -459.05,
        "profitPpm": -46684.99
    },
    {
        "date": "2024-10-22",
        "paymentsRouted": 13,
        "valueRouted": 63439,
        "revenue": 2334.82,
        "onchainCosts": 346.08,
        "offchainCost": 212.99,
        "offchainCostPpm": 3357.47,
        "percentCosts": 0.2395,
        "profit": 1775.75,
        "profitPpm": 27991.42
    },
    {
        "date": "2024-10-23",
        "paymentsRouted": 14,
        "valueRouted": 56075,
        "revenue": 962.59,
        "onchainCosts": 443.67,
        "offchainCost": 137.35,
        "offchainCostPpm": 2449.34,
        "percentCosts": 0.6036,
        "profit": 381.57,
        "profitPpm": 6804.71
    },
    {
        "date": "2024-10-24",
        "paymentsRouted": 14,
        "valueRouted": 74586,
        "revenue": 1830.63,
        "onchainCosts": 334.62,
        "offchainCost": 268.73,
        "offchainCostPpm": 3602.95,
        "percentCosts": 0.3296,
        "profit": 1227.28,
        "profitPpm": 16454.61
    },
    {
        "date": "2024-10-25",
        "paymentsRouted": 14,
        "valueRouted": 11395,
        "revenue": 260.02,
        "onchainCosts": 350.05,
        "offchainCost": 295.73,
        "offchainCostPpm": 25952.34,
        "percentCosts": 2.4836,
        "profit": -385.76,
        "profitPpm": -33853.54
    },
    {
        "date": "2024-10-26",
        "paymentsRouted": 12,
        "valueRouted": 132796,
        "revenue": 1605.23,
        "onchainCosts": 71.73,
        "offchainCost": 184.5,
        "offchainCostPpm": 1389.38,
        "percentCosts": 0.1596,
        "profit": 1348.99,
        "profitPpm": 10158.38
    },
    {
        "date": "2024-10-27",
        "paymentsRouted": 7,
        "valueRouted": 49002,
        "revenue": 2410.66,
        "onchainCosts": 135.46,
        "offchainCost": 26.1,
        "offchainCostPpm": 532.63,
        "percentCosts": 0.067,
        "profit": 2249.1,
        "profitPpm": 45898.21
    },
    {
        "date": "2024-10-28",
        "paymentsRouted": 20,
        "valueRouted": 133237,
        "revenue": 3037.55,
        "onchainCosts": 418.13,
        "offchainCost": 246.88,
        "offchainCostPpm": 1852.91,
        "percentCosts": 0.2189,
        "profit": 2372.54,
        "profitPpm": 17806.93
    },
    {
        "date": "2024-10-29",
        "paymentsRouted": 6,
        "valueRouted": 25247,
        "revenue": 990.91,
        "onchainCosts": 266.38,
        "offchainCost": 193.21,
        "offchainCostPpm": 7652.83,
        "percentCosts": 0.4638,
        "profit": 531.31,
        "profitPpm": 21044.57
    },
    {
        "date": "2024-10-30",
        "paymentsRouted": 20,
        "valueRouted": 82684,
        "revenue": 3352.38,
        "onchainCosts": 216.44,
        "offchainCost": 69.64,
        "offchainCostPpm": 842.25,
        "percentCosts": 0.0853,
        "profit": 3066.3,
        "profitPpm": 37084.6
    },
    {
        "date": "2024-10-31",
        "paymentsRouted": 15,
        "valueRouted": 13143,
        "revenue": 207.36,
        "onchainCosts": 428.89,
        "offchainCost": 78.31,
        "offchainCostPpm": 5958.23,
        "percentCosts": 2.446,
        "profit": -299.83,
        "profitPpm": -22813.25
    },
    {
        "date": "2024-11-01",
        "paymentsRouted": 14,
        "valueRouted": 110004,
        "revenue": 4349.52,
        "onchainCosts": 150.6,
        "offchainCost": 92.95,
        "offchainCostPpm": 844.99,
        "percentCosts": 0.056,
        "profit": 4105.97,
        "profitPpm": 37325.64
    },
    {
        "date": "2024-11-02",
        "paymentsRouted": 7,
        "valueRouted": 68052,
        "revenue": 2632.28,
        "onchainCosts": 393.87,
        "offchainCost": 255.01,
        "offchainCostPpm": 3747.34,
        "percentCosts": 0.2465,
        "profit": 1983.4,
        "profitPpm": 29145.34
    },
    {
        "date": "2024-11-03",
        "paymentsRouted": 3,
        "valueRouted": 11169,
        "revenue": 249.91,
        "onchainCosts": 274.91,
        "offchainCost": 200.68,
        "offchainCostPpm": 17967.44,
        "percentCosts": 1.903,
        "profit": -225.68,
        "profitPpm": -20205.86
    },
    {
        "date": "2024-11-04",
        "paymentsRouted": 16,
        "valueRouted": 141472,
        "revenue": 3979.21,
        "onchainCosts": 185.64,
        "offchainCost": 103.89,
        "offchainCostPpm": 734.36,
        "percentCosts": 0.0728,
        "profit": 3689.68,
        "profitPpm": 26080.63
    },
    {
        "date": "2024-11-05",
        "paymentsRouted": 11,
        "valueRouted": 124266,
        "revenue": 5999.61,
        "onchainCosts": 303.12,
        "offchainCost": 62.96,
        "offchainCostPpm": 506.67,
        "percentCosts": 0.061,
        "profit": 5633.53,
        "profitPpm": 45334.45
    },
    {
        "date": "2024-11-06",
        "paymentsRouted": 20,
        "valueRouted": 61888,
        "revenue": 1015.73,
        "onchainCosts": 426.08,
        "offchainCost": 10.57,
        "offchainCostPpm": 170.86,
        "percentCosts": 0.4299,
        "profit": 579.08,
        "profitPpm": 9356.88
    },
    {
        "date": "2024-11-07",
        "paymentsRouted": 12,
        "valueRouted": 50708,
        "revenue": 1906.91,
        "onchainCosts": 198.09,
        "offchainCost": 247.14,
        "offchainCostPpm": 4873.78,
        "percentCosts": 0.2335,
        "profit": 1461.68,
        "profitPpm": 28825.49
    },
    {
        "date": "2024-11-08",
        "paymentsRouted": 5,
        "valueRouted": 142045,
        "revenue": 5547.73,
        "onchainCosts": 113.46,
        "offchainCost": 229.02,
        "offchainCostPpm": 1612.28,
        "percentCosts": 0.0617,
        "profit": 5205.26,
        "profitPpm": 36645.11
    },
    {
        "date": "2024-11-09",
        "paymentsRouted": 8,
        "valueRouted": 113036,
        "revenue": 3632.79,
        "onchainCosts": 363.35,
        "offchainCost": 103.52,
        "offchainCostPpm": 915.86,
        "percentCosts": 0.1285,
        "profit": 3165.91,
        "profitPpm": 28008.0
    },
    {
        "date": "2024-11-10",
        "paymentsRouted": 7,
        "valueRouted": 199869,
        "revenue": 7643.48,
        "onchainCosts": 236.24,
        "offchainCost": 25.57,
        "offchainCostPpm": 127.95,
        "percentCosts": 0.0343,
        "profit": 7381.67,
        "profitPpm": 36932.55
    },
    {
        "date": "2024-11-11",
        "paymentsRouted": 13,
        "valueRouted": 141220,
        "revenue": 1742.04,
        "onchainCosts": 434.95,
        "offchainCost": 15.59,
        "offchainCostPpm": 110.4,
        "percentCosts": 0.2586,
        "profit": 1291.5,
        "profitPpm": 9145.31
    },
    {
        "date": "2024-11-12",
        "paymentsRouted": 4,
        "valueRouted": 52098,
        "revenue": 2290.89,
        "onchainCosts": 124.77,
        "offchainCost": 82.49,
        "offchainCostPpm": 1583.3,
        "percentCosts": 0.0905,
        "profit": 2083.64,
        "profitPpm": 39994.63
    },
    {
        "date": "2024-11-13",
        "paymentsRouted": 5,
        "valueRouted": 172050,
        "revenue": 1801.42,
        "onchainCosts": 220.11,
        "offchainCost": 284.96,
        "offchainCostPpm": 1656.24,
        "percentCosts": 0.2804,
        "profit": 1296.36,
        "profitPpm": 7534.8
    },
    {
        "date": "2024-11-14",
        "paymentsRouted": 9,
        "valueRouted": 11788,
        "revenue": 184.93,
        "onchainCosts": 159.28,
        "offchainCost": 38.68,
        "offchainCostPpm": 3281.25,
        "percentCosts": 1.0705,
        "profit": -13.03,
        "profitPpm": -1105.54
    },
    {
        "date": "2024-11-15",
        "paymentsRouted": 20,
        "valueRouted": 105076,
        "revenue": 3243.65,
        "onchainCosts": 394.93,
        "offchainCost": 77.87,
        "offchainCostPpm": 741.11,
        "percentCosts": 0.1458,
        "profit": 2770.85,
        "profitPpm": 26369.94
    },
    {
        "date": "2024-11-16",
        "paymentsRouted": 3,
        "valueRouted": 35248,
        "revenue": 1671.35,
        "onchainCosts": 467.53,
        "offchainCost": 195.8,
        "offchainCostPpm": 5554.82,
        "percentCosts": 0.3969,
        "profit": 1008.02,
        "profitPpm": 28598.0
    },
    {
        "date": "2024-11-17",
        "paymentsRouted": 3,
        "valueRouted": 89228,
        "revenue": 4227.37,
        "onchainCosts": 109.22,
        "offchainCost": 129.74,
        "offchainCostPpm": 1454.06,
        "percentCosts": 0.0565,
        "profit": 3988.41,
        "profitPpm": 44699.06
    },
    {
        "date": "2024-11-18",
        "paymentsRouted": 7,
        "valueRouted": 67985,
        "revenue": 3151.31,
        "onchainCosts": 413.84,
        "offchainCost": 182.33,
        "offchainCostPpm": 2681.94,
        "percentCosts": 0.1892,
        "profit": 2555.14,
        "profitPpm": 37583.86
    },
    {
        "date": "2024-11-19",
        "paymentsRouted": 20,
        "valueRouted": 140481,
        "revenue": 2262.44,
        "onchainCosts": 344.87,
        "offchainCost": 299.95,
        "offchainCostPpm": 2135.15,
        "percentCosts": 0.285,
        "profit": 1617.62,
        "profitPpm": 11514.87
    },
    {
        "date": "2024-11-20",
        "paymentsRouted": 12,
        "valueRouted": 91728,
        "revenue": 4143.64,
        "onchainCosts": 414.41,
        "offchainCost": 49.07,
        "offchainCostPpm": 534.9,
        "percentCosts": 0.1119,
        "profit": 3680.17,
        "profitPpm": 40120.46
    },
    {
        "date": "2024-11-21",
        "paymentsRouted": 8,
        "valueRouted": 191257,
        "revenue": 6577.54,
        "onchainCosts": 487.96,
        "offchainCost": 182.2,
        "offchainCostPpm": 952.67,
        "percentCosts": 0.1019,
        "profit": 5907.38,
        "profitPpm": 30887.12
    },
    {
        "date": "2024-11-22",
        "paymentsRouted": 2,
        "valueRouted": 82899,
        "revenue": 3375.55,
        "onchainCosts": 177.74,
        "offchainCost": 183.52,
        "offchainCostPpm": 2213.79,
        "percentCosts": 0.107,
        "profit": 3014.29,
        "profitPpm": 36361.0
    },
    {
        "date": "2024-11-23",
        "paymentsRouted": 4,
        "valueRouted": 158812,
        "revenue": 4006.47,
        "onchainCosts": 362.14,
        "offchainCost": 50.51,
        "offchainCostPpm": 318.07,
        "percentCosts": 0.103,
        "profit": 3593.82,
        "profitPpm": 22629.39
    },
    {
        "date": "2024-11-24",
        "paymentsRouted": 6,
        "valueRouted": 49268,
        "revenue": 1079.63,
        "onchainCosts": 442.55,
        "offchainCost": 63.76,
        "offchainCostPpm": 1294.08,
        "percentCosts": 0.469,
        "profit": 573.32,
        "profitPpm": 11636.7
    },
    {
        "date": "2024-11-25",
        "paymentsRouted": 20,
        "valueRouted": 27530,
        "revenue": 994.53,
        "onchainCosts": 66.05,
        "offchainCost": 247.89,
        "offchainCostPpm": 9004.28,
        "percentCosts": 0.3157,
        "profit": 680.59,
        "profitPpm": 24721.6
    },
    {
        "date": "2024-11-26",
        "paymentsRouted": 12,
        "valueRouted": 199133,
        "revenue": 5310.79,
        "onchainCosts": 480.13,
        "offchainCost": 256.79,
        "offchainCostPpm": 1289.53,
        "percentCosts": 0.1388,
        "profit": 4573.88,
        "profitPpm": 22968.96
    },
    {
        "date": "2024-11-27",
        "paymentsRouted": 7,
        "valueRouted": 45569,
        "revenue": 1837.61,
        "onchainCosts": 378.53,
        "offchainCost": 122.09,
        "offchainCostPpm": 2679.16,
        "percentCosts": 0.2724,
        "profit": 1337.0,
        "profitPpm": 29340.03
    },
    {
        "date": "2024-11-28",
        "paymentsRouted": 12,
        "valueRouted": 48797,
        "revenue": 2417.43,
        "onchainCosts": 137.38,
        "offchainCost": 213.0,
        "offchainCostPpm": 4364.98,
        "percentCosts": 0.1449,
        "profit": 2067.05,
        "profitPpm": 42360.27
    },
    {
        "date": "2024-11-29",
        "paymentsRouted": 13,
        "valueRouted": 11559,
        "revenue": 177.54,
        "onchainCosts": 219.5,
        "offchainCost": 114.32,
        "offchainCostPpm": 9889.97,
        "percentCosts": 1.8803,
        "profit": -156.29,
        "profitPpm": -13520.64
    },
    {
        "date": "2024-11-30",
        "paymentsRouted": 16,
        "valueRouted": 71843,
        "revenue": 1997.81,
        "onchainCosts": 174.76,
        "offchainCost": 274.77,
        "offchainCostPpm": 3824.54,
        "percentCosts": 0.225,
        "profit": 1548.28,
        "profitPpm": 21550.95
    },
    {
        "date": "2024-12-01",
        "paymentsRouted": 20,
        "valueRouted": 99741,
        "revenue": 4615.84,
        "onchainCosts": 54.82,
        "offchainCost": 111.34,
        "offchainCostPpm": 1116.29,
        "percentCosts": 0.036,
        "profit": 4449.68,
        "profitPpm": 44612.37
    },
    {
        "date": "2024-12-02",
        "paymentsRouted": 15,
        "valueRouted": 193357,
        "revenue": 9401.41,
        "onchainCosts": 129.37,
        "offchainCost": 205.82,
        "offchainCostPpm": 1064.46,
        "percentCosts": 0.0357,
        "profit": 9066.22,
        "profitPpm": 46888.5
    },
    {
        "date": "2024-12-03",
        "paymentsRouted": 12,
        "valueRouted": 37753,
        "revenue": 1093.45,
        "onchainCosts": 388.81,
        "offchainCost": 149.92,
        "offchainCostPpm": 3971.14,
        "percentCosts": 0.4927,
        "profit": 554.71,
        "profitPpm": 14693.16
    },
    {
        "date": "2024-12-04",
        "paymentsRouted": 1,
        "valueRouted": 97413,
        "revenue": 3947.43,
        "onchainCosts": 280.89,
        "offchainCost": 225.7,
        "offchainCostPpm": 2316.9,
        "percentCosts": 0.1283,
        "profit": 3440.84,
        "profitPpm": 35322.19
    },
    {
        "date": "2024-12-05",
        "paymentsRouted": 16,
        "valueRouted": 153655,
        "revenue": 3672.89,
        "onchainCosts": 81.51,
        "offchainCost": 262.27,
        "offchainCostPpm": 1706.85,
        "percentCosts": 0.0936,
        "profit": 3329.11,
        "profitPpm": 21666.12
    },
    {
        "date": "2024-12-06",
        "paymentsRouted": 7,
        "valueRouted": 194541,
        "revenue": 5690.11,
        "onchainCosts": 406.04,
        "offchainCost": 298.42,
        "offchainCostPpm": 1533.99,
        "percentCosts": 0.1238,
        "profit": 4985.64,
        "profitPpm": 25627.73
    },
    {
        "date": "2024-12-07",
        "paymentsRouted": 2,
        "valueRouted": 174728,
        "revenue": 5303.46,
        "onchainCosts": 376.35,
        "offchainCost": 166.68,
        "offchainCostPpm": 953.92,
        "percentCosts": 0.1024,
        "profit": 4760.44,
        "profitPpm": 27244.83
    },
    {
        "date": "2024-12-08",
        "paymentsRouted": 18,
        "valueRouted": 134305,
        "revenue": 3618.39,
        "onchainCosts": 255.6,
        "offchainCost": 82.8,
        "offchainCostPpm": 616.51,
        "percentCosts": 0.0935,
        "profit": 3279.99,
        "profitPpm": 24421.96
    },
    {
        "date": "2024-12-09",
        "paymentsRouted": 14,
        "valueRouted": 173435,
        "revenue": 2294.01,
        "onchainCosts": 141.1,
        "offchainCost": 233.12,
        "offchainCostPpm": 1344.16,
        "percentCosts": 0.1631,
        "profit": 1919.78,
        "profitPpm": 11069.19
    },
    {
        "date": "2024-12-10",
        "paymentsRouted": 6,
        "valueRouted": 134906,
        "revenue": 1726.16,
        "onchainCosts": 254.34,
        "offchainCost": 108.98,
        "offchainCostPpm": 807.85,
        "percentCosts": 0.2105,
        "profit": 1362.84,
        "profitPpm": 10102.13
    },
    {
        "date": "2024-12-11",
        "paymentsRouted": 16,
        "valueRouted": 147238,
        "revenue": 1910.15,
        "onchainCosts": 139.99,
        "offchainCost": 47.45,
        "offchainCostPpm": 322.29,
        "percentCosts": 0.0981,
        "profit": 1722.71,
        "profitPpm": 11700.18
    },
    {
        "date": "2024-12-12",
        "paymentsRouted": 11,
        "valueRouted": 102635,
        "revenue": 1445.06,
        "onchainCosts": 192.21,
        "offchainCost": 192.41,
        "offchainCostPpm": 1874.69,
        "percentCosts": 0.2662,
        "profit": 1060.44,
        "profitPpm": 10332.15
    },
    {
        "date": "2024-12-13",
        "paymentsRouted": 1,
        "valueRouted": 5628,
        "revenue": 137.58,
        "onchainCosts": 205.31,
        "offchainCost": 141.05,
        "offchainCostPpm": 25062.78,
        "percentCosts": 2.5174,
        "profit": -208.78,
        "profitPpm": -37096.04
    },
    {
        "date": "2024-12-14",
        "paymentsRouted": 11,
        "valueRouted": 199457,
        "revenue": 6686.63,
        "onchainCosts": 209.54,
        "offchainCost": 172.99,
        "offchainCostPpm": 867.32,
        "percentCosts": 0.0572,
        "profit": 6304.09,
        "profitPpm": 31606.27
    },
    {
        "date": "2024-12-15",
        "paymentsRouted": 14,
        "valueRouted": 32811,
        "revenue": 1457.28,
        "onchainCosts": 377.35,
        "offchainCost": 89.13,
        "offchainCostPpm": 2716.55,
        "percentCosts": 0.3201,
        "profit": 990.79,
        "profitPpm": 30196.94
    },
    {
        "date": "2024-12-16",
        "paymentsRouted": 15,
        "valueRouted": 126376,
        "revenue": 3003.87,
        "onchainCosts": 277.57,
        "offchainCost": 260.2,
        "offchainCostPpm": 2058.95,
        "percentCosts": 0.179,
        "profit": 2466.1,
        "profitPpm": 19513.97
    },
    {
        "date": "2024-12-17",
        "paymentsRouted": 3,
        "valueRouted": 87529,
        "revenue": 2820.05,
        "onchainCosts": 183.86,
        "offchainCost": 157.49,
        "offchainCostPpm": 1799.27,
        "percentCosts": 0.121,
        "profit": 2478.71,
        "profitPpm": 28318.73
    },
    {
        "date": "2024-12-18",
        "paymentsRouted": 9,
        "valueRouted": 36376,
        "revenue": 862.56,
        "onchainCosts": 469.97,
        "offchainCost": 59.56,
        "offchainCostPpm": 1637.22,
        "percentCosts": 0.6139,
        "profit": 333.04,
        "profitPpm": 9155.43
    },
    {
        "date": "2024-12-19",
        "paymentsRouted": 15,
        "valueRouted": 48780,
        "revenue": 1700.64,
        "onchainCosts": 259.33,
        "offchainCost": 278.4,
        "offchainCostPpm": 5707.34,
        "percentCosts": 0.3162,
        "profit": 1162.9,
        "profitPpm": 23839.78
    },
    {
        "date": "2024-12-20",
        "paymentsRouted": 8,
        "valueRouted": 116172,
        "revenue": 3750.44,
        "onchainCosts": 348.86,
        "offchainCost": 238.28,
        "offchainCostPpm": 2051.09,
        "percentCosts": 0.1566,
        "profit": 3163.3,
        "profitPpm": 27229.46
    },
    {
        "date": "2024-12-21",
        "paymentsRouted": 5,
        "valueRouted": 36954,
        "revenue": 406.41,
        "onchainCosts": 196.4,
        "offchainCost": 92.37,
        "offchainCostPpm": 2499.65,
        "percentCosts": 0.7105,
        "profit": 117.64,
        "profitPpm": 3183.5
    },
    {
        "date": "2024-12-22",
        "paymentsRouted": 12,
        "valueRouted": 162512,
        "revenue": 5927.93,
        "onchainCosts": 109.79,
        "offchainCost": 89.81,
        "offchainCostPpm": 552.63,
        "percentCosts": 0.0337,
        "profit": 5728.33,
        "profitPpm": 35248.67
    },
    {
        "date": "2024-12-23",
        "paymentsRouted": 11,
        "valueRouted": 169540,
        "revenue": 5905.32,
        "onchainCosts": 441.35,
        "offchainCost": 206.18,
        "offchainCostPpm": 1216.11,
        "percentCosts": 0.1097,
        "profit": 5257.78,
        "profitPpm": 31012.04
    },
    {
        "date": "2024-12-24",
        "paymentsRouted": 4,
        "valueRouted": 123371,
        "revenue": 5297.46,
        "onchainCosts": 102.53,
        "offchainCost": 82.79,
        "offchainCostPpm": 671.05,
        "percentCosts": 0.035,
        "profit": 5112.14,
        "profitPpm": 41437.13
    },
    {
        "date": "2024-12-25",
        "paymentsRouted": 4,
        "valueRouted": 49713,
        "revenue": 796.13,
        "onchainCosts": 180.12,
        "offchainCost": 196.04,
        "offchainCostPpm": 3943.39,
        "percentCosts": 0.4725,
        "profit": 419.98,
        "profitPpm": 8448.02
    },
    {
        "date": "2024-12-26",
        "paymentsRouted": 14,
        "valueRouted": 15909,
        "revenue": 510.24,
        "onchainCosts": 475.64,
        "offchainCost": 87.27,
        "offchainCostPpm": 5485.65,
        "percentCosts": 1.1032,
        "profit": -52.67,
        "profitPpm": -3310.65
    },
    {
        "date": "2024-12-27",
        "paymentsRouted": 13,
        "valueRouted": 24113,
        "revenue": 321.8,
        "onchainCosts": 372.03,
        "offchainCost": 285.61,
        "offchainCostPpm": 11844.63,
        "percentCosts": 2.0436,
        "profit": -335.84,
        "profitPpm": -13927.76
    },
    {
        "date": "2024-12-28",
        "paymentsRouted": 6,
        "valueRouted": 38146,
        "revenue": 483.56,
        "onchainCosts": 401.84,
        "offchainCost": 100.12,
        "offchainCostPpm": 2624.56,
        "percentCosts": 1.0381,
        "profit": -18.4,
        "profitPpm": -482.44
    },
    {
        "date": "2024-12-29",
        "paymentsRouted": 14,
        "valueRouted": 156783,
        "revenue": 7201.09,
        "onchainCosts": 389.82,
        "offchainCost": 296.35,
        "offchainCostPpm": 1890.18,
        "percentCosts": 0.0953,
        "profit": 6514.92,
        "profitPpm": 41553.74
    },
    {
        "date": "2024-12-30",
        "paymentsRouted": 8,
        "valueRouted": 27442,
        "revenue": 1214.44,
        "onchainCosts": 345.61,
        "offchainCost": 145.66,
        "offchainCostPpm": 5308.08,
        "percentCosts": 0.4045,
        "profit": 723.16,
        "profitPpm": 26352.44
    },
    {
        "date": "2024-12-31",
        "paymentsRouted": 10,
        "valueRouted": 25578,
        "revenue": 993.21,
        "onchainCosts": 398.65,
        "offchainCost": 263.36,
        "offchainCostPpm": 10296.3,
        "percentCosts": 0.6665,
        "profit": 331.21,
        "profitPpm": 12948.97
    },
    {
        "date": "2025-01-01",
        "paymentsRouted": 17,
        "valueRouted": 139253,
        "revenue": 5337.11,
        "onchainCosts": 114.51,
        "offchainCost": 269.69,
        "offchainCostPpm": 1936.69,
        "percentCosts": 0.072,
        "profit": 4952.9,
        "profitPpm": 35567.67
    },
    {
        "date": "2025-01-02",
        "paymentsRouted": 9,
        "valueRouted": 132875,
        "revenue": 3006.96,
        "onchainCosts": 311.73,
        "offchainCost": 287.21,
        "offchainCostPpm": 2161.53,
        "percentCosts": 0.1992,
        "profit": 2408.02,
        "profitPpm": 18122.41
    },
    {
        "date": "2025-01-03",
        "paymentsRouted": 5,
        "valueRouted": 150925,
        "revenue": 6320.5,
        "onchainCosts": 324.73,
        "offchainCost": 247.24,
        "offchainCostPpm": 1638.17,
        "percentCosts": 0.0905,
        "profit": 5748.53,
        "profitPpm": 38088.64
    },
    {
        "date": "2025-01-04",
        "paymentsRouted": 17,
        "valueRouted": 46293,
        "revenue": 2187.77,
        "onchainCosts": 386.6,
        "offchainCost": 82.97,
        "offchainCostPpm": 1792.31,
        "percentCosts": 0.2146,
        "profit": 1718.2,
        "profitPpm": 37115.79
    },
    {
        "date": "2025-01-05",
        "paymentsRouted": 4,
        "valueRouted": 14232,
        "revenue": 573.27,
        "onchainCosts": 137.47,
        "offchainCost": 254.53,
        "offchainCostPpm": 17884.69,
        "percentCosts": 0.6838,
        "profit": 181.27,
        "profitPpm": 12736.95
    },
    {
        "date": "2025-01-06",
        "paymentsRouted": 18,
        "valueRouted": 128055,
        "revenue": 2707.96,
        "onchainCosts": 68.38,
        "offchainCost": 86.01,
        "offchainCostPpm": 671.64,
        "percentCosts": 0.057,
        "profit": 2553.58,
        "profitPpm": 19941.25
    },
    {
        "date": "2025-01-07",
        "paymentsRouted": 18,
        "valueRouted": 42567,
        "revenue": 982.39,
        "onchainCosts": 176.03,
        "offchainCost": 38.78,
        "offchainCostPpm": 910.97,
        "percentCosts": 0.2187,
        "profit": 767.58,
        "profitPpm": 18032.23
    },
    {
        "date": "2025-01-08",
        "paymentsRouted": 16,
        "valueRouted": 110575,
        "revenue": 5072.86,
        "onchainCosts": 150.7,
        "offchainCost": 161.16,
        "offchainCostPpm": 1457.46,
        "percentCosts": 0.0615,
        "profit": 4761.0,
        "profitPpm": 43056.71
    },
    {
        "date": "2025-01-09",
        "paymentsRouted": 7,
        "valueRouted": 131670,
        "revenue": 5418.73,
        "onchainCosts": 265.5,
        "offchainCost": 282.41,
        "offchainCostPpm": 2144.83,
        "percentCosts": 0.1011,
        "profit": 4870.82,
        "profitPpm": 36992.61
    },
    {
        "date": "2025-01-10",
        "paymentsRouted": 19,
        "valueRouted": 33218,
        "revenue": 906.45,
        "onchainCosts": 225.78,
        "offchainCost": 11.24,
        "offchainCostPpm": 338.41,
        "percentCosts": 0.2615,
        "profit": 669.43,
        "profitPpm": 20152.55
    },
    {
        "date": "2025-01-11",
        "paymentsRouted": 10,
        "valueRouted": 64763,
        "revenue": 2630.19,
        "onchainCosts": 457.04,
        "offchainCost": 298.17,
        "offchainCostPpm": 4604.01,
        "percentCosts": 0.2871,
        "profit": 1874.98,
        "profitPpm": 28951.38
    },
    {
        "date": "2025-01-12",
        "paymentsRouted": 13,
        "valueRouted": 69552,
        "revenue": 1497.16,
        "onchainCosts": 223.53,
        "offchainCost": 149.45,
        "offchainCostPpm": 2148.75,
        "percentCosts": 0.2491,
        "profit": 1124.18,
        "profitPpm": 16163.21
    },
    {
        "date": "2025-01-13",
        "paymentsRouted": 18,
        "valueRouted": 193877,
        "revenue": 2548.53,
        "onchainCosts": 321.32,
        "offchainCost": 105.42,
        "offchainCostPpm": 543.77,
        "percentCosts": 0.1674,
        "profit": 2121.79,
        "profitPpm": 10943.99
    },
    {
        "date": "2025-01-14",
        "paymentsRouted": 16,
        "valueRouted": 50740,
        "revenue": 1506.37,
        "onchainCosts": 148.21,
        "offchainCost": 213.4,
        "offchainCostPpm": 4205.74,
        "percentCosts": 0.2401,
        "profit": 1144.76,
        "profitPpm": 22561.31
    },
    {
        "date": "2025-01-15",
        "paymentsRouted": 5,
        "valueRouted": 151559,
        "revenue": 4896.96,
        "onchainCosts": 407.12,
        "offchainCost": 126.86,
        "offchainCostPpm": 837.0,
        "percentCosts": 0.109,
        "profit": 4362.98,
        "profitPpm": 28787.35
    },
    {
        "date": "2025-01-16",
        "paymentsRouted": 16,
        "valueRouted": 164953,
        "revenue": 6784.06,
        "onchainCosts": 461.9,
        "offchainCost": 170.04,
        "offchainCostPpm": 1030.81,
        "percentCosts": 0.0931,
        "profit": 6152.13,
        "profitPpm": 37296.24
    },
    {
        "date": "2025-01-17",
        "paymentsRouted": 17,
        "valueRouted": 100294,
        "revenue": 1420.73,
        "onchainCosts": 402.64,
        "offchainCost": 131.88,
        "offchainCostPpm": 1314.93,
        "percentCosts": 0.3762,
        "profit": 886.21,
        "profitPpm": 8836.1
    },
    {
        "date": "2025-01-18",
        "paymentsRouted": 16,
        "valueRouted": 171829,
        "revenue": 7792.27,
        "onchainCosts": 410.88,
        "offchainCost": 233.71,
        "offchainCostPpm": 1360.11,
        "percentCosts": 0.0827,
        "profit": 7147.69,
        "profitPpm": 41597.67
    },
    {
        "date": "2025-01-19",
        "paymentsRouted": 10,
        "valueRouted": 194704,
        "revenue": 4603.86,
        "onchainCosts": 166.39,
        "offchainCost": 83.59,
        "offchainCostPpm": 429.3,
        "percentCosts": 0.0543,
        "profit": 4353.87,
        "profitPpm": 22361.5
    },
    {
        "date": "2025-01-20",
        "paymentsRouted": 3,
        "valueRouted": 44045,
        "revenue": 635.71,
        "onchainCosts": 348.28,
        "offchainCost": 184.91,
        "offchainCostPpm": 4198.32,
        "percentCosts": 0.8387,
        "profit": 102.51,
        "profitPpm": 2327.45
    },
    {
        "date": "2025-01-21",
        "paymentsRouted": 12,
        "valueRouted": 47517,
        "revenue": 928.39,
        "onchainCosts": 79.23,
        "offchainCost": 68.32,
        "offchainCostPpm": 1437.88,
        "percentCosts": 0.1589,
        "profit": 780.84,
        "profitPpm": 16432.91
    },
    {
        "date": "2025-01-22",
        "paymentsRouted": 3,
        "valueRouted": 189323,
        "revenue": 3974.6,
        "onchainCosts": 214.78,
        "offchainCost": 47.4,
        "offchainCostPpm": 250.35,
        "percentCosts": 0.066,
        "profit": 3712.42,
        "profitPpm": 19608.95
    },
    {
        "date": "2025-01-23",
        "paymentsRouted": 1,
        "valueRouted": 120919,
        "revenue": 4429.03,
        "onchainCosts": 370.77,
        "offchainCost": 296.43,
        "offchainCostPpm": 2451.46,
        "percentCosts": 0.1506,
        "profit": 3761.83,
        "profitPpm": 31110.3
    },
    {
        "date": "2025-01-24",
        "paymentsRouted": 6,
        "valueRouted": 18812,
        "revenue": 552.78,
        "onchainCosts": 206.77,
        "offchainCost": 35.34,
        "offchainCostPpm": 1878.76,
        "percentCosts": 0.438,
        "profit": 310.66,
        "profitPpm": 16514.17
    }
]

const chartConfig = {
    revenue: { label: "Revenue (sats)", color: "hsl(var(--chart-1))", axis: "left" },
    offchainCost: { label: "Off-Chain Costs (sats)", color: "hsl(var(--chart-2))", axis: "left" },
    onchainCosts: { label: "On-Chain Costs (sats)", color: "hsl(var(--chart-3))", axis: "left" },
    profit: { label: "Profit (sats)", color: "hsl(var(--chart-4))", axis: "left" },
    valueRouted: { label: "Value Routed (sats)", color: "hsl(var(--chart-5))", axis: "left" },
    offchainCostPpm: { label: "Off-Chain Costs (ppm)", color: "hsl(var(--chart-6))", axis: "right" },
    percentCosts: { label: "Percent Costs (%)", color: "hsl(var(--chart-1))", axis: "right" },
    profitPpm: { label: "Profit (ppm)", color: "hsl(var(--chart-2))", axis: "right" },
    paymentsRouted: { label: "Payments Routed (count)", color: "hsl(var(--chart-3))", axis: "right" },
} satisfies ChartConfig

export function ProfitabilityStatsChart() {

    const [timeRange, setTimeRange] = useState("180d")

    const filteredData = statsData.filter((data) => {
        const date = new Date(data.date)
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


    const aggregatedData = filteredData.reduce((acc, data, index, array) => {
        acc.offchainCost += data.offchainCost;
        acc.offchainCostPpm += data.offchainCostPpm
        acc.onchainCosts += data.onchainCosts;
        acc.percentCosts += data.percentCosts;
        acc.profit += data.profit;
        acc.profitPpm += data.profitPpm;
        acc.paymentsRouted += data.paymentsRouted;
        acc.valueRouted += data.valueRouted;
        acc.revenue += data.revenue;
        // Calculate the average of percentCosts on the last iteration
        if (index === array.length - 1) {
            return {
                ...acc,
                percentCosts: acc.percentCosts / array.length,
            };
        }
        return acc
    }, {
        offchainCost: 0,
        offchainCostPpm: 0,
        onchainCosts: 0,
        percentCosts: 0,
        profit: 0,
        profitPpm: 0,
        paymentsRouted: 0,
        valueRouted: 0,
        revenue: 0,
    });



    return (

        <>
            <Card className="mb-4">
                <CardHeader className="flex items-center gap-2 space-y-0 border-b py-5 sm:flex-row">
                    <div className="grid flex-1 gap-1 text-center sm:text-left">

                        <CardTitle>Profitability Stats</CardTitle>
                        <CardDescription>
                            Profitability Stats highlighted over various periods of time.
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
                        <LineChart accessibilityLayer data={filteredData} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>

                            <CartesianGrid vertical={false} />
                            <YAxis
                                yAxisId="left"
                                orientation="left"
                                tickLine={false}
                                axisLine={false}
                                tickMargin={0}
                                tickCount={10}
                                minTickGap={32}
                                label={{ value: 'On-Chain (sats)', angle: -90, position: "left", style: { textAnchor: 'middle' } }}
                                tickFormatter={formatNumber}
                            />
                            <YAxis
                                yAxisId="right"
                                orientation="right"
                                tickLine={false}
                                axisLine={false}
                                tickMargin={0}
                                tickCount={10}
                                minTickGap={32}
                                label={{ value: 'Revenue and Off-Chain Costs (sats)', angle: 90, position: "right", style: { textAnchor: 'middle' } }}
                                tickFormatter={formatNumber}
                            />


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

                            {Object.entries(chartConfig).map(([dataKey, { color, axis }]) => (
                                <Line
                                    key={dataKey}
                                    dataKey={dataKey}
                                    type="natural"
                                    yAxisId={axis}
                                    stroke={color}
                                    dot={false}
                                // dot={{
                                //     fill: color,
                                // }}
                                />
                            ))
                            }

                        </LineChart>
                    </ChartContainer>
                </CardContent>
                <CardFooter>
                    <div className="grid grid-cols-9 gap-2">
                        <Card>
                            <CardHeader>
                                Profit
                            </CardHeader>
                            <CardContent>
                                {aggregatedData.profit.toLocaleString()}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                Profit (ppm)
                            </CardHeader>
                            <CardContent>
                                {aggregatedData.profitPpm.toLocaleString()}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                Off-Chain Costs
                            </CardHeader>
                            <CardContent>
                                {aggregatedData.offchainCost.toLocaleString()}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                Off-Chain Costs (ppm)
                            </CardHeader>
                            <CardContent>
                                {aggregatedData.offchainCostPpm.toLocaleString()}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                On-Chain Costs
                            </CardHeader>
                            <CardContent>
                                {aggregatedData.onchainCosts.toLocaleString()}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                Percent Costs
                            </CardHeader>
                            <CardContent>
                                {(aggregatedData.percentCosts * 100).toFixed(2)}%
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                Payments Routed
                            </CardHeader>
                            <CardContent>
                                {aggregatedData.paymentsRouted.toLocaleString()}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                Value Routed
                            </CardHeader>
                            <CardContent>
                                {aggregatedData.valueRouted.toLocaleString()}
                            </CardContent>
                        </Card>
                        <Card>
                            <CardHeader>
                                Revenue
                            </CardHeader>
                            <CardContent>
                                {aggregatedData.revenue.toLocaleString()}
                            </CardContent>
                        </Card>

                    </div>
                </CardFooter>
            </Card>

        </>

    )
}


// export const ProfitabilityStats: React.FC = () => {
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
//                 {value.stats.toLocaleString()} sats ({value.ppm} ppm)
//             </span>
//         );
//     };

//     return (
//         <table>
//             <thead>
//                 <tr>
//                     <th>Line Item</th>
//                     <th>Description</th>
//                     <th>1 Day</th>
//                     <th>7 Day</th>
//                     <th>30 Day</th>
//                     <th>90 Day</th>
//                     <th>Lifetime</th>
//                 </tr>
//             </thead>
//             <tbody>
//                 {statsData.map((item) => (
//                     <tr key={item.lineItem}>
//                         <td>{item.lineItem}</td>
//                         <td>{item.description}</td>
//                         <td>{renderValue(item["1 Day"])}</td>
//                         <td>{renderValue(item["7 Day"])}</td>
//                         <td>{renderValue(item["30 Day"])}</td>
//                         <td>{renderValue(item["90 Day"])}</td>
//                         <td>{renderValue(item.Lifetime)}</td>
//                     </tr>
//                 ))}
//             </tbody>
//         </table>
//     );
// };
