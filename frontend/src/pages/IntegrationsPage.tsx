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

const providerIcons: Record<string, string> = {
  fitbit: '⌚',
  garmin: '🏃',
  oura: '💍',
  google_fit: '🏋️',
  apple_health: '🍎',
  myfitnesspal: '🍽️',
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
      if (data.link_url) {
        window.open(data.link_url, '_blank')
      }
      toast.success(data.message)
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
                    <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-muted text-2xl">
                      {providerIcons[provider.id] || <Plug className="h-6 w-6" />}
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
