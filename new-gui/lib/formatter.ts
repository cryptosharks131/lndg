// formatter function to properly display numbers
export function formatNumber(value: number) {
    return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}
