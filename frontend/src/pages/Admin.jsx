import { useState, useEffect, useCallback } from 'react'
import {
  Chart as ChartJS, RadialLinearScale, PointElement, LineElement, Filler,
  CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend,
} from 'chart.js'
import { Radar, Line, Doughnut, Bar } from 'react-chartjs-2'
import s from './Admin.module.css'

ChartJS.register(
  RadialLinearScale, PointElement, LineElement, Filler,
  CategoryScale, LinearScale, BarElement, ArcElement, Tooltip, Legend,
)

const API     = import.meta.env.VITE_API_URL ?? ''
const PW_KEY  = 'dot_admin_pw'
const DIMS    = ['Team', 'Legal', 'Product', 'Traction', 'Funding', 'Market', 'Branding']
const DIM_KEYS= ['team','legal','product','traction','funding','market','branding']
const STAGE_FR= { idea:'Idée','pre-seed':'Pré-seed', seed:'Seed','series-a':'Série A', growth:'Croissance', ideation:'Idéation' }
const PIE_COLORS = ['#2563eb','#7c3aed','#0891b2','#059669','#dc2626','#d97706','#db2777','#4f46e5']

function fmt(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleDateString('fr-FR') + ' ' + d.toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})
}
function scoreColor(v) {
  if (v >= 70) return '#4ade80'
  if (v >= 40) return '#facc15'
  return '#f87171'
}

// ── Chart options ─────────────────────────────────────────────────────────────

const radarOpts = {
  responsive: true,
  plugins: { legend: { display: false } },
  scales: {
    r: {
      min: 0, max: 100,
      ticks: { stepSize: 25, color: 'rgba(255,255,255,0.25)', font: { size: 9 }, backdropColor: 'transparent' },
      grid: { color: 'rgba(255,255,255,0.08)' },
      angleLines: { color: 'rgba(255,255,255,0.08)' },
      pointLabels: { color: 'rgba(255,255,255,0.75)', font: { size: 11, family: 'DM Sans' } },
    },
  },
}

const lineOpts = {
  responsive: true,
  plugins: { legend: { display: false }, tooltip: { mode: 'index' } },
  scales: {
    x: { ticks: { color: 'rgba(255,255,255,0.5)' }, grid: { color: 'rgba(255,255,255,0.06)' } },
    y: { ticks: { color: 'rgba(255,255,255,0.5)' }, grid: { color: 'rgba(255,255,255,0.06)' }, beginAtZero: true },
  },
}

const donutOpts = {
  responsive: true,
  cutout: '55%',
  plugins: {
    legend: { position: 'right', labels: { color: 'rgba(255,255,255,0.7)', font: { size: 11 }, padding: 12 } },
  },
}

const barOpts = {
  responsive: true,
  indexAxis: 'y',
  plugins: { legend: { display: false } },
  scales: {
    x: { min: 0, max: 100, ticks: { color: 'rgba(255,255,255,0.5)' }, grid: { color: 'rgba(255,255,255,0.06)' } },
    y: { ticks: { color: 'rgba(255,255,255,0.7)', font: { size: 11 } }, grid: { display: false } },
  },
}

