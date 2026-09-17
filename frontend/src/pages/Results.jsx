import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Chart as ChartJS, RadialLinearScale, PointElement,
  LineElement, Filler, Tooltip, Legend,
} from 'chart.js'
import { Radar } from 'react-chartjs-2'
import s from './Results.module.css'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

// ── Constants ─────────────────────────────────────────────────────────────────

const DIMS     = ['Team', 'Legal', 'Product', 'Traction', 'Funding', 'Market', 'Branding']
const DIM_KEYS = ['team', 'legal', 'product', 'traction', 'funding', 'market', 'branding']

const BOOST_MAP = {
  program:    ['product', 'traction'],
  expertise:  ['legal', 'funding'],
  mentorship: ['team', 'market'],
  service:    ['branding', 'product'],
  investment: ['funding', 'traction'],
  network:    ['market', 'team'],
}

const TIPS = {
  team:     ['🧑‍🤝‍🧑', 'Team Gap',              "Trouver un co-fondateur ou exploiter le réseau Executives in Residence de The Dot."],
  legal:    ['⚖️',  'Blocage juridique',      'Constituez votre entité avant toute levée ou signature de contrat commercial.'],
  product:  ['🛠️',  'Pas encore de produit',  'Validez votre idée avec un MVP lean avant d\'approcher des investisseurs.'],
  traction: ['📈',  'Pas encore de traction', 'Décrochez votre premier client payant avant de contacter des investisseurs.'],
  funding:  ['💰',  'Stratégie de levée floue','Subventions, angels et VC ont chacun leurs critères de maturité requis.'],
  market:   ['🌍',  'Portée marché limitée',  "TECH216 ou Bridge'up peuvent ouvrir des portes à l'international."],
  branding: ['🎨',  'Marque non établie',     'Une marque crédible est essentielle pour le B2B et la levée de fonds.'],
}

const PRI = {
  high:   { color: '#10b981', label: 'Haute priorité',   icon: '🟢' },
  medium: { color: '#f59e0b', label: 'Priorité moyenne', icon: '🟡' },
  low:    { color: '#6b7280', label: 'Faible priorité',  icon: '⚪' },
}

const TYPE_ICONS = {
  program:    '🚀',
  service:    '⚡',
  mentorship: '🧠',
  investment: '💰',
  network:    '🌐',
  expertise:  '🔬',
}

