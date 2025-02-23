'use client'

import { Button } from "@/components/ui/button"
import { DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { updateOutboundFees } from "@/lib/channel-actions"
import { useActionState } from "react"
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, CheckCircle2 } from "lucide-react"

import { Channel } from "@/lib/definitions";

export function OutboundFeesForm({ channel }: { channel: Channel }) {

    const [state, action, pending] = useActionState(updateOutboundFees, {
        success: false,
        message: "",
        errors: {},
        inputs: { chanId: channel.chan_id, baseFee: channel.local_base_fee, feeRate: channel.local_fee_rate }, // Initialize inputs with default values
    });


    return (
        <form action={action}>

            <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                    <Input
                        id="chanId"
                        name="chanId"
                        type="hidden"
                        value={channel.chan_id}
                        readOnly
                    />
                </div>
                {state?.errors?.chanId && (
                    <p className="text-sm text-red-500">{state.errors.chanId}</p>
                )}
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="baseFee" className="text-right">
                        Base Fee
                    </Label>
                    <Input id="baseFee"
                        name="baseFee"
                        placeholder={(1000).toLocaleString()}
                        className="col-span-2"
                        defaultValue={state?.inputs?.baseFee}
                    />
                    <Label htmlFor="fee" className="text-right">
                        msat
                    </Label>
                    {state?.errors?.baseFee && (
                        <p className="text-sm text-red-500 col-span-4">{state.errors.baseFee}</p>
                    )}
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="feeRate" className="text-right">
                        Fee Rate
                    </Label>
                    <Input id="feeRate"
                        name="feeRate"
                        placeholder={(100).toLocaleString()}
                        className="col-span-2"
                        defaultValue={state?.inputs?.feeRate}
                    />
                    <Label htmlFor="fee" className="text-right">
                        ppm
                    </Label>
                    {state?.errors?.baseFee && (
                        <p className="text-sm text-red-500 col-span-4">{state.errors.feeRate}</p>
                    )}
                </div>

            </div>
            {state?.message && (
                <Alert variant={state.success ? "default" : "destructive"} className={state.success ? "border-primary mb-4" : "mb-b"}>
                    {state.success ? <CheckCircle2 className="h-4 w-4 stroke-primary" /> : <AlertCircle className="h-4 w-4" />}
                    <AlertTitle>{state.success ? "Success" : "Fail"}</AlertTitle>
                    <AlertDescription>{state.message}</AlertDescription>

                </Alert>

            )}



            <Button aria-disabled={pending} type="submit">
                {pending ? "Submitting..." : "Update Fees"}
            </Button>


        </form>
    )
}
