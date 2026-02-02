import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { cn } from '@/lib/utils'
import { mockApi } from '@/api/mock'
import { GlassCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  ChevronDown,
  RefreshCw,
  Utensils,
  Moon,
  Dumbbell,
  HeartPulse,
  Scale,
  Activity,
  AlertTriangle,
  GitBranch,
  Database,
} from 'lucide-react'
import type { DataSummary, DataTypeSummary } from '@/types'

interface DataViewerProps {
  className?: string
}

const DATA_TYPE_CONFIG: Record<
  string,
  { label: string; icon: React.ElementType; color: string; columns: { key: string; label: string }[] }
> = {
  food_entries: {
    label: 'Food Entries',
    icon: Utensils,
    color: 'text-nutrition',
    columns: [
      { key: 'date', label: 'Date' },
      { key: 'food_name', label: 'Name' },
      { key: 'calories', label: 'Calories' },
      { key: 'protein_g', label: 'Protein (g)' },
    ],
  },
  sleep_entries: {
    label: 'Sleep Entries',
    icon: Moon,
    color: 'text-sleep',
    columns: [
      { key: 'date', label: 'Date' },
      { key: 'duration_hours', label: 'Duration (h)' },
      { key: 'quality_score', label: 'Quality' },
    ],
  },
  exercise_entries: {
    label: 'Exercise Entries',
    icon: Dumbbell,
    color: 'text-exercise',
    columns: [
      { key: 'date', label: 'Date' },
      { key: 'exercise_type', label: 'Type' },
      { key: 'duration_minutes', label: 'Duration (min)' },
      { key: 'calories_burned', label: 'Calories' },
    ],
  },
  vital_signs: {
    label: 'Vital Signs',
    icon: HeartPulse,
    color: 'text-heart',
    columns: [
      { key: 'date', label: 'Date' },
      { key: 'resting_heart_rate', label: 'Resting HR' },
      { key: 'hrv_ms', label: 'HRV (ms)' },
    ],
  },
  body_metrics: {
    label: 'Body Metrics',
    icon: Scale,
    color: 'text-body',
    columns: [
      { key: 'date', label: 'Date' },
      { key: 'weight_kg', label: 'Weight (kg)' },
      { key: 'body_fat_pct', label: 'Body Fat %' },
    ],
  },
  chronic_metrics: {
    label: 'Chronic Metrics',
    icon: Activity,
    color: 'text-glucose',
    columns: [
      { key: 'date', label: 'Date' },
      { key: 'time_of_day', label: 'Time of Day' },
      { key: 'blood_glucose_mgdl', label: 'Glucose (mg/dL)' },
    ],
  },
  anomalies: {
    label: 'Anomalies',
    icon: AlertTriangle,
    color: 'text-warning',
    columns: [
      { key: 'date', label: 'Date' },
      { key: 'metric_name', label: 'Metric' },
      { key: 'value', label: 'Value' },
      { key: 'severity', label: 'Severity' },
    ],
  },
  correlations: {
    label: 'Correlations',
    icon: GitBranch,
    color: 'text-recovery',
    columns: [
      { key: 'created_at', label: 'Date' },
      { key: 'metric_a', label: 'Metric A' },
      { key: 'metric_b', label: 'Metric B' },
      { key: 'strength', label: 'Strength' },
    ],
  },
}

