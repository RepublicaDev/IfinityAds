import React, { useState } from 'react'

export default function AdGenerator(){
  const [productUrl, setProductUrl] = useState('')
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)

  async function start(){
    // In a real app, use Firebase client SDK to get token and call backend
    const token = 'Bearer <FIREBASE_ID_TOKEN>'
    const resp = await fetch('/api/v1/ads/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': token },
      body: JSON.stringify({ product_url: productUrl, youtube_url: youtubeUrl })
    })
    const data = await resp.json()
    setJobId(data.job_id)
    setStatus('queued')
    pollStatus(data.job_id)
  }

  async function pollStatus(id){
    const interval = setInterval(async ()=>{
      const r = await fetch(`/api/v1/ads/status/${id}`)
      const j = await r.json()
      setStatus(j.status)
      if(j.status === 'done' || j.status === 'failed'){
        setResult(j.result)
        clearInterval(interval)
      }
    }, 3000)
  }

  return (
    <div className="p-4 border rounded bg-white">
      <label className="block mb-2">Product URL</label>
      <input value={productUrl} onChange={e=>setProductUrl(e.target.value)} className="w-full p-2 border mb-3" />
      <label className="block mb-2">YouTube URL (optional)</label>
      <input value={youtubeUrl} onChange={e=>setYoutubeUrl(e.target.value)} className="w-full p-2 border mb-3" />
      <button onClick={start} className="bg-blue-600 text-white px-4 py-2 rounded">Gerar anúncio</button>

      <div className="mt-4">
        <strong>Status:</strong> {status}
        {result && <pre className="mt-2 bg-gray-100 p-2 rounded">{JSON.stringify(result, null, 2)}</pre>}
      </div>
    </div>
  )
}
