import { memo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { CHART_COLORS, TOOLTIP_STYLE } from "./constants";

type Point = { lap: number; [key: string]: number | null };

function BaseChart({ data, lines }: { data: Point[]; lines: { key: string; color: string }[] }) {
  return (
    <div className="chart-wrap">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data}>
          <CartesianGrid stroke={CHART_COLORS.grid} strokeDasharray="3 3" />
          <XAxis dataKey="lap" stroke={CHART_COLORS.axis} fontSize={11} />
          <YAxis domain={["auto", "auto"]} stroke={CHART_COLORS.axis} fontSize={11} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          {lines.map((line) => (
            <Line
              key={line.key}
              type="monotone"
              dataKey={line.key}
              stroke={line.color}
              strokeWidth={2}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export const LapTimesChart = memo(function LapTimesChart({
  data,
}: {
  data: { lap: number; time: number | null }[];
}) {
  return <BaseChart data={data} lines={[{ key: "time", color: CHART_COLORS.pace }]} />;
});

export const StressPaceChart = memo(function StressPaceChart({
  data,
}: {
  data: { lap: number; baseline: number | null; stress: number | null }[];
}) {
  return (
    <BaseChart
      data={data}
      lines={[
        { key: "baseline", color: CHART_COLORS.baseline },
        { key: "stress", color: CHART_COLORS.stress },
      ]}
    />
  );
});
