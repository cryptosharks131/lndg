
'use client'

import { Button } from "@/components/ui/button"
import { DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { openChannel } from "@/lib/channel-actions"
import { useActionState } from "react"
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, CheckCircle2 } from "lucide-react"


export function OpenChannelForm() {
    const [state, action, pending] = useActionState(openChannel, undefined)

    return (

        <form action={action}>

            <div className="grid gap-4 py-4">
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="publicKey" className="text-right">
                        Public Key
                    </Label>
                    <Input id="publicKey"
                        name="publicKey"
                        placeholder="031d4c994a977fe0b15a638f15b16faf0be0fc817066d8134ddb6784366920c1eb"
                        minLength={66}
                        maxLength={66}
                        required
                        className="col-span-3"
                        defaultValue={state?.inputs?.publicKey}
                    />
                </div>
                {state?.errors?.publicKey && (
                    <p className="text-sm text-red-500">{state.errors.publicKey}</p>
                )}
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="capacity" className="text-right">
                        Capacity
                    </Label>
                    <Input id="capacity"
                        name="capacity"
                        placeholder={(1000000).toLocaleString()}
                        className="col-span-2"
                        defaultValue={state?.inputs?.capacity}
                    />
                    <Label htmlFor="fee" className="text-right">
                        sat
                    </Label>
                    {state?.errors?.capacity && (
                        <p className="text-sm text-red-500 col-span-4">{state.errors.capacity}</p>
                    )}
                </div>
                <div className="grid grid-cols-4 items-center gap-4">
                    <Label htmlFor="fee" className="text-right col-span-2">
                        Onchain Transaction Fee
                    </Label>
                    <Input id="fee"
                        name="fee"
                        placeholder="2"
                        className="col-span-1"
                        defaultValue={state?.inputs?.fee}
                    />
                    <Label htmlFor="fee" className="text-right">
                        sat/vB
                    </Label>
                    {state?.errors?.fee && (
                        <p className="text-sm text-red-500 col-span-4">{state.errors.fee}</p>
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
            <DialogFooter>


                <Button aria-disabled={pending} type="submit">
                    {pending ? "Submitting..." : "Open Channel"}
                </Button>
            </DialogFooter>

        </form>
    )
}