export function DataViewer({ className }: DataViewerProps) {
  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['mock', 'data-summary'],
    queryFn: () => mockApi.getDataSummary(),
  })

  if (isLoading) {
    return (
      <GlassCard className={cn('p-6', className)}>
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5" />
            <Skeleton className="h-6 w-48" />
          </div>
          <Skeleton className="h-9 w-24" />
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      </GlassCard>
    )
  }

  if (!data || data.total_records === 0) {
    return (
      <GlassCard className={cn('p-6', className)}>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Database className={cn(
            'h-12 w-12 text-muted-foreground/50',
            isFetching && 'animate-pulse'
          )} />
          <p className="mt-4 font-medium">
            {isFetching ? 'Loading...' : 'No data yet'}
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            {isFetching 
              ? 'Fetching your health records...'
              : 'Generate mock data above to see your health records'
            }
          </p>
        </div>
      </GlassCard>
    )
  }

  return (
    <GlassCard className={cn('p-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Database className="h-5 w-5 text-primary" />
          <h2 className="text-lg font-semibold">
            Your Data{' '}
            <span className="text-muted-foreground font-normal">
              ({data.total_records.toLocaleString()} total records)
            </span>
          </h2>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          <RefreshCw className={cn('mr-2 h-4 w-4', isFetching && 'animate-spin')} />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-6">
        {Object.entries(DATA_TYPE_CONFIG).map(([key, config]) => {
          const summary = data[key as keyof DataSummary] as DataTypeSummary
          if (!summary) return null
          const Icon = config.icon
          return (
            <div
              key={key}
              className="rounded-lg border bg-background/50 p-4 transition-colors hover:bg-background/70"
            >
              <div className="flex items-center gap-2 mb-2">
                <Icon className={cn('h-4 w-4', config.color)} />
                <span className="text-sm font-medium">{config.label}</span>
              </div>
              <p className="text-2xl font-bold">{summary.count.toLocaleString()}</p>
              {summary.first_date && summary.last_date && (
                <p className="text-xs text-muted-foreground mt-1">
                  {formatDateRange(summary.first_date, summary.last_date)}
                </p>
              )}
            </div>
          )
        })}
      </div>

      {/* Expandable Tables */}
      <div className="space-y-3">
        {Object.entries(DATA_TYPE_CONFIG).map(([key, config]) => {
          const summary = data[key as keyof DataSummary] as DataTypeSummary
          if (!summary || summary.count === 0) return null
          return (
            <DataTypeTable
              key={key}
              dataKey={key}
              config={config}
              summary={summary}
            />
          )
        })}
      </div>
    </GlassCard>
  )
}

interface DataTypeTableProps {
  dataKey: string
  config: (typeof DATA_TYPE_CONFIG)[string]
  summary: DataTypeSummary
}

function DataTypeTable({ dataKey, config, summary }: DataTypeTableProps) {
  const [isOpen, setIsOpen] = useState(false)
  const Icon = config.icon

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex w-full items-center justify-between rounded-lg border bg-background/50 p-3 transition-colors hover:bg-background/70">
        <div className="flex items-center gap-2">
          <Icon className={cn('h-4 w-4', config.color)} />
          <span className="font-medium">{config.label}</span>
          <span className="text-sm text-muted-foreground">
            ({summary.count.toLocaleString()})
          </span>
        </div>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-muted-foreground transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </CollapsibleTrigger>

      <CollapsibleContent>
        <div className="mt-2 rounded-lg border bg-background/30 overflow-hidden">
          <ScrollArea className="max-h-[300px]">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-muted/80 backdrop-blur">
                <tr>
                  {config.columns.map((col) => (
                    <th
                      key={col.key}
                      className="px-4 py-2 text-left font-medium text-muted-foreground"
                    >
                      {col.label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {summary.recent.map((record, idx) => (
                  <tr
                    key={record.id as string || idx}
                    className="border-t border-border/50 hover:bg-muted/30"
                  >
                    {config.columns.map((col) => (
                      <td key={col.key} className="px-4 py-2">
                        {formatCellValue(record[col.key], col.key)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </ScrollArea>
          {summary.count > 10 && (
            <div className="border-t border-border/50 px-4 py-2 text-center text-xs text-muted-foreground">
              Showing most recent 10 of {summary.count.toLocaleString()} records
            </div>
          )}
        </div>
      </CollapsibleContent>
    </Collapsible>
  )
}

function formatDateRange(first: string, last: string): string {
  const firstDate = new Date(first)
  const lastDate = new Date(last)
  const formatter = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  
  if (firstDate.toDateString() === lastDate.toDateString()) {
    return formatter.format(firstDate)
  }
  
  return `${formatter.format(firstDate)} - ${formatter.format(lastDate)}`
}

function formatCellValue(value: unknown, key: string): string {
  if (value === null || value === undefined) return '-'
  
  // Format date fields
  if (key === 'date' || key === 'created_at') {
    const date = new Date(value as string)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  }
  
  // Format numbers
  if (typeof value === 'number') {
    return value.toLocaleString(undefined, { maximumFractionDigits: 1 })
  }
  
  // Format strings - capitalize and replace underscores
  if (typeof value === 'string') {
    return value.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
  }
  
  return String(value)
}
