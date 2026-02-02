import {
  BarChart as RechartsBarChart,
  Bar,
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

interface BarChartProps {
  data: DataPoint[]
  dataKey?: string
  color?: MetricColor
  showGrid?: boolean
  showAxis?: boolean
  unit?: string
  radius?: number
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

export function BarChart({
  data,
  dataKey = 'value',
  color = 'exercise',
  showGrid = true,
  showAxis = true,
  unit,
  radius = 4,
}: BarChartProps) {
  const fillColor = METRIC_COLORS[color]

  return (
    <RechartsBarChart data={data}>
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
      <Bar
        dataKey={dataKey}
        fill={fillColor}
        radius={[radius, radius, 0, 0]}
        animationDuration={1000}
      />
    </RechartsBarChart>
  )
}
