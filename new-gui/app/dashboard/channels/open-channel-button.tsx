import { Button } from "@/components/ui/button"
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { OpenChannelForm } from "./open-channel-form"

export function OpenChannelButton() {
    return (
        <Dialog>
            <DialogTrigger asChild>
                <Button variant="default">Open Channel</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                    <DialogTitle>Open Channel</DialogTitle>
                    <DialogDescription>
                        Connect to a peer and open a channel. <br /> Use <a href="https://mempool.space/" className="text-primary">Mempool Space</a> to figure out what the On Chain transaction fee should be.
                    </DialogDescription>
                </DialogHeader>
                <OpenChannelForm />
            </DialogContent>
        </Dialog>
    )
}
