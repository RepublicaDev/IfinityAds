/**
 * Zustand Store - Estado global da aplicação
 */
import { create } from 'zustand'

export const useAppStore = create((set) => ({
  // UI State
  loading: false,
  error: null,
  success: null,

  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error, success: null }),
  setSuccess: (success) => set({ success, error: null }),
  clearMessages: () => set({ error: null, success: null }),

  // Análise de YouTube
  youtubeAnalysis: null,
  setYoutubeAnalysis: (analysis) => set({ youtubeAnalysis: analysis }),

  // Dados de Produto
  product: null,
  setProduct: (product) => set({ product }),

  // Job de Anúncio
  currentJobId: null,
  jobStatus: null,
  setCurrentJobId: (jobId) => set({ currentJobId: jobId, jobStatus: 'processing' }),
  setJobStatus: (status) => set({ jobStatus: status }),

  // Histórico
  analysisHistory: [],
  addToHistory: (item) => set((state) => ({
    analysisHistory: [item, ...state.analysisHistory].slice(0, 20),
  })),
}))

export default useAppStore
