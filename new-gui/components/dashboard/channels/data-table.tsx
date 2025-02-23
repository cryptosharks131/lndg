"use client"

import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    useReactTable,
} from "@tanstack/react-table"

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table"
import { Channel, Forward } from "@/lib/definitions"
import { MenuItem, CustomContextMenu } from "@/components/custom-context-menu"
import { ArrowBigDownDash, ArrowBigUpDash, Bitcoin, Bot, Copy, Scale, TrendingUpDown, ZapOff } from "lucide-react";
import { closeChannel, ToastData } from "@/lib/channel-actions";
import { useToast } from "@/hooks/use-toast";

interface DataTableProps<TData, TValue> {
    columns: ColumnDef<TData, TValue>[]
    data: TData[],
}

export function ChannelsTable<TData, TValue>({
    columns,
    data,
}: DataTableProps<TData, TValue>) {
    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
    })

    // console.log(channels)
    const { toast } = useToast()

    const copyPublicKey = async (channelAlias: string, key: string) => {
        try {
            console.log(channelAlias, key)
            await navigator.clipboard.writeText(key);
            const toast: ToastData = {
                variant: "default",
                title: "Key Copied!",
                description: `Public Key ${key} for ${channelAlias} copied to clipboard`,
            };
            return { toast: toast }
        } catch (err) {
            console.log(err)
            const toast: ToastData = {
                variant: "destructive",
                title: "Uh oh! Something went wrong.",
                description: `Failed to copy public key for ${channelAlias}: ${String(err)}`,
            };
            return { toast: toast }


        }
    }


    const menuItems = (channel: Channel, toast: ReturnType<typeof useToast>["toast"]): MenuItem[] => [
        {
            label: "Copy Public Key",
            icon: <Copy size={14} />,
            onClick: async () => {
                const copy = await copyPublicKey(channel.alias, channel.remote_pubkey)
                toast({ ...copy.toast });
            }
            ,
        },
        { separator: true },
        {
            label: "Liquidity Management",
            subItems: [
                { icon: <Bot size={14} />, label: "Toggle AR", onClick: () => console.log("Increasing fees...") },
                { separator: true },
                { icon: <TrendingUpDown size={14} />, label: "Show Movement", onClick: () => console.log("Show Movement...") },
                { icon: <Scale size={14} />, label: "Rebalance", onClick: () => console.log("Rebalancing...") },
                { label: "Loop Out", onClick: () => console.log("Looping Out...") },
                { label: "Loop In", onClick: () => console.log("Looping In...") }
            ]
        },
        {
            label: "Fee Management",
            icon: <Bitcoin size={14} />,
            subItems: [
                { icon: <ArrowBigUpDash size={14} />, label: "Increase Fees", onClick: () => console.log("Increasing fees...") },
                { icon: <ArrowBigDownDash size={14} />, label: "Decrease Fees", onClick: () => console.log("Decreasing fees...") }
            ]
        },
        { separator: true },
        {
            icon: <ZapOff size={14} />, label: "Close Channel", onClick: async () => {
                const response = await closeChannel(channel, 1, false);
                toast({ ...response.toast });
            }
        },
        {
            icon: <ZapOff size={14} className="stroke-destructive" />, label: "Force Close", onClick: async () => {
                const response = await closeChannel(channel, 1, true);
                toast({ ...response.toast });
            }
        },
        { separator: true },
    ];

    return (
        <div className="rounded-md border">
            <Table>
                <TableHeader>
                    {table.getHeaderGroups().map((headerGroup) => (
                        <TableRow key={headerGroup.id}>
                            {headerGroup.headers.map((header) => {
                                return (
                                    <TableHead key={header.id}>
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(
                                                header.column.columnDef.header,
                                                header.getContext()
                                            )}
                                    </TableHead>
                                )
                            })}
                        </TableRow>
                    ))}
                </TableHeader>
                <TableBody>
                    {table.getRowModel().rows?.length ? (
                        table.getRowModel().rows.map((row) => (

                            <CustomContextMenu
                                key={row.id}
                                trigger={
                                    <TableRow
                                        key={row.id}
                                        data-state={row.getIsSelected() && "selected"}
                                    >
                                        {row.getVisibleCells().map((cell) => (
                                            <TableCell key={cell.id}>
                                                {flexRender(cell.column.columnDef.cell, cell.getContext())}
                                            </TableCell>
                                        ))}
                                    </TableRow>
                                }
                                menuItems={menuItems(row.original as Channel, toast)}>
                            </CustomContextMenu>

                        ))
                    ) : (
                        <TableRow>
                            <TableCell colSpan={columns.length} className="h-24 text-center">
                                No results.
                            </TableCell>
                        </TableRow>
                    )}
                </TableBody>
            </Table>
        </div>
    )
}
