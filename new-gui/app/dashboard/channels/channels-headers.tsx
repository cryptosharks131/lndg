import { OpenChannelButton } from "./open-channel-button";


export default function ChannelsHeader() {
    return (
        <div className="border-b border-border pb-5 mb-5 sm:flex sm:items-center sm:justify-between">
            <h2 className="text-xl text-primary">Channels</h2>
            <div className="mt-3 flex sm:ml-4 sm:mt-0">
                <div
                    className="inline-flex items-center "
                >
                    <OpenChannelButton />
                </div>
            </div>
        </div >
    )
}