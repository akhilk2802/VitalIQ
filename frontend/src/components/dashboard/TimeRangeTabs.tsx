import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { TIME_RANGES } from '@/lib/constants'

interface TimeRangeTabsProps {
  value: number
  onChange: (value: number) => void
}

export function TimeRangeTabs({ value, onChange }: TimeRangeTabsProps) {
  return (
    <Tabs
      value={String(value)}
      onValueChange={(val) => onChange(Number(val))}
      className="w-auto"
    >
      <TabsList className="bg-muted/50">
        {TIME_RANGES.map((range) => (
          <TabsTrigger key={range.value} value={String(range.value)} className="px-4">
            {range.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  )
}
