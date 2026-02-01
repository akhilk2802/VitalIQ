import apiClient from './client'
import type { Provider, Connection } from '@/types'

export interface SyncParams {
  providers?: string[]
  days?: number
}

export interface SyncResult {
  sync_id: string
  started_at: string
  completed_at: string
  status: string
  providers: {
    provider: string
    status: string
    data_types: {
      data_type: string
      records_fetched: number
      records_normalized: number
      records_skipped: number
      records_failed: number
    }[]
    error?: string
  }[]
  total_records_synced: number
}

export interface SyncStatus {
  last_sync_at?: string
  sync_in_progress: boolean
  providers: Connection[]
}

export const integrationsApi = {
  getProviders: async (): Promise<{ providers: Provider[] }> => {
    const response = await apiClient.get('/integrations/providers')
    return response.data
  },

  getConnections: async (): Promise<{ connections: Connection[]; total: number }> => {
    const response = await apiClient.get('/integrations/connections')
    return response.data
  },

  connectProvider: async (provider: string, redirectUrl?: string): Promise<{ link_url: string; message: string }> => {
    const response = await apiClient.post(`/integrations/connect/${provider}`, {
      redirect_url: redirectUrl,
    })
    return response.data
  },

  disconnectProvider: async (connectionId: string): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.delete(`/integrations/connections/${connectionId}`)
    return response.data
  },

  triggerSync: async (params: SyncParams = {}): Promise<SyncResult> => {
    const response = await apiClient.post<SyncResult>('/integrations/sync', params)
    return response.data
  },

  getSyncStatus: async (): Promise<SyncStatus> => {
    const response = await apiClient.get<SyncStatus>('/integrations/sync/status')
    return response.data
  },
}
