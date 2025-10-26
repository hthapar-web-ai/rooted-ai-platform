const API_BASE = (import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000').replace(/\/$/,'')
export async function predict(payload){
  const r = await fetch(API_BASE + '/api/predict', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify(payload)
  })
  if(!r.ok) throw new Error('API error')
  return r.json()
}
export async function benchmarks(province){
  const url = new URL(API_BASE + '/api/benchmarks'); if(province) url.searchParams.set('province', province)
  const r = await fetch(url); if(!r.ok) throw new Error('API error')
  return r.json()
}
