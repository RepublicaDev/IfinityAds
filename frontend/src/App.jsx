import React, { useEffect } from 'react'
import { healthApi } from './services/api'
import { useAppStore } from './stores/appStore'
import ProductScraper from './features/ProductScraper'
import YouTubeAnalyzer from './features/YouTubeAnalyzer'
import './App.css'

function App() {
  const { error, success, clearMessages } = useAppStore()

  useEffect(() => {
    // Verifica saúde do backend na inicialização
    healthApi.check().catch(() => console.warn('Backend não disponível'))
  }, [])

  useEffect(() => {
    // Auto-limpa mensagens após 5 segundos
    if (error || success) {
      const timer = setTimeout(clearMessages, 5000)
      return () => clearTimeout(timer)
    }
  }, [error, success, clearMessages])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">InfinityAd AI 2.0</h1>
          <p className="text-gray-600 mt-2">Gerador inteligente de anúncios com IA</p>
        </div>
      </header>

      {/* Alerts */}
      {error && (
        <div
          role="alert"
          className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg"
          aria-live="polite"
        >
          <strong>Erro:</strong> {error}
        </div>
      )}

      {success && (
        <div
          role="alert"
          className="mx-4 mt-4 p-4 bg-green-50 border border-green-200 text-green-700 rounded-lg"
          aria-live="polite"
        >
          <strong>Sucesso:</strong> {success}
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ProductScraper />
          <YouTubeAnalyzer />
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-gray-600 text-sm">
            © 2026 InfinityAd. Todos os direitos reservados.
          </p>
        </div>
      </footer>
    </div>
  )
}

export default App
