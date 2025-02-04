import React from "react";
import { Rectangle, Layer } from "recharts";


export default function SankeyChartNode({
    x,
    y,
    width,
    height,
    index,
    payload,
    containerWidth,
}: {
    x: number,
    y: number,
    width: number,
    height: number,
    index: number,
    payload: { name: string, value: number },
    containerWidth: number
}) {
    const isOut = x + width + 6 > containerWidth;
    return (
        <Layer key={`CustomNode${index}`}>
            <Rectangle
                x={x}
                y={y}
                width={width}
                height={height}
                className={`fill-primary`}
            />
            <text
                textAnchor={isOut ? 'end' : 'start'}
                x={isOut ? x - 6 : x + width + 6}
                y={y + height / 2}
                className={`text-base fill-card-foreground`}
            >
                {payload.name}
            </text>
            <text
                textAnchor={isOut ? 'end' : 'start'}
                x={isOut ? x - 6 : x + width + 6}
                y={y + height / 2 + 13}
                className={`text-xs fill-card-foreground`}


            >
                {`${payload.value.toLocaleString()}`}
            </text>
        </Layer >
    );
};
