import {
  LineChart as RechartsLineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  type TooltipProps,
} from 'recharts'
import { METRIC_COLORS } from '@/lib/constants'
import { formatDate } from '@/lib/utils'
import type { MetricColor } from '@/types'

interface DataPoint {
  date: string
  [key: string]: unknown
}

interface LineConfig {
  dataKey: string
  color: MetricColor
  name?: string
  dashed?: boolean
}

interface LineChartProps {
  data: DataPoint[]
  lines: LineConfig[]
  showGrid?: boolean
  showAxis?: boolean
  showLegend?: boolean
}

const CustomTooltip = ({
  active,
  payload,
  label,
}: TooltipProps<number, string>) => {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="rounded-lg border border-border bg-popover p-3 shadow-lg">
      <p className="mb-2 text-xs text-muted-foreground">{formatDate(label)}</p>
      {payload.map((entry, index) => (
        <div key={index} className="flex items-center gap-2 text-sm">
          <div
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: entry.color }}
          />
          <span className="text-muted-foreground">{entry.name}:</span>
          <span className="font-medium">{entry.value?.toFixed(1)}</span>
        </div>
      ))}
    </div>
  )
}

export function LineChart({
  data,
  lines,
  showGrid = true,
  showAxis = true,
  showLegend = false,
}: LineChartProps) {
  return (
    <RechartsLineChart data={data}>
      {showGrid && (
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="hsl(var(--border))"
          vertical={false}
        />
      )}
      {showAxis && (
        <>
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
            axisLine={{ stroke: 'hsl(var(--border))' }}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 12, fill: 'hsl(var(--muted-foreground))' }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
        </>
      )}
      <Tooltip content={<CustomTooltip />} />
      {showLegend && (
        <Legend
          wrapperStyle={{ fontSize: '12px', paddingTop: '10px' }}
        />
      )}
      {lines.map((line) => (
        <Line
          key={line.dataKey}
          type="monotone"
          dataKey={line.dataKey}
          name={line.name || line.dataKey}
          stroke={METRIC_COLORS[line.color]}
          strokeWidth={2}
          strokeDasharray={line.dashed ? '5 5' : undefined}
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
          animationDuration={1000}
        />
      ))}
    </RechartsLineChart>
  )
}
