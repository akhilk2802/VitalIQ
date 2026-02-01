import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import apiClient from '@/api/client'
import {
  mealSchema,
  sleepSchema,
  exerciseSchema,
  vitalsSchema,
  type MealFormData,
  type SleepFormData,
  type ExerciseFormData,
  type VitalsFormData,
} from '@/lib/validators'
import { GlassCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ArrowLeft, Loader2, Utensils, Moon, Dumbbell, HeartPulse } from 'lucide-react'

type EntryType = 'meal' | 'sleep' | 'exercise' | 'vitals'

const entryConfig: Record<EntryType, { title: string; icon: React.ReactNode; color: string }> = {
  meal: { title: 'Add Meal', icon: <Utensils className="h-5 w-5" />, color: 'text-nutrition' },
  sleep: { title: 'Log Sleep', icon: <Moon className="h-5 w-5" />, color: 'text-sleep' },
  exercise: { title: 'Add Exercise', icon: <Dumbbell className="h-5 w-5" />, color: 'text-exercise' },
  vitals: { title: 'Log Vitals', icon: <HeartPulse className="h-5 w-5" />, color: 'text-heart' },
}

export function DataEntryPage() {
  const { type } = useParams<{ type: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const entryType = type as EntryType
  const config = entryConfig[entryType]

  if (!config) {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <p className="text-muted-foreground">Invalid entry type</p>
        <Button variant="link" onClick={() => navigate('/')}>
          Return to Dashboard
        </Button>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div className={config.color}>{config.icon}</div>
        <h1 className="text-2xl font-bold tracking-tight">{config.title}</h1>
      </div>

      {/* Form */}
      <GlassCard className="p-6">
        {entryType === 'meal' && <MealForm onSuccess={() => navigate('/')} />}
        {entryType === 'sleep' && <SleepForm onSuccess={() => navigate('/')} />}
        {entryType === 'exercise' && <ExerciseForm onSuccess={() => navigate('/')} />}
        {entryType === 'vitals' && <VitalsForm onSuccess={() => navigate('/')} />}
      </GlassCard>
    </div>
  )
}

function MealForm({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<MealFormData>({
    resolver: zodResolver(mealSchema),
  })

  const mutation = useMutation({
    mutationFn: (data: MealFormData) => apiClient.post('/nutrition', data),
    onSuccess: () => {
      toast.success('Meal added successfully')
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      onSuccess()
    },
    onError: () => {
      toast.error('Failed to add meal')
    },
  })

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="name">Meal Name *</Label>
        <Input id="name" placeholder="e.g., Chicken salad" {...register('name')} />
        {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="calories">Calories *</Label>
          <Input id="calories" type="number" placeholder="500" {...register('calories')} />
          {errors.calories && <p className="text-sm text-destructive">{errors.calories.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="protein">Protein (g)</Label>
          <Input id="protein" type="number" placeholder="30" {...register('protein')} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="carbs">Carbs (g)</Label>
          <Input id="carbs" type="number" placeholder="50" {...register('carbs')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="fats">Fats (g)</Label>
          <Input id="fats" type="number" placeholder="15" {...register('fats')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="sugar">Sugar (g)</Label>
          <Input id="sugar" type="number" placeholder="10" {...register('sugar')} />
        </div>
      </div>

      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Add Meal
      </Button>
    </form>
  )
}

function SleepForm({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<SleepFormData>({
    resolver: zodResolver(sleepSchema),
  })

  const mutation = useMutation({
    mutationFn: (data: SleepFormData) => apiClient.post('/sleep', data),
    onSuccess: () => {
      toast.success('Sleep logged successfully')
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      onSuccess()
    },
    onError: () => {
      toast.error('Failed to log sleep')
    },
  })

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="hours">Hours *</Label>
          <Input id="hours" type="number" step="0.5" placeholder="7.5" {...register('hours')} />
          {errors.hours && <p className="text-sm text-destructive">{errors.hours.message}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="quality">Quality (0-100)</Label>
          <Input id="quality" type="number" placeholder="85" {...register('quality')} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="bedtime">Bedtime</Label>
          <Input id="bedtime" type="time" {...register('bedtime')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="wake_time">Wake Time</Label>
          <Input id="wake_time" type="time" {...register('wake_time')} />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="date">Date</Label>
        <Input id="date" type="date" {...register('date')} />
      </div>

      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Log Sleep
      </Button>
    </form>
  )
}

function ExerciseForm({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ExerciseFormData>({
    resolver: zodResolver(exerciseSchema),
  })

  const mutation = useMutation({
    mutationFn: (data: ExerciseFormData) => apiClient.post('/exercise', data),
    onSuccess: () => {
      toast.success('Exercise added successfully')
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      onSuccess()
    },
    onError: () => {
      toast.error('Failed to add exercise')
    },
  })

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="activity_type">Activity Type *</Label>
          <Input id="activity_type" placeholder="e.g., Running" {...register('activity_type')} />
          {errors.activity_type && (
            <p className="text-sm text-destructive">{errors.activity_type.message}</p>
          )}
        </div>
        <div className="space-y-2">
          <Label htmlFor="duration_minutes">Duration (min) *</Label>
          <Input
            id="duration_minutes"
            type="number"
            placeholder="45"
            {...register('duration_minutes')}
          />
          {errors.duration_minutes && (
            <p className="text-sm text-destructive">{errors.duration_minutes.message}</p>
          )}
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="calories_burned">Calories Burned</Label>
          <Input id="calories_burned" type="number" placeholder="300" {...register('calories_burned')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="avg_heart_rate">Avg Heart Rate</Label>
          <Input id="avg_heart_rate" type="number" placeholder="140" {...register('avg_heart_rate')} />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="intensity">Intensity</Label>
        <select
          id="intensity"
          {...register('intensity')}
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
        >
          <option value="">Select intensity</option>
          <option value="low">Low</option>
          <option value="moderate">Moderate</option>
          <option value="high">High</option>
          <option value="vigorous">Vigorous</option>
        </select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="notes">Notes</Label>
        <Input id="notes" placeholder="How did it feel?" {...register('notes')} />
      </div>

      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Add Exercise
      </Button>
    </form>
  )
}

function VitalsForm({ onSuccess }: { onSuccess: () => void }) {
  const queryClient = useQueryClient()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<VitalsFormData>({
    resolver: zodResolver(vitalsSchema),
  })

  const mutation = useMutation({
    mutationFn: (data: VitalsFormData) => apiClient.post('/vitals', data),
    onSuccess: () => {
      toast.success('Vitals logged successfully')
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      onSuccess()
    },
    onError: () => {
      toast.error('Failed to log vitals')
    },
  })

  return (
    <form onSubmit={handleSubmit((data) => mutation.mutate(data))} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="resting_hr">Resting Heart Rate (bpm)</Label>
          <Input id="resting_hr" type="number" placeholder="65" {...register('resting_hr')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="hrv_ms">HRV (ms)</Label>
          <Input id="hrv_ms" type="number" placeholder="45" {...register('hrv_ms')} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="blood_pressure_systolic">BP Systolic (mmHg)</Label>
          <Input id="blood_pressure_systolic" type="number" placeholder="120" {...register('blood_pressure_systolic')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="blood_pressure_diastolic">BP Diastolic (mmHg)</Label>
          <Input id="blood_pressure_diastolic" type="number" placeholder="80" {...register('blood_pressure_diastolic')} />
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="space-y-2">
          <Label htmlFor="spo2">SpO2 (%)</Label>
          <Input id="spo2" type="number" placeholder="98" {...register('spo2')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="respiratory_rate">Respiratory Rate</Label>
          <Input id="respiratory_rate" type="number" placeholder="14" {...register('respiratory_rate')} />
        </div>
        <div className="space-y-2">
          <Label htmlFor="body_temp">Temperature (°F)</Label>
          <Input id="body_temp" type="number" step="0.1" placeholder="98.6" {...register('body_temp')} />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="date">Date</Label>
        <Input id="date" type="date" {...register('date')} />
      </div>

      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        Log Vitals
      </Button>
    </form>
  )
}
