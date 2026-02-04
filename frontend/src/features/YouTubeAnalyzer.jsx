/**
 * Feature: YouTube Analyzer
 * Component para analisar vídeos do YouTube
 */
import React, { useState } from 'react'
import { Input, Button, Card } from '../components'
import { youtubeApi } from '../services/api'
import { useAppStore } from '../stores/appStore'

const SentimentBadge = ({ sentiment }) => {
  const colors = {
    positive: 'bg-green-100 text-green-800',
    negative: 'bg-red-100 text-red-800',
    neutral: 'bg-gray-100 text-gray-800',
    mixed: 'bg-yellow-100 text-yellow-800',
  }

  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${colors[sentiment]}`}>
      {sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}
    </span>
  )
}

export function YouTubeAnalyzer() {
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [forceReanalysis, setForceReanalysis] = useState(false)
  const { loading, setLoading, setError, setSuccess, youtubeAnalysis, setYoutubeAnalysis } = useAppStore()

  const handleAnalyze = async () => {
    if (!youtubeUrl.trim()) {
      setError('URL do YouTube é obrigatória')
      return
    }

    setLoading(true)
    try {
      const response = await youtubeApi.analyze(youtubeUrl, forceReanalysis)
      setYoutubeAnalysis(response.data)
      setSuccess('Vídeo analisado com sucesso!')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao analisar vídeo')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="Analisar Vídeo YouTube" subtitle="Extraia insights com NLP avançado">
      <div className="space-y-4">
        <Input
          label="URL do Vídeo"
          placeholder="https://youtube.com/watch?v=..."
          value={youtubeUrl}
          onChange={(e) => setYoutubeUrl(e.target.value)}
          disabled={loading}
        />

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={forceReanalysis}
            onChange={(e) => setForceReanalysis(e.target.checked)}
            disabled={loading}
            className="w-4 h-4 rounded"
          />
          <span className="text-sm text-gray-700">Forçar nova análise</span>
        </label>

        <Button
          variant="primary"
          onClick={handleAnalyze}
          loading={loading}
          className="w-full"
        >
          Analisar Vídeo
        </Button>
      </div>

      {youtubeAnalysis && (
        <div className="mt-6 border-t pt-4 space-y-4">
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Sentimento Geral</h4>
            <div className="flex items-center gap-3">
              <SentimentBadge sentiment={youtubeAnalysis.overall_sentiment} />
              <span className="text-sm text-gray-600">
                Score: {youtubeAnalysis.sentiment_score.toFixed(2)} | Confiança: {(youtubeAnalysis.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {youtubeAnalysis.positive_aspects.length > 0 && (
            <div>
              <h5 className="font-medium text-gray-900 mb-2">✓ Aspectos Positivos</h5>
              <ul className="space-y-1">
                {youtubeAnalysis.positive_aspects.map((aspect, i) => (
                  <li key={i} className="text-sm text-gray-700">• {aspect}</li>
                ))}
              </ul>
            </div>
          )}

          {youtubeAnalysis.negative_aspects.length > 0 && (
            <div>
              <h5 className="font-medium text-gray-900 mb-2">✗ Aspectos Negativos</h5>
              <ul className="space-y-1">
                {youtubeAnalysis.negative_aspects.map((aspect, i) => (
                  <li key={i} className="text-sm text-gray-700">• {aspect}</li>
                ))}
              </ul>
            </div>
          )}

          {youtubeAnalysis.topics.length > 0 && (
            <div>
              <h5 className="font-medium text-gray-900 mb-2">Tópicos Identificados</h5>
              <div className="space-y-2">
                {youtubeAnalysis.topics.map((topic, i) => (
                  <div key={i} className="flex items-center justify-between text-sm">
                    <span className="text-gray-700">{topic.name}</span>
                    <SentimentBadge sentiment={topic.sentiment} />
                  </div>
                ))}
              </div>
            </div>
          )}

          {youtubeAnalysis.brands_mentioned.length > 0 && (
            <div>
              <h5 className="font-medium text-gray-900 mb-2">Marcas Mencionadas</h5>
              <div className="flex flex-wrap gap-2">
                {youtubeAnalysis.brands_mentioned.map((brand, i) => (
                  <span key={i} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-sm">
                    {brand}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  )
}

export default YouTubeAnalyzer
