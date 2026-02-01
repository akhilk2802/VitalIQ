import apiClient from './client'
import type { Correlation, CorrelationSummary } from '@/types'

export interface CorrelationsParams {
  correlation_type?: string
  actionable_only?: boolean
  limit?: number
}

export interface DetectCorrelationsParams {
  days?: number
  include_granger?: boolean
  include_pearson?: boolean
  include_cross_correlation?: boolean
  include_mutual_info?: boolean
  include_population_comparison?: boolean
  min_confidence?: number
  generate_insights?: boolean
}

export interface CorrelationDetectionResult {
  total_correlations: number
  significant_correlations: number
  actionable_count: number
  new_correlations: number
  by_type: Record<string, number>
  by_strength: Record<string, number>
  top_findings: string[]
  correlations: Correlation[]
}

export interface CorrelationInsights {
  summary: string
  key_findings: string[]
  recommendations: string[]
  total_correlations: number
  actionable_count: number
  period_days: number
  generated_at: string
}

// Job status types
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface JobResponse {
  job_id: string
  status: JobStatus
  progress: number
  message: string
  result?: CorrelationDetectionResult
  error?: string
  created_at: string
  started_at?: string
  completed_at?: string
}

export interface DetectStartResponse {
  job_id: string
  status: string
  message: string
}

export const correlationsApi = {
  getCorrelations: async (params: CorrelationsParams = {}): Promise<Correlation[]> => {
    const response = await apiClient.get<Correlation[]>('/correlations', { params })
    return response.data
  },

  /**
   * Start correlation detection as a background job.
   * Returns immediately with a job_id.
   */
  startDetection: async (params: DetectCorrelationsParams = {}): Promise<DetectStartResponse> => {
    const response = await apiClient.post<DetectStartResponse>('/correlations/detect', params)
    return response.data
  },

  /**
   * Get the status of a correlation detection job.
   */
  getJobStatus: async (jobId: string): Promise<JobResponse> => {
    const response = await apiClient.get<JobResponse>(`/correlations/jobs/${jobId}`)
    return response.data
  },

  /**
   * Poll for job completion with progress updates.
   * Returns a promise that resolves when the job completes.
   */
  waitForCompletion: async (
    jobId: string,
    onProgress?: (job: JobResponse) => void,
    pollInterval: number = 2000
  ): Promise<JobResponse> => {
    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const job = await correlationsApi.getJobStatus(jobId)
          
          // Call progress callback
          if (onProgress) {
            onProgress(job)
          }
          
          if (job.status === 'completed') {
            resolve(job)
          } else if (job.status === 'failed') {
            reject(new Error(job.error || 'Job failed'))
          } else {
            // Still pending or running, poll again
            setTimeout(poll, pollInterval)
          }
        } catch (error) {
          reject(error)
        }
      }
      
      poll()
    })
  },

  /**
   * Convenience method: Start detection and wait for completion.
   */
  detectCorrelations: async (
    params: DetectCorrelationsParams = {},
    onProgress?: (job: JobResponse) => void
  ): Promise<CorrelationDetectionResult> => {
    // Start the job
    const startResponse = await correlationsApi.startDetection(params)
    
    // Wait for completion
    const completedJob = await correlationsApi.waitForCompletion(
      startResponse.job_id,
      onProgress
    )
    
    if (!completedJob.result) {
      throw new Error('Job completed but no result returned')
    }
    
    return completedJob.result
  },

  getTopCorrelations: async (limit: number = 5): Promise<{ correlations: CorrelationSummary[]; total_actionable: number }> => {
    const response = await apiClient.get('/correlations/top', {
      params: { limit },
    })
    return response.data
  },

  getCorrelationInsights: async (days: number = 30): Promise<CorrelationInsights> => {
    const response = await apiClient.get<CorrelationInsights>('/correlations/insights', {
      params: { days },
    })
    return response.data
  },

  getCorrelation: async (correlationId: string): Promise<Correlation> => {
    const response = await apiClient.get<Correlation>(`/correlations/${correlationId}`)
    return response.data
  },
}
