import { useState } from 'react'
import { useDashboard } from '@/hooks/useDashboard'
import { ChartContainer, AreaChart, LineChart, BarChart } from '@/components/charts'
import { TimeRangeTabs, CorrelationOverview } from '@/components/dashboard'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export function TrendsPage() {
  const [timeRange, setTimeRange] = useState(30)
  const { data, isLoading } = useDashboard({ days: timeRange })

  // Transform daily summaries for charts
  // Backend returns: sleep.duration_hours, sleep.quality_score
  const sleepData = data?.daily_summaries?.map((d) => ({
    date: d.date,
    value: d.sleep?.duration_hours || 0,
    quality: d.sleep?.quality_score || 0,
  })) || []

  // Backend returns: nutrition.total_calories, total_protein_g, total_carbs_g, total_fats_g
  const nutritionData = data?.daily_summaries?.map((d) => ({
    date: d.date,
    value: d.nutrition?.total_calories || 0,
    protein: d.nutrition?.total_protein_g || 0,
    carbs: d.nutrition?.total_carbs_g || 0,
    fats: d.nutrition?.total_fats_g || 0,
  })) || []

  // Backend returns: exercises as array - need to sum duration_minutes and calories_burned
  const exerciseData = data?.daily_summaries?.map((d) => {
    const exercises = d.exercises || []
    return {
    date: d.date,
      value: exercises.reduce((sum, e) => sum + (e.duration_minutes || 0), 0),
      calories: exercises.reduce((sum, e) => sum + (e.calories_burned || 0), 0),
    }
  }) || []

  // Backend returns: vitals as array - take first entry or average
  const vitalsData = data?.daily_summaries?.map((d) => {
    const vitals = d.vitals || []
    const firstVital = vitals[0]
    return {
    date: d.date,
      heart_rate: firstVital?.resting_heart_rate || 0,
      hrv: firstVital?.hrv_ms || 0,
    }
  }) || []

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
      <Tabs defaultValue="compare" className="space-y-6">
        <TabsList>
          <TabsTrigger value="compare">Compare All</TabsTrigger>
          <TabsTrigger value="sleep">Sleep</TabsTrigger>
          <TabsTrigger value="nutrition">Nutrition</TabsTrigger>
          <TabsTrigger value="exercise">Exercise</TabsTrigger>
          <TabsTrigger value="vitals">Vitals</TabsTrigger>
        </TabsList>

        <TabsContent value="compare" className="space-y-6">
          <CorrelationOverview days={timeRange} />
        </TabsContent>

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
