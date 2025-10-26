import { useState, useEffect } from "react";
import { predict, benchmarks } from "./lib/api";

const fmt = (n)=>Number(n||0).toLocaleString('en-CA',{style:'currency',currency:'CAD',maximumFractionDigits:0})

export default function App() {
  const [form, setForm] = useState({ province:'ON', collections:'', ebitda_or_sde:'', equipped_ops:'', sqft:'' })
  const [busy, setBusy] = useState(false)
  const [res, setRes] = useState(null)
  const [bm, setBm] = useState([])

  useEffect(()=>{(async()=>{ try{ const j=await benchmarks(); setBm(j.rows||[]) }catch(e){/*noop*/} })()},[])

  const set = (k)=>(e)=> setForm(s=>({...s,[k]:e.target.value}))

  const onSubmit = async (e)=>{
    e.preventDefault(); setBusy(true); setRes(null)
    try{
      // defaulting EBITDA and sqft when missing
      const p = {
        province: form.province || 'ON',
        collections: Number(form.collections||0),
        ebitda_or_sde: Number(form.ebitda_or_sde||0) || (Number(form.collections||0)*0.25),
        equipped_ops: Number(form.equipped_ops||0),
        sqft: Number(form.sqft||0) || (Number(form.equipped_ops||0)*290),
      }
      const j = await predict(p); setRes(j)
    }catch(err){ console.error(err) }
    finally{ setBusy(false) }
  }

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 flex flex-col items-center">
      <header className="w-full bg-white shadow-sm">
        <div className="max-w-5xl mx-auto px-6 py-4 flex justify-between items-center">
          <h1 className="text-2xl font-bold text-emerald-600">Rooted.ai</h1>
          <nav className="flex gap-6 text-sm text-gray-600">
            <a href="#benchmarks" className="hover:text-emerald-600">Benchmarks</a>
            <a href="#roadmap" className="hover:text-emerald-600">Roadmap</a>
          </nav>
        </div>
      </header>

      <section className="text-center mt-16">
        <h2 className="text-4xl font-extrabold text-gray-800">
          AI-Tuned <span className="text-emerald-600">Valuation</span> for Dental Practices
        </h2>
        <p className="text-gray-500 mt-3">Ontario-tuned model. Works across Canada.</p>
      </section>

      <form onSubmit={onSubmit} className="mt-10 bg-white shadow-lg rounded-2xl p-8 w-full max-w-xl">
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-semibold mb-1">Province</label>
            <select value={form.province} onChange={set('province')} className="w-full border rounded-lg p-3">
              {['ON','BC','AB','SK','MB','NB','NS','NL','PE','YT','NT','NU'].map(p=> <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Annual Collections (CAD)</label>
            <input type="number" value={form.collections} onChange={set('collections')} className="w-full border rounded-lg p-3" placeholder="e.g. 1,800,000"/>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">EBITDA / SDE (CAD) — optional</label>
            <input type="number" value={form.ebitda_or_sde} onChange={set('ebitda_or_sde')} className="w-full border rounded-lg p-3" placeholder="e.g. 400,000"/>
            <p className="text-xs text-gray-500 mt-1">If unknown, we’ll assume ~25% of revenue.</p>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Equipped Operatories</label>
            <input type="number" value={form.equipped_ops} onChange={set('equipped_ops')} className="w-full border rounded-lg p-3" placeholder="e.g. 6"/>
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Square Footage</label>
            <input type="number" value={form.sqft} onChange={set('sqft')} className="w-full border rounded-lg p-3" placeholder="e.g. 1900"/>
            <p className="text-xs text-gray-500 mt-1">If unknown, ≈ operatories × 290 sq ft.</p>
          </div>
        </div>
        <button className="mt-6 w-full md:w-auto px-5 py-3 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-semibold" disabled={busy}>
          {busy ? 'Calculating…' : 'See Your Practice Value'}
        </button>
      </form>

      {res && (
        <div className="mt-6 bg-emerald-50 border border-emerald-200 px-6 py-5 rounded-xl w-full max-w-xl">
          <div className="text-sm text-emerald-700 mb-1">Estimated valuation</div>
          <div className="text-3xl font-extrabold text-emerald-700">{fmt(res.estimate)}</div>
          <div className="mt-2 grid md:grid-cols-2 gap-3">
            <div className="rounded-lg p-4 border border-emerald-200 bg-white">
              <div className="text-xs text-gray-500 mb-1">68% range</div>
              <div className="text-lg font-bold">{fmt(res.range_68[0])} – {fmt(res.range_68[1])}</div>
            </div>
            <div className="rounded-lg p-4 border border-emerald-200 bg-white">
              <div className="text-xs text-gray-500 mb-1">95% range</div>
              <div className="text-lg font-bold">{fmt(res.range_95[0])} – {fmt(res.range_95[1])}</div>
            </div>
          </div>
        </div>
      )}

      <section id="benchmarks" className="mt-16 max-w-5xl px-6">
        <h3 className="text-2xl font-bold mb-3">Canadian Benchmarks</h3>
        <div className="overflow-auto rounded-xl border bg-white">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left p-3">Province</th>
                <th className="text-left p-3">Avg Collections</th>
                <th className="text-left p-3">EBITDA Margin</th>
                <th className="text-left p-3">EBITDA Multiple</th>
                <th className="text-left p-3">Ops (mean)</th>
                <th className="text-left p-3">Sqft/Op (mean)</th>
              </tr>
            </thead>
            <tbody>
              {bm.map(r=>(
                <tr key={r.province} className="border-t">
                  <td className="p-3 font-semibold">{r.province}</td>
                  <td className="p-3">{(r.avg_collections||0).toLocaleString('en-CA')}</td>
                  <td className="p-3">{Math.round((r.avg_ebitda_margin||0)*100)}%</td>
                  <td className="p-3">{r.ebitda_multiple}</td>
                  <td className="p-3">{r.ops_mean}</td>
                  <td className="p-3">{r.sqft_per_op_mean}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <footer id="roadmap" className="mt-16 mb-10 text-sm text-gray-500">
        © {new Date().getFullYear()} Rooted.ai — Benchmarks update nightly (demo CSV).
      </footer>
    </div>
  )
}
