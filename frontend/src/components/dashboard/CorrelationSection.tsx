import { useState } from 'react'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'
import { GlassCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import {
  ChevronDown,
  GitBranch,
  ArrowRight,
  TrendingUp,
  TrendingDown,
  Lightbulb,
} from 'lucide-react'
import type { CorrelationSummary } from '@/types'

interface CorrelationSectionProps {
  correlations?: CorrelationSummary[]
  totalActionable?: number
  isLoading?: boolean
  className?: string
}

export function CorrelationSection({
  correlations = [],
  totalActionable = 0,
  isLoading,
  className,
}: CorrelationSectionProps) {
  const [isOpen, setIsOpen] = useState(true)

  if (isLoading) {
    return (
      <GlassCard className={cn('p-6', className)}>
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5" />
          <Skeleton className="h-5 w-32" />
        </div>
        <div className="mt-4 space-y-3">
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      </GlassCard>
    )
  }

  return (
    <GlassCard className={cn('p-6', className)}>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger className="flex w-full items-center justify-between">
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-recovery" />
            <h3 className="font-medium">Top Correlations</h3>
            {totalActionable > 0 && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-medium text-primary-foreground">
                {totalActionable}
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
          {correlations.length === 0 ? (
            <div className="flex flex-col items-center py-6 text-center">
              <GitBranch className="h-10 w-10 text-muted-foreground/50" />
              <p className="mt-3 text-sm font-medium">No correlations yet</p>
              <p className="text-xs text-muted-foreground">
                Track more data to discover patterns
              </p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                {correlations.map((correlation, index) => (
                  <CorrelationItem key={index} correlation={correlation} />
                ))}
              </div>

              <Button asChild variant="ghost" size="sm" className="mt-4 w-full">
                <Link to="/correlations">
                  Explore all correlations
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </>
          )}
        </CollapsibleContent>
      </Collapsible>
    </GlassCard>
  )
}

interface CorrelationItemProps {
  correlation: CorrelationSummary
}

function CorrelationItem({ correlation }: CorrelationItemProps) {
  const isPositive = correlation.correlation_value > 0
  const strengthColors: Record<string, string> = {
    weak: 'text-muted-foreground',
    moderate: 'text-nutrition',
    strong: 'text-primary',
    very_strong: 'text-exercise',
  }

  const formatMetricName = (name: string) =>
    name
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (c) => c.toUpperCase())

  return (
    <div className="rounded-lg border border-border bg-background/50 p-3">
      <div className="flex items-start gap-3">
        <div
          className={cn(
            'mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full',
            isPositive ? 'bg-exercise/10' : 'bg-heart/10'
          )}
        >
          {isPositive ? (
            <TrendingUp className="h-3.5 w-3.5 text-exercise" />
          ) : (
            <TrendingDown className="h-3.5 w-3.5 text-heart" />
          )}
        </div>

        <div className="flex-1">
          <div className="flex items-center gap-2 text-sm">
            <span className="font-medium">{formatMetricName(correlation.metric_a)}</span>
            <span className="text-muted-foreground">→</span>
            <span className="font-medium">{formatMetricName(correlation.metric_b)}</span>
          </div>

          <div className="mt-1 flex items-center gap-2">
            <span
              className={cn(
                'text-xs font-medium capitalize',
                strengthColors[correlation.strength] || 'text-muted-foreground'
              )}
            >
              {correlation.strength.replace('_', ' ')}
            </span>
            {correlation.lag_days && correlation.lag_days > 0 && (
              <span className="text-xs text-muted-foreground">
                • {correlation.lag_days}d lag
              </span>
            )}
            {correlation.causal_direction && correlation.causal_direction !== 'none' && (
              <span className="text-xs text-muted-foreground">• Causal</span>
            )}
          </div>

          {correlation.insight && (
            <div className="mt-2 flex items-start gap-1.5">
              <Lightbulb className="mt-0.5 h-3 w-3 shrink-0 text-nutrition" />
              <p className="text-xs text-muted-foreground line-clamp-2">
                {correlation.insight}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
