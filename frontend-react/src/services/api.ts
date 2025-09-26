import axios, { AxiosInstance, AxiosError } from 'axios'
import { ChatResponse, ClearConversationResponse, SystemStats, ApiError } from '@/types'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: '/api',
      timeout: 60000, // 增加到60秒
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const apiError: ApiError = {
          message: error.message || 'An error occurred',
          code: error.code,
          details: error.response?.data,
        }
        return Promise.reject(apiError)
      }
    )
  }

  async askQuestion(question: string): Promise<ChatResponse> {
    try {
      const response = await this.client.post('/ask_question', {
        question,
      })
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async clearConversation(): Promise<ClearConversationResponse> {
    try {
      const response = await this.client.post('/clear_conversation')
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async getSystemStats(): Promise<SystemStats> {
    try {
      const response = await this.client.get('/system_stats')
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  async healthCheck(): Promise<any> {
    try {
      const response = await this.client.get('/health')
      return response.data
    } catch (error) {
      throw this.handleError(error)
    }
  }

  private handleError(error: any): ApiError {
    if (error.response) {
      // Server responded with error status
      return {
        message: error.response.data?.message || 'Server error',
        code: error.response.status.toString(),
        details: error.response.data,
      }
    } else if (error.request) {
      // Request was made but no response received
      return {
        message: 'Network error - please check your connection',
        code: 'NETWORK_ERROR',
      }
    } else {
      // Something else happened
      return {
        message: error.message || 'An unexpected error occurred',
        code: 'UNKNOWN_ERROR',
      }
    }
  }
}

export const apiClient = new ApiClient()
export default apiClient
