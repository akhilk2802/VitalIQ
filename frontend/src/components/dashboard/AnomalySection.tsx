import { useState } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { getRelativeTime, capitalize } from '@/lib/utils'
import { SEVERITY_CONFIG, METRIC_COLORS } from '@/lib/constants'
import { GlassCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  Zap,
} from 'lucide-react'
import type { Anomaly } from '@/types'

interface AnomalySectionProps {
  anomalies?: Anomaly[]
  isLoading?: boolean
  onAcknowledge?: (id: string) => void
  className?: string
}

export function AnomalySection({
  anomalies = [],
  isLoading,
  onAcknowledge,
  className,
}: AnomalySectionProps) {
  const [isOpen, setIsOpen] = useState(true)
  const unacknowledged = anomalies.filter((a) => !a.is_acknowledged)

  if (isLoading) {
    return (
      <GlassCard className={cn('p-6', className)}>
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5" />
          <Skeleton className="h-5 w-32" />
        </div>
        <div className="mt-4 space-y-3">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </div>
      </GlassCard>
    )
  }

  return (
    <GlassCard className={cn('p-6', className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger className="flex w-full items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-nutrition" />
            <h3 className="font-medium">Anomalies</h3>
            {unacknowledged.length > 0 && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-heart px-1.5 text-xs font-medium text-white">
                {unacknowledged.length}
              </span>
            )}
          </div>
          <ChevronDown
            className={cn(
              'h-4 w-4 text-muted-foreground transition-transform',
              isOpen && 'rotate-180'
            )}
          />
        </CollapsibleTrigger>

        <CollapsibleContent className="mt-4">
          {anomalies.length === 0 ? (
            <div className="flex flex-col items-center py-6 text-center">
              <CheckCircle2 className="h-10 w-10 text-exercise" />
              <p className="mt-3 text-sm font-medium">All clear!</p>
              <p className="text-xs text-muted-foreground">
                No anomalies detected recently
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                {anomalies.slice(0, 5).map((anomaly) => (
                  <AnomalyItem
                    key={anomaly.id}
                    anomaly={anomaly}
                    onAcknowledge={onAcknowledge}
                  />
                ))}
              </div>

              {anomalies.length > 5 && (
                <Button asChild variant="ghost" size="sm" className="mt-4 w-full">
                  <Link to="/alerts">
                    View all {anomalies.length} anomalies
                    <ArrowRight className="ml-2 h-4 w-4" />
                  </Link>
                </Button>
              )}
            </>
          )}
        </CollapsibleContent>
      </Collapsible>
    </GlassCard>
  )
}

interface AnomalyItemProps {
  anomaly: Anomaly
  onAcknowledge?: (id: string) => void
}

function AnomalyItem({ anomaly, onAcknowledge }: AnomalyItemProps) {
  const severityConfig = SEVERITY_CONFIG[anomaly.severity]
  const metricName = anomaly.metric_name.replace(/_/g, ' ')

  return (
    <div
      className={cn(
        'rounded-lg border p-3 transition-colors',
        anomaly.is_acknowledged
          ? 'border-border bg-background/30'
          : 'border-border bg-background/50'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <Zap
              className="h-4 w-4"
              style={{ color: severityConfig.color }}
            />
            <span className="text-sm font-medium capitalize">{metricName}</span>
            <span
              className="rounded-full px-2 py-0.5 text-xs font-medium"
              style={{
                color: severityConfig.color,
                backgroundColor: severityConfig.bgColor,
              }}
            >
              {severityConfig.label}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
            {anomaly.explanation ||
              `Value of ${anomaly.value.toFixed(1)} deviates ${anomaly.deviation.toFixed(1)} from baseline (${anomaly.baseline_value.toFixed(1)})`}
          </p>
          <p className="mt-1 text-xs text-muted-foreground/70">
            {getRelativeTime(anomaly.detected_at)}
          </p>
        </div>

        {!anomaly.is_acknowledged && onAcknowledge && (
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0 text-xs"
            onClick={() => onAcknowledge(anomaly.id)}
          >
            Dismiss
          </Button>
        )}
      </div>
    </div>
  )
}
