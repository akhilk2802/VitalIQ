import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { integrationsApi } from '@/api'
import { cn, getRelativeTime } from '@/lib/utils'
import { GlassCard } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Plug,
  RefreshCw,
  Check,
  X,
  Clock,
  ExternalLink,
  Smartphone,
} from 'lucide-react'

// Brand logos as SVG components - authentic brand colors and recognizable icons
const ProviderLogos: Record<string, React.FC<{ className?: string }>> = {
  // Apple Health - Apple heart icon
  apple_health: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z" fill="#FF2D55"/>
    </svg>
  ),
  // Google Fit - Heart with G colors
  google_fit: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M16.5 3c-1.74 0-3.41.81-4.5 2.09C10.91 3.81 9.24 3 7.5 3 4.42 3 2 5.42 2 8.5c0 3.78 3.4 6.86 8.55 11.54L12 21.35l1.45-1.32C18.6 15.36 22 12.28 22 8.5 22 5.42 19.58 3 16.5 3z" fill="#EA4335"/>
      <path d="M12 21.35l-1.45-1.32c-2.57-2.33-4.64-4.32-6.15-5.98l7.6-4.39 7.6 4.39c-1.51 1.66-3.58 3.65-6.15 5.98L12 21.35z" fill="#4285F4"/>
      <path d="M12 9.66l-7.6 4.39C3.52 12.72 3 11.16 3 9.5 3 6.46 5.46 4 8.5 4c1.5 0 2.87.59 3.88 1.55L12 5.09l-.38.46C10.61 4.59 9.24 4 8.5 4 5.46 4 3 6.46 3 9.5c0 1.66.52 3.22 1.4 4.55L12 9.66z" fill="#FBBC05"/>
      <path d="M12 9.66l7.6 4.39c.88-1.33 1.4-2.89 1.4-4.55C21 6.46 18.54 4 15.5 4c-.74 0-1.61.59-2.62 1.55l.74.9c1.01-.96 1.88-1.45 1.88-1.45C18.54 4 21 6.46 21 9.5c0 1.66-.52 3.22-1.4 4.55L12 9.66z" fill="#34A853"/>
    </svg>
  ),
  // Fitbit - Iconic dots pattern
  fitbit: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="4" r="2" fill="#00B0B9"/>
      <circle cx="12" cy="12" r="2" fill="#00B0B9"/>
      <circle cx="12" cy="20" r="2" fill="#00B0B9"/>
      <circle cx="6" cy="8" r="1.5" fill="#00B0B9"/>
      <circle cx="6" cy="16" r="1.5" fill="#00B0B9"/>
      <circle cx="18" cy="8" r="1.5" fill="#00B0B9"/>
      <circle cx="18" cy="16" r="1.5" fill="#00B0B9"/>
    </svg>
  ),
  // Garmin - Triangle/Arrow design
  garmin: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M12 2L2 22h20L12 2z" fill="none" stroke="#007CC3" strokeWidth="2"/>
      <path d="M12 8l-5 10h10l-5-10z" fill="#007CC3"/>
    </svg>
  ),
  // Oura - Concentric rings
  oura: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="#B8B8B8" strokeWidth="2" fill="none"/>
      <circle cx="12" cy="12" r="6" stroke="#B8B8B8" strokeWidth="2" fill="none"/>
      <circle cx="12" cy="12" r="2" fill="#B8B8B8"/>
    </svg>
  ),
  // WHOOP - Strain icon
  whoop: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <rect x="3" y="8" width="18" height="8" rx="4" fill="#44D62C"/>
      <rect x="6" y="10" width="12" height="4" rx="2" fill="#1A1A1A"/>
      <circle cx="9" cy="12" r="1" fill="#44D62C"/>
      <circle cx="15" cy="12" r="1" fill="#44D62C"/>
    </svg>
  ),
  // Withings - Scale/Health icon
  withings: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" fill="#00B5AD"/>
      <path d="M12 6v6l4 2" stroke="white" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  ),
  // MyFitnessPal - Fork and knife
  myfitnesspal: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" fill="#0070C9"/>
      <path d="M8 6v5c0 1.1.9 2 2 2h1v7h2v-7h1c1.1 0 2-.9 2-2V6h-2v5h-1V6h-2v5h-1V6H8z" fill="white"/>
    </svg>
  ),
  // Strava - Iconic orange arrow
  strava: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <path d="M15.387 17.944l-2.089-4.116h-3.065L15.387 24l5.15-10.172h-3.066" fill="#FC4C02"/>
      <path d="M8.379 12.345l2.836 5.598h4.172L10.463 0l-7 13.828h4.169l2.747-1.483z" fill="#FC4C02"/>
    </svg>
  ),
  // Polar - Red circle/target
  polar: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" fill="none" stroke="#D30027" strokeWidth="2"/>
      <circle cx="12" cy="12" r="6" fill="none" stroke="#D30027" strokeWidth="2"/>
      <circle cx="12" cy="12" r="2" fill="#D30027"/>
    </svg>
  ),
}

// Brand colors for each provider
const providerColors: Record<string, string> = {
  apple_health: '#FF3B30',
  google_fit: '#4285F4',
  fitbit: '#00B0B9',
  garmin: '#007CC3',
  oura: '#FFFFFF',
  whoop: '#44D62C',
  withings: '#00A1E0',
  myfitnesspal: '#0070C9',
  strava: '#FC4C02',
  polar: '#D30027',
}

