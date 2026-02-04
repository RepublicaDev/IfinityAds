/**
 * Feature: Product Scraper
 * Component para scrapear e exibir informações de produtos
 */
import React, { useState } from 'react'
import { Input, Button, Card } from '../components'
import { productApi } from '../services/api'
import { useAppStore } from '../stores/appStore'

export function ProductScraper() {
  const [productUrl, setProductUrl] = useState('')
  const [bypassCache, setBypassCache] = useState(false)
  const { loading, setLoading, setError, setSuccess, product, setProduct } = useAppStore()

  const handleScrape = async () => {
    if (!productUrl.trim()) {
      setError('URL do produto é obrigatória')
      return
    }

    setLoading(true)
    try {
      const response = await productApi.scrape(productUrl, bypassCache)
      setProduct(response.data)
      setSuccess('Produto scrapado com sucesso!')
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao scrapear produto')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card title="Scrapear Produto" subtitle="Insira a URL do produto para extrair informações">
      <div className="space-y-4">
        <Input
          label="URL do Produto"
          placeholder="https://shopee.com.br/product/..."
          value={productUrl}
          onChange={(e) => setProductUrl(e.target.value)}
          disabled={loading}
        />

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={bypassCache}
            onChange={(e) => setBypassCache(e.target.checked)}
            disabled={loading}
            className="w-4 h-4 rounded"
          />
          <span className="text-sm text-gray-700">Ignorar cache</span>
        </label>

        <Button
          variant="primary"
          onClick={handleScrape}
          loading={loading}
          className="w-full"
        >
          Scrapear Produto
        </Button>
      </div>

      {product && (
        <div className="mt-6 border-t pt-4">
          <h4 className="font-semibold text-gray-900 mb-3">Informações do Produto</h4>
          <div className="space-y-2">
            <p><strong>Nome:</strong> {product.name}</p>
            <p><strong>Preço:</strong> {product.price.currency} {product.price.amount}</p>
            <p><strong>Avaliação:</strong> {product.rating ? `${product.rating}/5 (${product.review_count} reviews)` : 'Sem avaliações'}</p>
            <p><strong>Marketplace:</strong> {product.marketplace}</p>
            {product.images.length > 0 && (
              <img
                src={product.images[0].url}
                alt={product.name}
                className="mt-3 w-full h-48 object-cover rounded-lg"
              />
            )}
          </div>
        </div>
      )}
    </Card>
  )
}

export default ProductScraper