const STAGE_LABELS = {
  ideation: 'Idéation', 'pre-seed': 'Pré-seed',
  seed: 'Seed', growth: 'Croissance', scale: 'Scale',
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Results() {
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [activeTab, setActiveTab] = useState('all')

  useEffect(() => {
    const raw = sessionStorage.getItem('dotResults')
    if (!raw) { nav('/diagnostic'); return }
    try { setData(JSON.parse(raw)) } catch { nav('/diagnostic') }
  }, [nav])

  if (!data) return <div className={s.loading}>⚡ Chargement…</div>

  const {
    form = {},
    startup_name,
    effective_stage,
    stage_warning,
    spider_scores = {},
    needs = [],
    results = [],
  } = data

  const llmPowered = results.some(r => r.llm_powered)
  const scores = DIMS.map(d => spider_scores[d] ?? 0)

  const tabs = ['all', 'high', 'medium', 'low']
  const tabCounts = {
    all: results.length,
    high: results.filter(r => r.priority === 'high').length,
    medium: results.filter(r => r.priority === 'medium').length,
    low: results.filter(r => r.priority === 'low').length,
  }
  const filtered = activeTab === 'all' ? results : results.filter(r => r.priority === activeTab)

  const downloadJSON = () => {
    const payload = {
      startup_name,
      effective_stage,
      spider_scores,
      needs,
      generated_at: data.timestamp,
      results: results.map((r, i) => ({
        rank: i + 1,
        name: r.name,
        type: r.type,
        score: Math.round(r.score),
        priority: r.priority,
        eligible: r.eligible,
        advice: r.advice,
        url: r.url,
      })),
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `thedot_${(startup_name || 'diagnostic').replace(/\s+/g, '_').toLowerCase()}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className={s.wrap}>

      {/* ── Topbar ── */}
      <div className={s.topbar}>
        <button className={s.backBtn} onClick={() => nav('/diagnostic')}>
          ← Modifier le diagnostic
        </button>
        <button className={s.homeBtn} onClick={() => nav('/')}>🏠</button>
      </div>

      {/* ── Hero ── */}
      <div className={s.hero}>
        <div className={s.heroInner}>
          <div className={s.heroLeft}>
            <div className={s.startupBadge}>{startup_name}</div>
            <h1 className={s.heroTitle}>Vos programmes recommandés</h1>
            <div className={s.stagePill}>
              Stade effectif&nbsp;:&nbsp;
              <strong>{STAGE_LABELS[effective_stage] || effective_stage}</strong>
              {llmPowered && (
                <span className={s.aiBadgeHero}>⚡ AI-powered</span>
              )}
            </div>
            {stage_warning && (
              <div className={s.stageWarning}>
                ⚠️ {stage_warning.replace(/\*\*/g, '')}
              </div>
            )}
            <div className={s.stats}>
              <StatBubble val={results.length} label="Analysés" />
              <StatBubble val={tabCounts.high} label="Haute priorité" color="#10b981" />
              <StatBubble val={results.filter(r => r.eligible).length} label="Éligibles" color="#60a5fa" />
            </div>
          </div>
          <div className={s.heroRight}>
            <SpiderChart spiderScores={spider_scores} />
          </div>
        </div>
      </div>

      {/* ── Score pills ── */}
      <ScorePills scores={scores} />

      {/* ── Snapshot panel ── */}
      <SnapshotPanel scores={scores} needs={needs} form={form} effectiveStage={effective_stage} />

      {/* ── Content ── */}
      <div className={s.content}>

        {/* Tabs */}
        <div className={s.tabs}>
          {tabs.map(t => (
            <button
              key={t}
              className={`${s.tab} ${activeTab === t ? s.tabActive : ''}`}
              onClick={() => setActiveTab(t)}
            >
              {t === 'all' ? '📋 Tous' : t === 'high' ? '🟢 Haute priorité' : t === 'medium' ? '🟡 Moyenne' : '⚪ Faible'}
              <span className={s.tabCount}>{tabCounts[t]}</span>
            </button>
          ))}
        </div>

        {/* Cards */}
        <div className={s.cards}>
          {filtered.length === 0 && (
            <div className={s.empty}>Aucun programme pour ce filtre.</div>
          )}
          {filtered.map((r, i) => (
            <ProgramCard
              key={r.id || r.name}
              r={r}
              rank={i + 1}
              scores={scores}
              form={form}
              effectiveStage={effective_stage}
            />
          ))}
        </div>

        {/* Export */}
        <div className={s.exportSection}>
          <div className={s.exportTitle}>Export</div>
          <div className={s.exportBtns}>
            <button className={s.exportBtn} onClick={downloadJSON}>
              ⬇️ Télécharger JSON
            </button>
            <button className={s.exportBtnSec} onClick={() => window.print()}>
              🖨️ Imprimer / PDF
            </button>
          </div>
        </div>

        {/* CTA */}
        <div className={s.cta}>
          <button className={s.ctaBtn} onClick={() => nav('/diagnostic')}>
            🔄 Recommencer le diagnostic
          </button>
          <button className={s.ctaSecondary} onClick={() => nav('/')}>
            ← Accueil
          </button>
        </div>

      </div>
    </div>
  )
}

// ── Spider chart ───────────────────────────────────────────────────────────────

function SpiderChart({ spiderScores }) {
  const labels = Object.keys(spiderScores)
  const values = Object.values(spiderScores)
  return (
    <div className={s.chartWrap}>
      <div className={s.chartTitle}>Profil de maturité</div>
      <Radar
        data={{
          labels,
          datasets: [{
            label: 'Maturité',
            data: values,
            backgroundColor: 'rgba(96,165,250,0.15)',
            borderColor: '#60a5fa',
            borderWidth: 2,
            pointBackgroundColor: '#fff',
            pointBorderColor: '#60a5fa',
            pointRadius: 3,
          }],
        }}
        options={{
          responsive: true,
          maintainAspectRatio: true,
          scales: {
            r: {
              min: 0, max: 100,
              ticks: {
                stepSize: 25,
                color: '#666',
                font: { size: 10 },
                backdropColor: 'transparent',
              },
              grid: { color: 'rgba(255,255,255,0.08)' },
              pointLabels: { color: '#ccc', font: { size: 11, weight: '600' } },
              angleLines: { color: 'rgba(255,255,255,0.06)' },
            },
          },
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: { label: ctx => ` ${ctx.raw} / 100` },
            },
          },
        }}
      />
    </div>
  )
}

// ── Score pills ────────────────────────────────────────────────────────────────

function ScorePills({ scores }) {
  return (
    <div className={s.scorePillsWrap}>
      <div className={s.scorePills}>
        {DIMS.map((dim, i) => {
          const sc = scores[i] ?? 0
          const color = sc >= 70 ? '#4ade80' : sc >= 40 ? '#facc15' : '#f87171'
          return (
            <div key={dim} className={s.scorePill}>
              <div className={s.scorePillDim}>{dim}</div>
              <div className={s.scorePillVal} style={{ color }}>{sc}</div>
              <div className={s.scorePillBar}>
                <div
                  className={s.scorePillFill}
                  style={{ width: `${sc}%`, background: color }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Snapshot panel ────────────────────────────────────────────────────────────

function SnapshotPanel({ scores, needs, form, effectiveStage }) {
  const incorporated = !['not_incorporated', 'in_progress'].includes(form?.legal_status || '')

  const statusFlags = [
    {
      ok: incorporated,
      icon: '⚖️',
      label: 'Juridique',
      val: incorporated ? 'Constitué' : 'Non constitué',
    },
    {
      ok: (scores[0] ?? 0) >= 40,
      icon: '🧑‍🤝‍🧑',
      label: 'Équipe',
      val: (scores[0] ?? 0) >= 40 ? 'Couverte' : 'Lacune détectée',
    },
    {
      ok: !!(form?.has_customers || form?.has_revenue),
      icon: '📈',
      label: 'Traction',
      val: form?.has_customers ? 'Validée' : 'Pas encore',
    },
    {
      ok: form?.funding_need === 'none',
      icon: '💰',
      label: 'Levée',
      val: form?.funding_need === 'none'
        ? 'Pas de levée active'
        : (form?.funding_need || '').toUpperCase(),
    },
  ]

  // Build strategic advice cards
  const weakDims = DIM_KEYS
    .map((key, i) => ({ key, score: scores[i] ?? 0 }))
    .filter(d => d.score < 50)
    .sort((a, b) => a.score - b.score)

  const strongDims = DIMS.filter((_, i) => (scores[i] ?? 0) >= 70)

  const adviceCards = []
  if (weakDims.length === 0) {
    adviceCards.push({
      kind: 'ok', icon: '✅',
      title: 'Profil solide',
      body: "Vous êtes fort sur toutes les dimensions. Concentrez-vous sur l'exécution et exploitez le réseau de The Dot.",
    })
  } else {
    weakDims.slice(0, 3).forEach(({ key }) => {
      if (TIPS[key]) {
        const [icon, title, body] = TIPS[key]
        adviceCards.push({ kind: 'warn', icon, title, body })
      }
    })
  }
  if (strongDims.length > 0) {
    adviceCards.push({
      kind: 'ok', icon: '⭐',
      title: `Points forts : ${strongDims.join(', ')}`,
      body: 'Exploitez ces atouts comme avantages concurrentiels dans vos pitches.',
    })
  }
  if (form?.diaspora_founder) adviceCards.push({
    kind: 'info', icon: '🌍',
    title: 'Entrepreneur de la diaspora',
    body: 'Dot Landing est fait pour vous : 4 mois de soutien intensif entièrement gratuit.',
  })
  if (form?.outside_tunis) adviceCards.push({
    kind: 'info', icon: '📍',
    title: 'Startup régionale',
    body: 'Dot Camp+ supprime la barrière géographique et est conçu pour votre région.',
  })
  if (form?.seeking_investors) adviceCards.push({
    kind: 'info', icon: '💼',
    title: 'Levée de fonds en vue',
    body: 'Préparez structure juridique, modèle financier et MVP avant tout contact avec un VC.',
  })
  if (form?.is_ai_startup) adviceCards.push({
    kind: 'info', icon: '🤖',
    title: 'Startup IA',
    body: "L'AI Hub vous donne accès au calcul GPU et aux formations partenaires NVIDIA.",
  })
  if (form?.is_industry40) adviceCards.push({
    kind: 'info', icon: '🏭',
    title: 'Industrie 4.0',
    body: 'TECH216 peut ouvrir des partenariats de nearshoring avec des industriels européens.',
  })

  const kindStyle = {
    warn: { accent: '#f59e0b', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.22)' },
    ok:   { accent: '#10b981', bg: 'rgba(16,185,129,0.08)',  border: 'rgba(16,185,129,0.22)' },
    info: { accent: '#60a5fa', bg: 'rgba(96,165,250,0.08)',  border: 'rgba(96,165,250,0.22)' },
  }

  return (
    <div className={s.snapshot}>
      <div className={s.snapshotGrid}>

        {/* Needs */}
        <div className={s.snapshotBox}>
          <div className={s.snapshotBoxTitle}>🎯 Besoins identifiés</div>
          <div className={s.needsTags}>
            {needs.length === 0
              ? <span style={{ color: 'rgba(255,255,255,0.3)', fontSize: '.8rem' }}>Aucun besoin spécifique détecté.</span>
              : needs.map(n => (
                  <span key={n} className={s.needsTag}>
                    {n.replace(/_/g, ' ')}
                  </span>
                ))
            }
          </div>
        </div>

        {/* Status flags */}
        <div className={s.snapshotBox}>
          <div className={s.snapshotBoxTitle}>📊 Indicateurs de statut</div>
          <div className={s.statusFlags}>
            {statusFlags.map(({ ok, icon, label, val }, i) => (
              <div key={i} className={`${s.statusFlag} ${ok ? s.flagOk : s.flagWarn}`}>
                <span className={s.flagIcon}>{icon}</span>
                <div>
                  <div className={s.flagLabel}>{label}</div>
                  <div className={s.flagVal}>{val}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Strategic advice */}
      <div className={s.snapshotBoxWide}>
        <div className={s.snapshotBoxTitle}>💡 Conseils stratégiques</div>
        <div className={s.adviceGrid}>
          {adviceCards.map((card, i) => {
            const { accent, bg, border } = kindStyle[card.kind]
            return (
              <div
                key={i}
                className={s.adviceCard}
                style={{ background: bg, borderColor: border, borderLeftColor: accent }}
              >
                <span className={s.adviceCardIcon}>{card.icon}</span>
                <div>
                  <div className={s.adviceCardTitle}>{card.title}</div>
                  <div className={s.adviceCardBody}>{card.body}</div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

// ── Eligibility checklist ─────────────────────────────────────────────────────

function buildChecklist(r, form, effectiveStage) {
  const checks = []
  const rid = (r.id || '').toUpperCase()
  const incorporated = !['not_incorporated', 'in_progress'].includes(form?.legal_status || '')
  const stagesRaw = r.stages_raw || []

  // Stage compatibility
  if (stagesRaw.length > 0) {
    checks.push([
      stagesRaw.includes(effectiveStage),
      `Stade ${STAGE_LABELS[effectiveStage] || effectiveStage} compatible`,
    ])
  }

  if (rid === 'R001') {
    checks.push([!!form?.has_product, 'Possède un MVP fonctionnel'])
    checks.push([incorporated, 'Juridiquement constitué'])
    checks.push([!form?.outside_tunis, 'Peut se baser à Tunis'])
  } else if (rid === 'R002') {
    checks.push([!!form?.outside_tunis, 'Basé hors des grands hubs côtiers'])
    checks.push([!form?.has_revenue, 'Pas encore en phase de revenus'])
  } else if (rid === 'R003') {
    checks.push([!!form?.diaspora_founder, 'Fondateur de la diaspora tunisienne'])
  } else if (rid === 'R004') {
    checks.push([!!form?.has_product, 'Possède un produit à challenger'])
    checks.push([['seed', 'growth', 'scale'].includes(effectiveStage), 'Stade Seed ou au-delà'])
  } else if (rid === 'R005') {
    checks.push([true, 'Accessible à tous les stades'])
    checks.push([true, 'Aucun prérequis — session à la demande'])
  } else if (rid === 'R006') {
    checks.push([true, 'Accessible à tous les membres The Dot'])
  } else if (rid === 'R007') {
    checks.push([true, 'Ouvert à toute la communauté The Dot'])
  } else if (rid === 'R008') {
    checks.push([!!form?.is_ai_startup, 'Produit IA / ML core'])
    checks.push([!!form?.has_product, 'Possède un MVP fonctionnel'])
    checks.push([incorporated, 'Juridiquement constitué'])
  } else if (rid === 'R009') {
    checks.push([['tech', 'saas', 'fintech'].includes(form?.sector || ''), 'Secteur Tech ou SaaS'])
    checks.push([incorporated, 'Juridiquement constitué'])
    checks.push([['seed', 'growth', 'scale'].includes(effectiveStage), 'Stade Seed ou au-delà'])
  } else {
    // Generic fallbacks
    checks.push([!!form?.has_product, 'Possède un MVP ou prototype'])
  }

  return checks
}

function EligibilityChecklist({ r, form, effectiveStage }) {
  const checks = buildChecklist(r, form, effectiveStage)
  const met = checks.filter(([ok]) => ok).length
  const total = checks.length
  const pct = total ? Math.round((met / total) * 100) : 0
  const barColor = pct >= 75 ? '#16a34a' : pct >= 50 ? '#f59e0b' : '#ef4444'

  return (
    <div className={s.eligWrap}>
      <div className={s.eligHeader}>
        <span className={s.eligTitle}>Éligibilité</span>
        <span style={{ fontSize: '.72rem', fontWeight: 700, color: barColor }}>
          {met}/{total} critères remplis
        </span>
      </div>
      <div className={s.eligBarBg}>
        <div
          className={s.eligBarFill}
          style={{ width: `${pct}%`, background: barColor }}
        />
      </div>
      <div className={s.eligItems}>
        {checks.map(([ok, label], i) => (
          <span key={i} className={`${s.eligItem} ${ok ? s.checkOk : s.checkFail}`}>
            {ok ? '✅' : '❌'} {label}
          </span>
        ))}
      </div>
    </div>
  )
}

// ── Impact radar ───────────────────────────────────────────────────────────────

function ImpactRadar({ scores, r }) {
  const boosted = BOOST_MAP[r.type] || ['product']
  const before = scores
  const after = scores.map((sc, i) =>
    boosted.includes(DIM_KEYS[i]) ? Math.min(sc + 25, 100) : sc
  )

  return (
    <div className={s.impactWrap}>
      <div className={s.impactTitle}>Impact estimé sur votre maturité</div>
      <div className={s.impactSubtitle}>
        Projection si vous complétez ce programme (dimensions boostées&nbsp;:&nbsp;
        {boosted.map(k => k.charAt(0).toUpperCase() + k.slice(1)).join(', ')})
      </div>
      <div className={s.impactLegend}>
        <span style={{ color: '#94a3b8' }}>— Avant</span>
        <span style={{ color: '#38bdf8', marginLeft: '1.25rem' }}>— Après</span>
      </div>
      <div className={s.impactChart}>
        <Radar
          data={{
            labels: DIMS,
            datasets: [
              {
                label: 'Avant',
                data: before,
                backgroundColor: 'rgba(148,163,184,0.06)',
                borderColor: '#94a3b8',
                borderWidth: 1.5,
                pointRadius: 2,
                pointBackgroundColor: '#94a3b8',
              },
              {
                label: 'Après',
                data: after,
                backgroundColor: 'rgba(56,189,248,0.18)',
                borderColor: '#38bdf8',
                borderWidth: 2,
                pointRadius: 3,
                pointBackgroundColor: '#fff',
                pointBorderColor: '#38bdf8',
              },
            ],
          }}
          options={{
            responsive: true,
            maintainAspectRatio: true,
            scales: {
              r: {
                min: 0, max: 100,
                ticks: { display: false },
                grid: { color: 'rgba(255,255,255,0.06)' },
                pointLabels: {
                  color: 'rgba(255,255,255,0.65)',
                  font: { size: 9, weight: '600' },
                },
                angleLines: { color: 'rgba(255,255,255,0.06)' },
              },
            },
            plugins: { legend: { display: false } },
          }}
        />
      </div>
    </div>
  )
}

// ── Program card ───────────────────────────────────────────────────────────────

function ProgramCard({ r, rank, scores, form, effectiveStage }) {
  const [impactOpen, setImpactOpen] = useState(false)
  const pri = PRI[r.priority] || PRI.low
  const typeIcon = TYPE_ICONS[r.type] || '📌'
  const score = Math.round(r.score ?? 0)
  const barColor = score >= 70 ? '#2563eb' : score >= 50 ? '#0891b2' : '#7c3aed'

  return (
    <div className={`${s.card} ${r.priority === 'high' ? s.cardHigh : ''}`}>

      {/* Header */}
      <div className={s.cardHeader}>
        <div className={s.cardLeft}>
          <div className={s.rankBadge}>#{rank}</div>
          <div className={s.typeIcon}>{typeIcon}</div>
          <div>
            <div className={s.cardName}>{r.name}</div>
            {r.duration && <div className={s.cardDuration}>⏱ {r.duration}</div>}
          </div>
        </div>
        <div className={s.cardRight}>
          <div
            className={s.scoreRing}
            style={{ '--score-pct': `${score}%`, '--score-color': pri.color }}
          >
            <span className={s.scoreNum}>{score}</span>
          </div>
        </div>
      </div>

      {/* Score bar */}
      <div className={s.scoreBarWrap}>
        <div className={s.sBarFill} style={{ width: `${score}%`, background: barColor }} />
      </div>

      {/* Badges row */}
      <div className={s.cardMeta}>
        <span
          className={s.priBadge}
          style={{
            background: pri.color + '22',
            color: pri.color,
            border: `1px solid ${pri.color}55`,
          }}
        >
          {pri.icon} {pri.label}
        </span>
        {r.eligible !== undefined && (
          <span className={`${s.eligBadge} ${r.eligible ? s.eligYes : s.eligNo}`}>
            {r.eligible ? '✓ Éligible' : '✗ Stade non ciblé'}
          </span>
        )}
        {r.type && <span className={s.typeBadge}>{r.type}</span>}
        {r.llm_powered && <span className={s.aiBadge}>⚡ AI</span>}
      </div>

      {/* Key benefit */}
      {r.key_benefit && (
        <div className={s.keyBenefit}>⭐ {r.key_benefit}</div>
      )}

      {/* Description */}
      {r.description && (
        <p className={s.cardDesc}>{r.description}</p>
      )}

      {/* Pour qui */}
      {r.eligibility_criteria && (
        <div className={s.pourQui}>
          <span className={s.pourQuiLabel}>Pour qui ?</span>
          <span className={s.pourQuiText}>{r.eligibility_criteria}</span>
        </div>
      )}

      {/* Deliverables */}
      {r.deliverables && (
        <div className={s.deliverables}>
          <span className={s.deliverablesLabel}>Ce que vous obtenez</span>
          <span className={s.deliverablesText}>{r.deliverables}</span>
        </div>
      )}

      {/* Reasons */}
      {r.reasons?.length > 0 && (
        <div className={s.reasons}>
          {r.reasons.map((reason, i) => (
            <span key={i} className={s.reason}>✓ {reason}</span>
          ))}
        </div>
      )}

      {/* AI advice */}
      {r.advice && (
        <div className={s.adviceBlock}>
          💬 {r.advice}
        </div>
      )}

      {/* Justification */}
      {r.justification && (
        <div className={s.justification}>
          💡 {r.justification}
        </div>
      )}

      {/* Eligibility checklist */}
      <EligibilityChecklist r={r} form={form} effectiveStage={effectiveStage} />

      {/* Impact radar toggle */}
      <button className={s.toggleBtn} onClick={() => setImpactOpen(v => !v)}>
        {impactOpen ? "▲ Masquer l'impact" : '▼ Voir l\'impact estimé sur ma maturité'}
      </button>
      {impactOpen && <ImpactRadar scores={scores} r={r} />}

      {/* Actions */}
      <div className={s.cardActions}>
        {r.url && (
          <a
            href={r.url}
            target="_blank"
            rel="noopener noreferrer"
            className={s.learnMore}
          >
            En savoir plus →
          </a>
        )}
        <a
          href={r.url || 'https://thedot.tn'}
          target="_blank"
          rel="noopener noreferrer"
          className={s.applyBtn}
        >
          Postuler →
        </a>
      </div>

    </div>
  )
}

// ── StatBubble ────────────────────────────────────────────────────────────────

function StatBubble({ val, label, color }) {
  return (
    <div className={s.statBubble}>
      <div className={s.statVal} style={color ? { color } : {}}>
        {val}
      </div>
      <div className={s.statLabel}>{label}</div>
    </div>
  )
}
