import { cn } from '@/lib/utils'
import { GlassCard } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ResponsiveContainer } from 'recharts'
import type { ReactNode } from 'react'

interface ChartContainerProps {
  title?: string
  subtitle?: string
  children: ReactNode
  isLoading?: boolean
  isEmpty?: boolean
  emptyMessage?: string
  height?: number
  className?: string
  headerAction?: ReactNode
}

export function ChartContainer({
  title,
  subtitle,
  children,
  isLoading,
  isEmpty,
  emptyMessage = 'No data available',
  height = 300,
  className,
  headerAction,
}: ChartContainerProps) {
  if (isLoading) {
    return (
      <GlassCard className={cn('p-6', className)}>
        {title && (
          <div className="mb-4 flex items-start justify-between">
            <div>
              <Skeleton className="h-5 w-32" />
              {subtitle && <Skeleton className="mt-1 h-4 w-48" />}
            </div>
          </div>
        )}
        <Skeleton style={{ height }} className="w-full" />
      </GlassCard>
    )
  }

  if (isEmpty) {
    return (
      <GlassCard className={cn('p-6', className)}>
        {title && (
          <div className="mb-4">
            <h3 className="font-medium">{title}</h3>
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
        )}
        <div
          className="flex flex-col items-center justify-center text-center"
          style={{ height }}
        >
          <p className="text-sm text-muted-foreground">{emptyMessage}</p>
        </div>
      </GlassCard>
    )
  }

  return (
    <GlassCard className={cn('p-6', className)}>
      {(title || headerAction) && (
        <div className="mb-4 flex items-start justify-between">
          <div>
            {title && <h3 className="font-medium">{title}</h3>}
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
          {headerAction}
        </div>
      )}
      <ResponsiveContainer width="100%" height={height}>
        {children as React.ReactElement}
      </ResponsiveContainer>
    </GlassCard>
  )
}