// ── Login ─────────────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }) {
  const [pw, setPw]     = useState('')
  const [err, setErr]   = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault(); setBusy(true); setErr('')
    try {
      const r = await fetch(`${API}/api/admin/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw }),
      })
      if (!r.ok) { setErr('Mot de passe incorrect'); setBusy(false); return }
      onLogin(pw)
    } catch { setErr('Erreur réseau'); setBusy(false) }
  }

  return (
    <div className={s.loginWrap}>
      <div className={s.loginCard}>
        <div className={s.loginLogo}>🔵</div>
        <h1 className={s.loginTitle}>The Dot — Admin</h1>
        <p className={s.loginSub}>Tableau de bord back-office</p>
        <form onSubmit={submit} className={s.loginForm}>
          <input className={s.loginInput} type="password" placeholder="Mot de passe admin"
            value={pw} onChange={e => setPw(e.target.value)} autoFocus />
          {err && <p className={s.loginErr}>{err}</p>}
          <button className={s.loginBtn} disabled={busy || !pw}>
            {busy ? 'Vérification…' : 'Accéder →'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Overview tab ──────────────────────────────────────────────────────────────

function OverviewTab({ stats }) {
  if (!stats) return <div className={s.loading}>Chargement…</div>

  const radarData = {
    labels: DIMS,
    datasets: [{
      data: DIM_KEYS.map(k => stats.avg_scores?.[k] ?? 0),
      fill: true,
      backgroundColor: 'rgba(96,165,250,0.12)',
      borderColor: '#60a5fa',
      borderWidth: 2,
      pointBackgroundColor: '#93c5fd',
      pointRadius: 4,
    }],
  }

  const monthKeys   = Object.keys(stats.monthly_trend ?? {})
  const monthVals   = Object.values(stats.monthly_trend ?? {})
  const lineData = {
    labels: monthKeys,
    datasets: [{
      data: monthVals,
      borderColor: '#60a5fa',
      backgroundColor: 'rgba(96,165,250,0.15)',
      fill: true,
      tension: 0.35,
      pointBackgroundColor: '#93c5fd',
      pointRadius: 5,
    }],
  }

  const secKeys  = Object.keys(stats.by_sector ?? {})
  const secVals  = Object.values(stats.by_sector ?? {})
  const donutData = {
    labels: secKeys,
    datasets: [{ data: secVals, backgroundColor: PIE_COLORS, borderColor: '#060d1c', borderWidth: 2 }],
  }

  const progNames  = (stats.top_programs ?? []).map(p => p.name)
  const progScores = (stats.top_programs ?? []).map(p => p.avg_score)
  const barData = {
    labels: progNames,
    datasets: [{
      data: progScores,
      backgroundColor: progScores.map(v => v >= 70 ? '#2563eb' : v >= 45 ? '#7c3aed' : '#1e3a8a'),
      borderRadius: 4,
    }],
  }

  return (
    <div className={s.overviewWrap}>
      {/* KPIs */}
      <div className={s.kpiRow}>
        <div className={s.kpiCard}>
          <div className={s.kpiVal}>{stats.total}</div>
          <div className={s.kpiLabel}>Diagnostics</div>
        </div>
        <div className={s.kpiCard}>
          <div className={s.kpiVal} style={{ fontFamily: 'DM Mono, monospace', color: scoreColor(stats.global_avg) }}>
            {stats.global_avg}
          </div>
          <div className={s.kpiLabel}>Score moyen</div>
        </div>
        <div className={s.kpiCard}>
          <div className={s.kpiVal} style={{ fontSize: '1.5rem', fontFamily: 'DM Sans, sans-serif' }}>
            {stats.top_sector ? stats.top_sector.charAt(0).toUpperCase() + stats.top_sector.slice(1) : '—'}
          </div>
          <div className={s.kpiLabel}>Secteur dominant</div>
        </div>
        <div className={s.kpiCard}>
          <div className={s.kpiVal}>{stats.this_month}</div>
          <div className={s.kpiLabel}>Ce mois-ci</div>
        </div>
      </div>

      {/* Radar + Line */}
      <div className={s.chartsRow2}>
        <div className={s.chartBox}>
          <div className={s.chartTitle}>Maturité moyenne</div>
          {Object.keys(stats.avg_scores ?? {}).length > 0
            ? <Radar data={radarData} options={radarOpts} />
            : <div className={s.noData}>Pas encore de données</div>}
        </div>
        <div className={s.chartBox}>
          <div className={s.chartTitle}>Évolution mensuelle</div>
          {monthKeys.length > 0
            ? <Line data={lineData} options={lineOpts} />
            : <div className={s.noData}>Pas encore de données</div>}
        </div>
      </div>

      {/* Sector pie */}
      {secKeys.length > 0 && (
        <div className={s.chartBoxFull}>
          <div className={s.chartTitle}>Répartition par secteur</div>
          <div className={s.donutWrap}>
            <Doughnut data={donutData} options={donutOpts} />
          </div>
        </div>
      )}

      {/* Program bar */}
      {progNames.length > 0 && (
        <div className={s.chartBoxFull}>
          <div className={s.chartTitle}>Programmes — score moyen</div>
          <Bar data={barData} options={barOpts} />
        </div>
      )}
    </div>
  )
}

// ── Diagnostic detail panel ───────────────────────────────────────────────────

function DiagDetail({ sub, pw, onDelete }) {
  const scores = sub.spider_scores ?? {}
  const hasScores = Object.keys(scores).length > 0
  const miniRadarData = {
    labels: DIMS,
    datasets: [{
      data: DIM_KEYS.map(k => scores[k] ?? 0),
      fill: true,
      backgroundColor: 'rgba(96,165,250,0.12)',
      borderColor: '#60a5fa',
      borderWidth: 1.5,
      pointBackgroundColor: '#93c5fd',
      pointRadius: 3,
    }],
  }

  async function handleDelete() {
    if (!confirm(`Supprimer le diagnostic de "${sub.startup_name}" ? Cette action est irréversible.`)) return
    const r = await fetch(`${API}/api/admin/submissions/${sub.id}?pw=${encodeURIComponent(pw)}`, { method: 'DELETE' })
    if (r.ok) onDelete(sub.id)
  }

  const needs = Array.isArray(sub.needs) ? sub.needs : []

  return (
    <div className={s.detailPanel}>
      {hasScores && (
        <div className={s.detailRadar}>
          <Radar data={miniRadarData} options={{ ...radarOpts, maintainAspectRatio: true }} />
        </div>
      )}
      {needs.length > 0 && (
        <div className={s.detailNeeds}>
          <span className={s.detailLabel}>Besoins identifiés :</span>
          <div className={s.needsTags}>
            {needs.map(n => <span key={n} className={s.needsTag}>{n}</span>)}
          </div>
        </div>
      )}
      <div className={s.detailMeta}>
        <span>Statut juridique : <strong>{sub.legal_status || '—'}</strong></span>
        <span>Éligibles : <strong>{sub.eligible_count ?? '—'}</strong></span>
        <span>Programme #1 : <strong style={{color:'#93c5fd'}}>{sub.top_program || '—'}</strong></span>
      </div>
      <button className={s.deleteBtn} onClick={handleDelete}>🗑️ Supprimer ce diagnostic</button>
    </div>
  )
}

// ── Diagnostics tab ───────────────────────────────────────────────────────────

function DiagnosticsTab({ pw }) {
  const [rows, setRows]       = useState([])
  const [total, setTotal]     = useState(0)
  const [page, setPage]       = useState(0)
  const [search, setSearch]   = useState('')
  const [stage, setStage]     = useState('all')
  const [sector, setSector]   = useState('all')
  const [expanded, setExpanded] = useState(null)
  const [loading, setLoading] = useState(true)
  const [stages, setStages]   = useState([])
  const [sectors, setSectors] = useState([])
  const limit = 15

  const load = useCallback(async (p, sq, st, sc) => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        pw, limit, offset: p * limit,
        search: sq, stage: st, sector: sc,
      })
      const r = await fetch(`${API}/api/admin/submissions?${params}`)
      const d = await r.json()
      setRows(d.submissions ?? [])
      setTotal(d.total ?? 0)
      // Collect unique filter values from first load
      if (p === 0 && !sq && st === 'all' && sc === 'all') {
        const allStages  = [...new Set((d.submissions ?? []).map(x => x.effective_stage).filter(Boolean))]
        const allSectors = [...new Set((d.submissions ?? []).map(x => x.sector).filter(Boolean))]
        if (allStages.length)  setStages(allStages)
        if (allSectors.length) setSectors(allSectors)
      }
    } catch {}
    setLoading(false)
  }, [pw])

  useEffect(() => { setPage(0); load(0, search, stage, sector) }, [search, stage, sector, load])
  useEffect(() => { load(page, search, stage, sector) }, [page, load])

  const pages = Math.ceil(total / limit)

  function toggleExpand(id) {
    setExpanded(prev => prev === id ? null : id)
  }

  function handleDelete(id) {
    setRows(r => r.filter(x => x.id !== id))
    setTotal(t => t - 1)
    setExpanded(null)
  }

  return (
    <div className={s.diagTab}>
      {/* Filters */}
      <div className={s.filterRow}>
        <input className={s.filterInput} placeholder="🔍 Recherche par nom…"
          value={search} onChange={e => setSearch(e.target.value)} />
        <select className={s.filterSelect} value={stage} onChange={e => setStage(e.target.value)}>
          <option value="all">Tous les stades</option>
          {stages.map(st => <option key={st} value={st}>{STAGE_FR[st] ?? st}</option>)}
        </select>
        <select className={s.filterSelect} value={sector} onChange={e => setSector(e.target.value)}>
          <option value="all">Tous les secteurs</option>
          {sectors.map(sc => <option key={sc} value={sc}>{sc}</option>)}
        </select>
        <span className={s.filterCount}>{total} résultat{total !== 1 ? 's' : ''}</span>
      </div>

      {loading ? (
        <div className={s.loading}>Chargement…</div>
      ) : rows.length === 0 ? (
        <div className={s.noData}>Aucun diagnostic enregistré pour l'instant.</div>
      ) : (
        rows.map(row => {
          const avg = row.spider_scores
            ? Math.round(Object.values(row.spider_scores).reduce((a, b) => a + b, 0) / 7)
            : Math.round(row.top_score ?? 0)
          const isOpen = expanded === row.id
          return (
            <div key={row.id} className={s.diagCard}>
              <div className={s.diagRow}>
                <div className={s.diagInfo}>
                  <div className={s.diagName}>{row.startup_name || '—'}</div>
                  <div className={s.diagTags}>
                    <span className={s.diagTag}>{row.sector || '—'}</span>
                    <span className={s.diagTagBlue}>{STAGE_FR[row.effective_stage] ?? row.effective_stage}</span>
                  </div>
                </div>
                <div className={s.diagRight}>
                  <div className={s.diagScore} style={{ color: scoreColor(avg) }}>
                    {avg}<span className={s.diagScoreSub}>/100</span>
                  </div>
                  <div className={s.diagDate}>{fmt(row.timestamp)}</div>
                </div>
              </div>
              <div className={s.diagActions}>
                <button className={s.viewBtn} onClick={() => toggleExpand(row.id)}>
                  {isOpen ? '▲ Réduire' : '👁️ Détail'}
                </button>
              </div>
              {isOpen && <DiagDetail sub={row} pw={pw} onDelete={handleDelete} />}
            </div>
          )
        })
      )}

      {pages > 1 && (
        <div className={s.pagination}>
          <button onClick={() => setPage(p => Math.max(0, p-1))} disabled={page === 0}>←</button>
          <span>Page {page+1} / {pages}</span>
          <button onClick={() => setPage(p => Math.min(pages-1, p+1))} disabled={page >= pages-1}>→</button>
        </div>
      )}
    </div>
  )
}

// ── Programs tab ──────────────────────────────────────────────────────────────

function ProgramsTab({ pw }) {
  const [programs, setPrograms] = useState([])
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    fetch(`${API}/api/programs`)
      .then(r => r.json())
      .then(d => { setPrograms(Array.isArray(d) ? d : []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])

  if (loading) return <div className={s.loading}>Chargement…</div>

  return (
    <div className={s.progsTab}>
      <p className={s.progsNote}>
        📋 {programs.length} programmes dans le catalogue — lecture seule (modifiable via <code>resources.csv</code>)
      </p>
      {programs.map(p => (
        <div key={p.id} className={s.progCard}>
          <div className={s.progCardTop}>
            <div>
              <div className={s.progName}>{p.name}</div>
              <div className={s.progMeta}>
                <span className={s.progId}>{p.id}</span>
                <span className={s.progType}>{p.type}</span>
                <span className={s.progStages}>{p.stages}</span>
              </div>
            </div>
            {p.url && (
              <a href={p.url} target="_blank" rel="noreferrer" className={s.progLink}>↗ Voir</a>
            )}
          </div>
          <div className={s.progDesc}>{p.description}</div>
          {p.needs && (
            <div className={s.progNeeds}>
              {p.needs.split(',').slice(0,6).map(n => (
                <span key={n} className={s.needsTag}>{n.trim()}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Settings tab ─────────────────────────────────────────────────────────────

function SettingsTab({ pw }) {
  const [settings, setSettings] = useState(null)
  const [saved, setSaved]       = useState(false)
  const [err, setErr]           = useState('')

  useEffect(() => {
    fetch(`${API}/api/admin/settings?pw=${encodeURIComponent(pw)}`)
      .then(r => r.json())
      .then(d => setSettings(d))
      .catch(() => setErr('Impossible de charger les paramètres'))
  }, [pw])

  async function handleSave() {
    setSaved(false); setErr('')
    try {
      const r = await fetch(`${API}/api/admin/settings?pw=${encodeURIComponent(pw)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings),
      })
      if (!r.ok) { setErr('Erreur de sauvegarde'); return }
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch { setErr('Erreur réseau') }
  }

  async function handleReset() {
    try {
      const r = await fetch(`${API}/api/admin/settings?pw=${encodeURIComponent(pw)}`)
      const defaults = await r.json()
      // Reset to config defaults (just reload from server after clearing)
      await fetch(`${API}/api/admin/settings?pw=${encodeURIComponent(pw)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rule_weight: 0.6, semantic_weight: 0.4, llm_candidate_limit: 10, groq_timeout: 15 }),
      })
      setSettings({ rule_weight: 0.6, semantic_weight: 0.4, llm_candidate_limit: 10, groq_timeout: 15 })
      setSaved(true); setTimeout(() => setSaved(false), 3000)
    } catch { setErr('Erreur réseau') }
  }

  if (!settings) return <div className={s.loading}>{err || 'Chargement…'}</div>

  const total = (settings.rule_weight + settings.semantic_weight).toFixed(2)

  return (
    <div className={s.settingsTab}>
      <div className={s.settingsSection}>
        <h3 className={s.settingsTitle}>⚖️ Pondération du matching</h3>
        <div className={s.sliderRow}>
          <label className={s.sliderLabel}>
            Priorité aux critères métier
            <span className={s.sliderVal}>{settings.rule_weight.toFixed(2)}</span>
          </label>
          <input type="range" min="0" max="1" step="0.05"
            value={settings.rule_weight}
            onChange={e => setSettings(p => ({ ...p, rule_weight: parseFloat(e.target.value) }))}
            className={s.slider} />
          <p className={s.sliderHint}>Part des règles métier (stade, besoins, secteur) dans le score.</p>
        </div>
        <div className={s.sliderRow}>
          <label className={s.sliderLabel}>
            Priorité à la compréhension IA
            <span className={s.sliderVal}>{settings.semantic_weight.toFixed(2)}</span>
          </label>
          <input type="range" min="0" max="1" step="0.05"
            value={settings.semantic_weight}
            onChange={e => setSettings(p => ({ ...p, semantic_weight: parseFloat(e.target.value) }))}
            className={s.slider} />
          <p className={s.sliderHint}>Part de l'analyse sémantique IA dans le score.</p>
        </div>
        <p className={s.totalHint} style={{ color: Math.abs(parseFloat(total)-1) < 0.01 ? '#4ade80' : '#f59e0b' }}>
          Total : {total} (idéalement = 1.0)
        </p>
      </div>

      <div className={s.settingsSection}>
        <h3 className={s.settingsTitle}>🤖 Paramètres LLM</h3>
        <div className={s.settingsGrid}>
          <div className={s.sliderRow}>
            <label className={s.sliderLabel}>
              Programmes envoyés au LLM
              <span className={s.sliderVal}>{settings.llm_candidate_limit}</span>
            </label>
            <input type="range" min="3" max="20" step="1"
              value={settings.llm_candidate_limit}
              onChange={e => setSettings(p => ({ ...p, llm_candidate_limit: parseInt(e.target.value) }))}
              className={s.slider} />
            <p className={s.sliderHint}>Nombre de programmes pré-sélectionnés transmis à l'IA.</p>
          </div>
          <div className={s.sliderRow}>
            <label className={s.sliderLabel}>
              Délai Groq (secondes)
              <span className={s.sliderVal}>{settings.groq_timeout}</span>
            </label>
            <input type="range" min="5" max="60" step="1"
              value={settings.groq_timeout}
              onChange={e => setSettings(p => ({ ...p, groq_timeout: parseInt(e.target.value) }))}
              className={s.slider} />
            <p className={s.sliderHint}>Durée max d'attente Groq avant bascule sur fallback.</p>
          </div>
        </div>
      </div>

      {err && <p className={s.settingsErr}>{err}</p>}
      {saved && <p className={s.settingsOk}>✅ Paramètres enregistrés.</p>}

      <div className={s.settingsBtns}>
        <button className={s.saveBtn} onClick={handleSave}>💾 Enregistrer</button>
        <button className={s.resetBtn} onClick={handleReset}>🔄 Réinitialiser</button>
      </div>
    </div>
  )
}

// ── Dashboard shell ───────────────────────────────────────────────────────────

function Dashboard({ pw, onLogout }) {
  const [tab, setTab]   = useState('overview')
  const [stats, setStats] = useState(null)
  const [err, setErr]   = useState('')

  useEffect(() => {
    fetch(`${API}/api/admin/stats?pw=${encodeURIComponent(pw)}`)
      .then(async r => {
        const d = await r.json()
        if (!r.ok) { setErr(`Erreur : ${d.detail ?? r.status}`); return }
        setStats(d)
      })
      .catch(e => setErr(`Erreur réseau : ${e.message}`))
  }, [pw])

  const tabs = [
    { key: 'overview',    label: '📊 Vue d\'ensemble' },
    { key: 'diagnostics', label: '🗂️ Diagnostics' },
    { key: 'programs',    label: '📋 Programmes' },
    { key: 'settings',    label: '⚙️ Paramètres' },
  ]

  return (
    <div className={s.dashWrap}>
      <header className={s.dashHeader}>
        <div className={s.dashHeaderLeft}>
          <span className={s.dashLogo}>🔵</span>
          <div>
            <h1 className={s.dashTitle}>The Dot — Admin Dashboard</h1>
            <p className={s.dashSub}>Connecté · The Dot Resource Matcher v2.0</p>
          </div>
        </div>
        <div className={s.dashHeaderRight}>
          <a href="/" className={s.homeLink}>← Accueil</a>
          <button className={s.logoutBtn} onClick={onLogout}>Déconnexion</button>
        </div>
      </header>

      <nav className={s.tabNav}>
        {tabs.map(t => (
          <button key={t.key} className={`${s.tabBtn} ${tab === t.key ? s.tabActive : ''}`}
            onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </nav>

      <main className={s.dashMain}>
        {err && <div className={s.errBanner}>{err}</div>}
        {tab === 'overview'    && <OverviewTab stats={stats} />}
        {tab === 'diagnostics' && <DiagnosticsTab pw={pw} />}
        {tab === 'programs'    && <ProgramsTab pw={pw} />}
        {tab === 'settings'    && <SettingsTab pw={pw} />}
      </main>
    </div>
  )
}

// ── Root ──────────────────────────────────────────────────────────────────────

export default function Admin() {
  const [pw, setPw] = useState(() => sessionStorage.getItem(PW_KEY) ?? '')

  function handleLogin(p) { sessionStorage.setItem(PW_KEY, p); setPw(p) }
  function handleLogout()  { sessionStorage.removeItem(PW_KEY); setPw('') }

  return pw
    ? <Dashboard pw={pw} onLogout={handleLogout} />
    : <LoginScreen onLogin={handleLogin} />
}
