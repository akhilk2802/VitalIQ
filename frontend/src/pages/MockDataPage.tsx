import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { mockApi, type PersonaType } from '@/api/mock'
import { cn } from '@/lib/utils'
import { GlassCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DataViewer } from '@/components/dashboard'
import {
  Database,
  Play,
  Trash2,
  User,
  Activity,
  Moon,
  Cookie,
  Heart,
  Sparkles,
  Check,
  Info,
} from 'lucide-react'

const CURRENT_PERSONA_KEY = 'vitaliq_current_persona'

interface StoredPersonaInfo {
  id: string
  name: string
  generatedAt: string
  days: number
}

const personaIcons: Record<string, React.ReactNode> = {
  active_athlete: <Activity className="h-5 w-5 text-exercise" />,
  poor_sleeper: <Moon className="h-5 w-5 text-sleep" />,
  pre_diabetic: <Cookie className="h-5 w-5 text-glucose" />,
  stress_prone: <Heart className="h-5 w-5 text-heart" />,
  healthy_balanced: <Sparkles className="h-5 w-5 text-recovery" />,
}

const personaColors: Record<string, string> = {
  active_athlete: 'border-exercise/50 bg-exercise/5',
  poor_sleeper: 'border-sleep/50 bg-sleep/5',
  pre_diabetic: 'border-glucose/50 bg-glucose/5',
  stress_prone: 'border-heart/50 bg-heart/5',
  healthy_balanced: 'border-recovery/50 bg-recovery/5',
}

const personaBgColors: Record<string, string> = {
  active_athlete: 'bg-exercise/10',
  poor_sleeper: 'bg-sleep/10',
  pre_diabetic: 'bg-glucose/10',
  stress_prone: 'bg-heart/10',
  healthy_balanced: 'bg-recovery/10',
}

