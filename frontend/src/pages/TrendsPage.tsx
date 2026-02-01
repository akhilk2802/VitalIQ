import { useState } from 'react'
import { useDashboard } from '@/hooks/useDashboard'
import { ChartContainer, AreaChart, LineChart, BarChart } from '@/components/charts'
import { TimeRangeTabs } from '@/components/dashboard'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function TrendsPage() {
  const [timeRange, setTimeRange] = useState(30)
  const { data, isLoading } = useDashboard({ days: timeRange })

  // Transform daily summaries for charts
  const sleepData = data?.daily_summaries?.map((d) => ({
    date: d.date,
    value: d.sleep?.hours || 0,
    quality: d.sleep?.quality || 0,
  })) || []

  const nutritionData = data?.daily_summaries?.map((d) => ({
    date: d.date,
    value: d.nutrition?.total_calories || 0,
    protein: d.nutrition?.protein || 0,
    carbs: d.nutrition?.carbs || 0,
    fats: d.nutrition?.fats || 0,
  })) || []

  const exerciseData = data?.daily_summaries?.map((d) => ({
    date: d.date,
    value: d.exercise?.total_minutes || 0,
    calories: d.exercise?.total_calories || 0,
  })) || []

  const vitalsData = data?.daily_summaries?.map((d) => ({
    date: d.date,
    heart_rate: d.vitals?.resting_hr || 0,
    hrv: d.vitals?.hrv_ms || 0,
  })) || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Trends</h1>
          <p className="text-muted-foreground">
            Visualize your health metrics over time
          </p>
        </div>
        <TimeRangeTabs value={timeRange} onChange={setTimeRange} />
      </div>

      {/* Metric tabs */}
      <Tabs defaultValue="sleep" className="space-y-6">
        <TabsList>
          <TabsTrigger value="sleep">Sleep</TabsTrigger>
          <TabsTrigger value="nutrition">Nutrition</TabsTrigger>
          <TabsTrigger value="exercise">Exercise</TabsTrigger>
          <TabsTrigger value="vitals">Vitals</TabsTrigger>
        </TabsList>

        <TabsContent value="sleep" className="space-y-6">
          <ChartContainer
            title="Sleep Duration"
            subtitle="Hours of sleep per night"
            isLoading={isLoading}
            isEmpty={sleepData.length === 0}
          >
            <AreaChart data={sleepData} color="sleep" unit="hours" />
          </ChartContainer>
          <ChartContainer
            title="Sleep Quality"
            subtitle="Quality score (0-100)"
            isLoading={isLoading}
            isEmpty={sleepData.length === 0}
          >
            <LineChart
              data={sleepData}
              lines={[{ dataKey: 'quality', color: 'sleep', name: 'Quality' }]}
            />
          </ChartContainer>
        </TabsContent>

        <TabsContent value="nutrition" className="space-y-6">
          <ChartContainer
            title="Daily Calories"
            subtitle="Total calorie intake"
            isLoading={isLoading}
            isEmpty={nutritionData.length === 0}
          >
            <BarChart data={nutritionData} color="nutrition" unit="kcal" />
          </ChartContainer>
          <ChartContainer
            title="Macronutrients"
            subtitle="Protein, carbs, and fats"
            isLoading={isLoading}
            isEmpty={nutritionData.length === 0}
          >
            <LineChart
              data={nutritionData}
              lines={[
                { dataKey: 'protein', color: 'heart', name: 'Protein' },
                { dataKey: 'carbs', color: 'nutrition', name: 'Carbs' },
                { dataKey: 'fats', color: 'glucose', name: 'Fats' },
              ]}
              showLegend
            />
          </ChartContainer>
        </TabsContent>

        <TabsContent value="exercise" className="space-y-6">
          <ChartContainer
            title="Exercise Duration"
            subtitle="Minutes of activity"
            isLoading={isLoading}
            isEmpty={exerciseData.length === 0}
          >
            <BarChart data={exerciseData} color="exercise" unit="min" />
          </ChartContainer>
          <ChartContainer
            title="Calories Burned"
            subtitle="During exercise sessions"
            isLoading={isLoading}
            isEmpty={exerciseData.length === 0}
          >
            <AreaChart
              data={exerciseData.map((d) => ({ ...d, value: d.calories }))}
              color="exercise"
              unit="kcal"
            />
          </ChartContainer>
        </TabsContent>

        <TabsContent value="vitals" className="space-y-6">
          <ChartContainer
            title="Heart Rate & HRV"
            subtitle="Resting heart rate and heart rate variability"
            isLoading={isLoading}
            isEmpty={vitalsData.length === 0}
          >
            <LineChart
              data={vitalsData}
              lines={[
                { dataKey: 'heart_rate', color: 'heart', name: 'Heart Rate (bpm)' },
                { dataKey: 'hrv', color: 'hrv', name: 'HRV (ms)' },
              ]}
              showLegend
            />
          </ChartContainer>
        </TabsContent>
      </Tabs>
    </div>
  )
}
