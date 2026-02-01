import {
  AreaChart as RechartsAreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  type TooltipProps,
} from 'recharts'
import { METRIC_COLORS } from '@/lib/constants'
import { formatDate } from '@/lib/utils'
import type { MetricColor } from '@/types'

interface DataPoint {
  date: string
  value: number
  [key: string]: unknown
}

interface AreaChartProps {
  data: DataPoint[]
  dataKey?: string
  color?: MetricColor
  showGrid?: boolean
  showAxis?: boolean
  gradientOpacity?: number
  unit?: string
}

const CustomTooltip = ({
  active,
  payload,
  label,
  unit,
}: TooltipProps<number, string> & { unit?: string }) => {
  if (!active || !payload || !payload.length) return null

  return (
    <div className="rounded-lg border border-border bg-popover p-3 shadow-lg">
      <p className="text-xs text-muted-foreground">{formatDate(label)}</p>
      <p className="text-sm font-medium">
        {payload[0].value?.toFixed(1)} {unit}
      </p>
    </div>
  )
}

export function AreaChart({
  data,
  dataKey = 'value',
  color = 'sleep',
  showGrid = true,
  showAxis = true,
  gradientOpacity = 0.3,
  unit,
}: AreaChartProps) {
  const strokeColor = METRIC_COLORS[color]
  const gradientId = `gradient-${color}`

  return (
    <RechartsAreaChart data={data}>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="5%" stopColor={strokeColor} stopOpacity={gradientOpacity} />
          <stop offset="95%" stopColor={strokeColor} stopOpacity={0} />
        </linearGradient>
      </defs>
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
      <Tooltip content={<CustomTooltip unit={unit} />} />
      <Area
        type="monotone"
        dataKey={dataKey}
        stroke={strokeColor}
        strokeWidth={2}
        fill={`url(#${gradientId})`}
        animationDuration={1000}
      />
    </RechartsAreaChart>
  )
}