export function MockDataPage() {
  const [selectedPersona, setSelectedPersona] = useState<PersonaType>('healthy_balanced')
  const [days, setDays] = useState(150)
  const [clearExisting, setClearExisting] = useState(true)
  const [currentPersona, setCurrentPersona] = useState<StoredPersonaInfo | null>(null)
  const queryClient = useQueryClient()

  // Load stored persona info on mount
  useEffect(() => {
    const stored = localStorage.getItem(CURRENT_PERSONA_KEY)
    if (stored) {
      try {
        setCurrentPersona(JSON.parse(stored))
      } catch {
        localStorage.removeItem(CURRENT_PERSONA_KEY)
      }
    }
  }, [])

  const { data: personasData, isLoading: personasLoading } = useQuery({
    queryKey: ['mock', 'personas'],
    queryFn: () => mockApi.getPersonas(),
  })

  const generateMutation = useMutation({
    mutationFn: () =>
      mockApi.generateMockData({
        days,
        persona: selectedPersona,
        clear_existing: clearExisting,
        include_diabetes: true,
        include_heart: true,
      }),
    onSuccess: (result) => {
      toast.success(
        `Generated ${result.total_entries} entries for ${result.persona_name} persona`
      )
      
      // Store current persona info
      const personaInfo: StoredPersonaInfo = {
        id: selectedPersona,
        name: result.persona_name,
        generatedAt: new Date().toISOString(),
        days: days,
      }
      localStorage.setItem(CURRENT_PERSONA_KEY, JSON.stringify(personaInfo))
      setCurrentPersona(personaInfo)
      
      // Invalidate all queries to refresh dashboard and data viewer
      queryClient.invalidateQueries()
    },
    onError: () => {
      toast.error('Failed to generate mock data')
    },
  })

  const clearMutation = useMutation({
    mutationFn: () => mockApi.clearAllData(),
    onSuccess: (result) => {
      toast.success(`Cleared ${result.total_deleted} entries`)
      
      // Clear stored persona info
      localStorage.removeItem(CURRENT_PERSONA_KEY)
      setCurrentPersona(null)
      
      // Invalidate all queries to refresh dashboard and data viewer
      queryClient.invalidateQueries()
    },
    onError: () => {
      toast.error('Failed to clear data')
    },
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Mock Data Generator</h1>
        <p className="text-muted-foreground">
          Generate realistic health data for testing and demonstration
        </p>
      </div>

      {/* Current Persona Indicator */}
      {currentPersona && (
        <GlassCard className={cn('p-4', personaBgColors[currentPersona.id])}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn(
                'flex h-10 w-10 items-center justify-center rounded-lg',
                personaColors[currentPersona.id]
              )}>
                {personaIcons[currentPersona.id] || <User className="h-5 w-5" />}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-muted-foreground">Current Persona:</span>
                  <span className="font-semibold">{currentPersona.name}</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  {currentPersona.days} days of data • Generated {new Date(currentPersona.generatedAt).toLocaleDateString()}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Info className="h-4 w-4" />
              <span>Using mock data</span>
            </div>
          </div>
        </GlassCard>
      )}

      {/* Configuration */}
      <GlassCard className="p-6">
        <h2 className="font-medium mb-4">Configuration</h2>
        
        <div className="grid gap-6 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="days">Number of Days</Label>
            <Input
              id="days"
              type="number"
              min={7}
              max={365}
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            />
            <p className="text-xs text-muted-foreground">
              Generates data for the past {days} days
            </p>
          </div>

          <div className="space-y-2">
            <Label>Options</Label>
            <div className="flex items-center gap-2">
              <button
                type="button"
                role="checkbox"
                aria-checked={clearExisting}
                onClick={() => setClearExisting(!clearExisting)}
                className={cn(
                  'flex h-5 w-5 items-center justify-center rounded border transition-colors',
                  clearExisting
                    ? 'border-primary bg-primary'
                    : 'border-muted-foreground'
                )}
              >
                {clearExisting && <Check className="h-3 w-3 text-primary-foreground" />}
              </button>
              <span className="text-sm">Clear existing data first</span>
            </div>
          </div>
        </div>
      </GlassCard>

      {/* Personas */}
      <div>
        <h2 className="font-medium mb-4">Select Persona</h2>
        
        {personasLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {personasData?.personas?.map((persona) => (
              <button
                key={persona.id}
                onClick={() => setSelectedPersona(persona.id as PersonaType)}
                className={cn(
                  'rounded-xl border-2 p-4 text-left transition-all',
                  selectedPersona === persona.id
                    ? personaColors[persona.id]
                    : 'border-border bg-card hover:border-muted-foreground'
                )}
              >
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    {personaIcons[persona.id] || <User className="h-5 w-5" />}
                  </div>
                  <div>
                    <h3 className="font-medium">{persona.name}</h3>
                  </div>
                </div>
                <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
                  {persona.description}
                </p>
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button
          size="lg"
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          className="flex-1"
        >
          <Play className={cn('mr-2 h-4 w-4', generateMutation.isPending && 'animate-pulse')} />
          {generateMutation.isPending ? 'Generating...' : 'Generate Data'}
        </Button>
        
        <Button
          size="lg"
          variant="destructive"
          onClick={() => clearMutation.mutate()}
          disabled={clearMutation.isPending}
        >
          <Trash2 className="mr-2 h-4 w-4" />
          {clearMutation.isPending ? 'Clearing...' : 'Clear All Data'}
        </Button>
      </div>

      {/* Result */}
      {generateMutation.data && (
        <GlassCard className="p-6">
          <div className="flex items-center gap-2 mb-4">
            <Database className="h-5 w-5 text-exercise" />
            <h3 className="font-medium">Generation Results</h3>
          </div>
          
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Object.entries(generateMutation.data.entries_created).map(([key, value]) => (
              <div key={key} className="rounded-lg bg-muted p-3">
                <p className="text-2xl font-bold">{value}</p>
                <p className="text-xs text-muted-foreground capitalize">
                  {key.replace(/_/g, ' ')}
                </p>
              </div>
            ))}
          </div>

          {generateMutation.data.embedded_patterns.length > 0 && (
            <div className="mt-4 pt-4 border-t border-border">
              <p className="text-sm font-medium mb-2">Embedded Patterns</p>
              <ul className="space-y-1">
                {generateMutation.data.embedded_patterns.map((pattern, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <span>•</span>
                    <span>{pattern}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </GlassCard>
      )}

      {/* Data Viewer */}
      <DataViewer />
    </div>
  )
}
