"use client";

import * as React from "react";
import { BookOpen, Bot, ChartNoAxesCombined, Settings2, Zap } from "lucide-react";

import { NavMain } from "@/components/nav-main";
import { NavUser } from "@/components/nav-user";
import { TeamSwitcher } from "@/components/team-switcher";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar";

// This is sample data.
const data = {
  node: {
    name: "bob",
    publicKey:
      "03304f0af87b37bd02f3f9ac4a4940fd93b590f77fccb73d1e30d0e9380c893ea6",
  },
  teams: [
    {
      name: "LNDg",
      logo: Zap,
      plan: "LNDg Overview",
    },
  ],
  navMain: [
    {
      title: "Dashboard",
      url: "/dashboard",
      icon: ChartNoAxesCombined,
      isActive: true,
      items: [
        {
          title: "Overview",
          url: "/dashboard/",
        },
        {
          title: "Channel Performance",
          url: "/dashboard/performance",
        },
        {
          title: "Node Profitability",
          url: "/dashboard/profitability",
        },
      ]
    },
    {
      title: "Channels and Peers",
      url: "/dashboard/channels",
      icon: Bot,
      isActive: true,
      items: [
        {
          title: "Channels",
          url: "/dashboard/channels",
        },
        {
          title: "Channel Closures",
          url: "/dashboard/channel-closures",
        },
        {
          title: "Peers",
          url: "/dashboard/peers",
        },
        {
          title: "Peer Events",
          url: "/dashboard/peer-events",
        },
      ],
    },
    {
      title: "Financials",
      url: "/dashboard/financials",
      icon: BookOpen,
      items: [
        {
          title: "Auto-Rate",
          url: "/dashboard/auto-rate",
        },
        {
          title: "Fee Rates",
          url: "/dashboard/fee-rates",
        },
        {
          title: "Trades",
          url: "/dashboard/trades",
        },
        {
          title: "Key Sends",
          url: "/dashboard/key-sends",
        },
        {
          title: "Rebalancing",
          url: "/dashboard/rebalancing",
        },
      ],
    },
    {
      title: "Logs and Settings",
      url: "#",
      icon: Settings2,
      items: [
        {
          title: "Towers",
          url: "/dashboard/towers",
        },
        {
          title: "Batching",
          url: "/dashboard/batching",
        },
        {
          title: "Fee Logs",
          url: "/dashboard/fee-logs",
        },
        {
          title: "Advanced Settings",
          url: "/dashboard/advanced-settings",
        },
        {
          title: "Logs",
          url: "/dashboard/logs",
        },
      ],
    },
  ],
};

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <TeamSwitcher teams={data.teams} />
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser node={data.node} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
