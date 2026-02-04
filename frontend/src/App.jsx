import React from 'react'
import AdGenerator from './components/AdGenerator'

export default function App(){
  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <header className="max-w-3xl mx-auto">
        <h1 className="text-3xl font-bold">InfinityAd AI</h1>
        <p className="text-sm text-gray-600">Gerador de anúncios (MVP)</p>
      </header>
      <main className="mt-6 max-w-3xl mx-auto">
        <AdGenerator />
      </main>
    </div>
  )
}
