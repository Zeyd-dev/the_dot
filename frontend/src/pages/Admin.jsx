import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import s from './Admin.module.css'

const API = import.meta.env.VITE_API_URL ?? ''
const PW_KEY = 'dot_admin_pw'

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmt(ts) {
  if (!ts) return '—'
  const d = new Date(ts)
  return d.toLocaleDateString('fr-FR') + ' ' + d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })
}

function scoreColor(v) {
  if (v >= 70) return '#22c55e'
  if (v >= 45) return '#f59e0b'
  return '#ef4444'
}

const STAGE_FR = {
  'idea': 'Idée', 'pre-seed': 'Pré-seed', 'seed': 'Seed',
  'series-a': 'Série A', 'growth': 'Croissance',
}

// ── Login screen ─────────────────────────────────────────────────────────────

function LoginScreen({ onLogin }) {
  const [pw, setPw]     = useState('')
  const [err, setErr]   = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setErr('')
    try {
      const r = await fetch(`${API}/api/admin/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: pw }),
      })
      if (!r.ok) { setErr('Mot de passe incorrect'); setBusy(false); return }
      onLogin(pw)
    } catch {
      setErr('Erreur réseau')
      setBusy(false)
    }
  }

  return (
    <div className={s.loginWrap}>
      <div className={s.loginCard}>
        <div className={s.loginLogo}>⚙️</div>
        <h1 className={s.loginTitle}>Administration</h1>
        <p className={s.loginSub}>The Dot Resource Matcher</p>
        <form onSubmit={submit} className={s.loginForm}>
          <input
            className={s.loginInput}
            type="password"
            placeholder="Mot de passe admin"
            value={pw}
            onChange={e => setPw(e.target.value)}
            autoFocus
          />
          {err && <p className={s.loginErr}>{err}</p>}
          <button className={s.loginBtn} disabled={busy || !pw}>
            {busy ? 'Vérification…' : 'Accéder au tableau de bord →'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Stat card ────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent }) {
  return (
    <div className={s.statCard}>
      <div className={s.statVal} style={accent ? { color: accent } : {}}>{value ?? '—'}</div>
      <div className={s.statLabel}>{label}</div>
      {sub && <div className={s.statSub}>{sub}</div>}
    </div>
  )
}

// ── Bar chart (horizontal) ───────────────────────────────────────────────────

function BarChart({ data, title }) {
  if (!data || !Object.keys(data).length) return null
  const max = Math.max(...Object.values(data))
  return (
    <div className={s.chartBox}>
      <h3 className={s.chartTitle}>{title}</h3>
      <div className={s.barList}>
        {Object.entries(data).map(([k, v]) => (
          <div key={k} className={s.barRow}>
            <span className={s.barLabel}>{STAGE_FR[k] ?? k}</span>
            <div className={s.barTrack}>
              <div className={s.barFill} style={{ width: `${Math.round((v / max) * 100)}%` }} />
            </div>
            <span className={s.barCount}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Submissions table ────────────────────────────────────────────────────────

function SubmissionsTable({ pw }) {
  const [rows, setRows]   = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage]   = useState(0)
  const [loading, setLoading] = useState(true)
  const limit = 20

  const load = useCallback(async (p) => {
    setLoading(true)
    try {
      const r = await fetch(`${API}/api/admin/submissions?pw=${encodeURIComponent(pw)}&limit=${limit}&offset=${p * limit}`)
      const d = await r.json()
      setRows(d.submissions ?? [])
      setTotal(d.total ?? 0)
    } catch { /* ignore */ }
    setLoading(false)
  }, [pw])

  useEffect(() => { load(page) }, [page, load])

  const pages = Math.ceil(total / limit)

  return (
    <div className={s.tableBox}>
      <div className={s.tableHeader}>
        <h3 className={s.chartTitle}>Diagnostics récents</h3>
        <span className={s.tableCount}>{total} au total</span>
      </div>
      {loading ? (
        <div className={s.tableLoading}>Chargement…</div>
      ) : rows.length === 0 ? (
        <div className={s.tableEmpty}>Aucun diagnostic enregistré pour l'instant.</div>
      ) : (
        <>
          <div className={s.tableScroll}>
            <table className={s.table}>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Startup</th>
                  <th>Secteur</th>
                  <th>Stade</th>
                  <th>Marché</th>
                  <th>Équipe</th>
                  <th>Programme #1</th>
                  <th>Score</th>
                  <th>Éligibles</th>
                  <th>Date</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(r => (
                  <tr key={r.id}>
                    <td className={s.tdMuted}>{r.id}</td>
                    <td className={s.tdBold}>{r.startup_name || '—'}</td>
                    <td>{r.sector || '—'}</td>
                    <td><span className={s.stagePill}>{STAGE_FR[r.effective_stage] ?? r.effective_stage}</span></td>
                    <td>{r.market_type || '—'}</td>
                    <td>{r.team_size ?? '—'}</td>
                    <td className={s.tdProgram}>{r.top_program || '—'}</td>
                    <td>
                      <span className={s.scoreChip} style={{ color: scoreColor(r.top_score) }}>
                        {Math.round(r.top_score)}
                      </span>
                    </td>
                    <td>{r.eligible_count ?? '—'}</td>
                    <td className={s.tdDate}>{fmt(r.timestamp)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {pages > 1 && (
            <div className={s.pagination}>
              <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>←</button>
              <span>Page {page + 1} / {pages}</span>
              <button onClick={() => setPage(p => Math.min(pages - 1, p + 1))} disabled={page >= pages - 1}>→</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ── Dashboard ────────────────────────────────────────────────────────────────

function Dashboard({ pw, onLogout }) {
  const [stats, setStats] = useState(null)
  const [err, setErr]     = useState('')

  useEffect(() => {
    fetch(`${API}/api/admin/stats?pw=${encodeURIComponent(pw)}`)
      .then(r => r.json())
      .then(setStats)
      .catch(() => setErr('Impossible de charger les stats'))
  }, [pw])

  const topStage = stats?.by_stage ? Object.entries(stats.by_stage)[0] : null

  return (
    <div className={s.dashWrap}>
      {/* Header */}
      <header className={s.dashHeader}>
        <div className={s.dashHeaderLeft}>
          <span className={s.dashLogo}>⚙️</span>
          <div>
            <h1 className={s.dashTitle}>Tableau de bord Admin</h1>
            <p className={s.dashSub}>The Dot Resource Matcher</p>
          </div>
        </div>
        <button className={s.logoutBtn} onClick={onLogout}>Déconnexion</button>
      </header>

      <main className={s.dashMain}>
        {err && <p className={s.errBanner}>{err}</p>}

        {/* KPI cards */}
        <div className={s.statGrid}>
          <StatCard label="Diagnostics total" value={stats?.total} accent="#60a5fa" />
          <StatCard label="Aujourd'hui" value={stats?.today} accent="#34d399" />
          <StatCard
            label="Stade le plus courant"
            value={topStage ? (STAGE_FR[topStage[0]] ?? topStage[0]) : '—'}
            sub={topStage ? `${topStage[1]} diagnostics` : ''}
          />
          <StatCard
            label="Programme #1 recommandé"
            value={stats?.top_programs?.[0]?.name ?? '—'}
            sub={stats?.top_programs?.[0] ? `${stats.top_programs[0].count} fois` : ''}
          />
        </div>

        {/* Charts row */}
        {stats && (
          <div className={s.chartsRow}>
            <BarChart data={stats.by_stage}  title="Répartition par stade" />
            <BarChart data={stats.by_sector} title="Répartition par secteur" />
          </div>
        )}

        {/* Top programmes */}
        {stats?.top_programs?.length > 0 && (
          <div className={s.topProgsBox}>
            <h3 className={s.chartTitle}>Top programmes recommandés</h3>
            <div className={s.topProgsList}>
              {stats.top_programs.map((p, i) => (
                <div key={p.name} className={s.topProgRow}>
                  <span className={s.topProgRank}>#{i + 1}</span>
                  <span className={s.topProgName}>{p.name}</span>
                  <span className={s.topProgCount}>{p.count} recommandations</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Submissions table */}
        <SubmissionsTable pw={pw} />
      </main>
    </div>
  )
}

// ── Root component ───────────────────────────────────────────────────────────

export default function Admin() {
  const navigate = useNavigate()
  const [pw, setPw] = useState(() => sessionStorage.getItem(PW_KEY) ?? '')

  function handleLogin(p) {
    sessionStorage.setItem(PW_KEY, p)
    setPw(p)
  }

  function handleLogout() {
    sessionStorage.removeItem(PW_KEY)
    setPw('')
  }

  return pw
    ? <Dashboard pw={pw} onLogout={handleLogout} />
    : <LoginScreen onLogin={handleLogin} />
}
