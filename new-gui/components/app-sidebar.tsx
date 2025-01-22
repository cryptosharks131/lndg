"use client";

import * as React from "react";
import { BookOpen, Bot, Settings2, SquareTerminal, Zap } from "lucide-react";

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
      url: "/",
      icon: SquareTerminal,
      isActive: true,
      items: [
        {
          title: "Overview",
          url: "/",
        },
        {
          title: "Performance",
          url: "/performance",
        },
        {
          title: "Financials",
          url: "/financials",
        },
      ],
    },
    {
      title: "Channels and Peers",
      url: "/peers",
      icon: Bot,
      items: [
        {
          title: "Channel Closures",
          url: "/channel-closures",
        },
        {
          title: "Peers",
          url: "/peers",
        },
        {
          title: "Peer Events",
          url: "/peer-events",
        },
      ],
    },
    {
      title: "Financials",
      url: "/financials",
      icon: BookOpen,
      items: [
        {
          title: "Auto-Rate",
          url: "/auto-rate",
        },
        {
          title: "Fee Rates",
          url: "/fee-rates",
        },
        {
          title: "Trades",
          url: "/trades",
        },
        {
          title: "Key Sends",
          url: "/key-sends",
        },
        {
          title: "Rebalancing",
          url: "/rebalancing",
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
          url: "/towers",
        },
        {
          title: "Batching",
          url: "/batching",
        },
        {
          title: "Fee Logs",
          url: "/fee-logs",
        },
        {
          title: "Advanced Settings",
          url: "/advanced-settings",
        },
        {
          title: "Logs",
          url: "/logs",
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