export function IntegrationsPage() {
  const queryClient = useQueryClient()

  const { data: providersData, isLoading: providersLoading } = useQuery({
    queryKey: ['integrations', 'providers'],
    queryFn: () => integrationsApi.getProviders(),
  })

  const { data: connectionsData, isLoading: connectionsLoading } = useQuery({
    queryKey: ['integrations', 'connections'],
    queryFn: () => integrationsApi.getConnections(),
  })

  const { data: syncStatus } = useQuery({
    queryKey: ['integrations', 'sync-status'],
    queryFn: () => integrationsApi.getSyncStatus(),
    refetchInterval: 5000, // Poll for sync status
  })

  const connectMutation = useMutation({
    mutationFn: (provider: string) =>
      integrationsApi.connectProvider(provider, window.location.href),
    onSuccess: (data) => {
      // In mock mode, connection is auto-completed - no URL to open
      if (data.link_url) {
        window.open(data.link_url, '_blank')
        toast.info('Opening authorization page...')
      } else {
        // Mock mode - connection was auto-completed
        toast.success(data.message || 'Provider connected successfully!')
      }
      queryClient.invalidateQueries({ queryKey: ['integrations'] })
    },
    onError: () => {
      toast.error('Failed to connect provider')
    },
  })

  const disconnectMutation = useMutation({
    mutationFn: (connectionId: string) =>
      integrationsApi.disconnectProvider(connectionId),
    onSuccess: () => {
      toast.success('Provider disconnected')
      queryClient.invalidateQueries({ queryKey: ['integrations'] })
    },
    onError: () => {
      toast.error('Failed to disconnect provider')
    },
  })

  const syncMutation = useMutation({
    mutationFn: () => integrationsApi.triggerSync({}),
    onSuccess: (result) => {
      toast.success(`Sync complete: ${result.total_records_synced} records synced`)
      queryClient.invalidateQueries({ queryKey: ['integrations'] })
    },
    onError: () => {
      toast.error('Failed to sync data')
    },
  })

  const isConnected = (provider: string) =>
    connectionsData?.connections?.some(
      (c) => c.provider === provider && c.status === 'connected'
    )

  const getConnection = (provider: string) =>
    connectionsData?.connections?.find((c) => c.provider === provider)

  const isLoading = providersLoading || connectionsLoading

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Integrations</h1>
          <p className="text-muted-foreground">
            Connect your health devices and apps
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => syncMutation.mutate()}
            disabled={syncMutation.isPending || syncStatus?.sync_in_progress}
          >
            <RefreshCw
              className={cn(
                'mr-2 h-4 w-4',
                (syncMutation.isPending || syncStatus?.sync_in_progress) && 'animate-spin'
              )}
            />
            Sync Now
          </Button>
        </div>
      </div>

      {/* Last sync info */}
      {syncStatus?.last_sync_at && (
        <GlassCard className="p-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Last synced {getRelativeTime(syncStatus.last_sync_at)}</span>
          </div>
        </GlassCard>
      )}

      {/* Providers grid */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48" />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {providersData?.providers?.map((provider) => {
            const connected = isConnected(provider.id)
            const connection = getConnection(provider.id)

            return (
              <GlassCard key={provider.id} className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div 
                      className="flex h-12 w-12 items-center justify-center rounded-xl"
                      style={{ 
                        backgroundColor: providerColors[provider.id] 
                          ? `${providerColors[provider.id]}20` 
                          : 'hsl(var(--muted))' 
                      }}
                    >
                      {ProviderLogos[provider.id] ? (
                        (() => {
                          const Logo = ProviderLogos[provider.id]
                          return <Logo className="h-7 w-7" />
                        })()
                      ) : (
                        <Plug className="h-6 w-6 text-muted-foreground" />
                      )}
                    </div>
                    <div>
                      <h3 className="font-medium">{provider.name}</h3>
                      <div className="flex items-center gap-1">
                        {connected ? (
                          <>
                            <Check className="h-3 w-3 text-exercise" />
                            <span className="text-xs text-exercise">Connected</span>
                          </>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            Not connected
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>

                <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
                  {provider.description}
                </p>

                <div className="mt-3 flex flex-wrap gap-1">
                  {provider.supported_data_types.map((type) => (
                    <span
                      key={type}
                      className="rounded-full bg-muted px-2 py-0.5 text-xs capitalize"
                    >
                      {type.replace('_', ' ')}
                    </span>
                  ))}
                </div>

                {provider.requires_mobile && (
                  <div className="mt-3 flex items-center gap-1 text-xs text-muted-foreground">
                    <Smartphone className="h-3 w-3" />
                    <span>Requires mobile app</span>
                  </div>
                )}

                <div className="mt-4 pt-4 border-t border-border">
                  {connected ? (
                    <div className="flex items-center justify-between">
                      {connection?.last_sync_at && (
                        <span className="text-xs text-muted-foreground">
                          Synced {getRelativeTime(connection.last_sync_at)}
                        </span>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => connection && disconnectMutation.mutate(connection.id)}
                        disabled={disconnectMutation.isPending}
                      >
                        <X className="mr-1 h-4 w-4" />
                        Disconnect
                      </Button>
                    </div>
                  ) : (
                    <Button
                      className="w-full"
                      onClick={() => connectMutation.mutate(provider.id)}
                      disabled={connectMutation.isPending || provider.requires_mobile}
                    >
                      {provider.requires_mobile ? (
                        'Coming Soon'
                      ) : (
                        <>
                          <ExternalLink className="mr-2 h-4 w-4" />
                          Connect
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </GlassCard>
            )
          })}
        </div>
      )}
    </div>
  )
}
