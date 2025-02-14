export default function Loading() {
    return (
        <div className="p-4">
            <div className="animate-pulse space-y-4">
                <div className="h-8 w-48 bg-gray-200 rounded" />
                <div className="h-[400px] bg-gray-200 rounded" />
            </div>
        </div>
    );
}