import AnalyticsFilterPane from "@/components/dashboard/analytics-filter-pane";



export default function ChannelsHeader({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <>

            <div className="border-b border-border pb-5 mb-5 sm:flex sm:items-center sm:justify-between">
                <h2 className="text-xl text-card-foreground">Profitability</h2>
                <div className="mt-3 flex sm:ml-4 sm:mt-0">
                    <div
                        className="inline-flex items-center "
                    >
                        <AnalyticsFilterPane />

                    </div>
                </div>
            </div >
            {children}
        </>
    )
}