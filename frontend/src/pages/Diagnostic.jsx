import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import s from './Diagnostic.module.css'

const TOTAL_STEPS = 7

const INITIAL = {
  startup_name: '', sector: 'tech', business_model: 'b2b',
  business_model_type: 'saas', market_type: 'local', market_size: 'medium',
  diaspora_founder: false, outside_tunis: false,
  stage: 'pre-seed', has_product: false, has_customers: false, has_revenue: false,
  team_size: 1, full_time_count: 1, has_tech_cofounder: false,
  has_business_cofounder: false, has_competitive_advantage: false, has_ip_protection: false,
  legal_status: 'not_incorporated', has_startup_label: false, has_branding: false,
  funding_need: 'none', funding_range: 'none', has_pitch_deck: false, seeking_investors: false,
  is_ai_startup: false, is_industry40: false, is_mobile_focused: false,
  needs_workspace: false, needs_content_production: false, needs_events_space: false,
  needs_mentorship: false, needs_market_access: false, needs_legal_expert: false,
  value_proposition: '',
}

export default function Diagnostic() {
  const nav = useNavigate()
  const [step, setStep] = useState(1)
  const [form, setForm] = useState(INITIAL)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const toggle = k => setForm(f => ({ ...f, [k]: !f[k] }))

  const canNext = () => {
    if (step === 1 && !form.startup_name.trim()) return false
    return true
  }

  const submit = async () => {
    if (!form.startup_name.trim()) { setError('Le nom de la startup est requis.'); return }
    setLoading(true); setError('')
    try {
      const res = await fetch('/api/match', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) throw new Error(`Erreur serveur: ${res.status}`)
      const data = await res.json()
      // Store API result + original form so Results page can build eligibility checklists
      sessionStorage.setItem('dotResults', JSON.stringify({ ...data, form }))
      nav('/results')
    } catch (e) {
      setError(e.message || 'Erreur de connexion au serveur. Vérifiez que l\'API est démarrée.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={s.wrap}>
      {/* Header */}
      <div className={s.header}>
        <button className={s.back} onClick={() => step === 1 ? nav('/') : setStep(step - 1)}>← {step === 1 ? 'Accueil' : 'Retour'}</button>
        <div className={s.headerTitle}>The Dot — Resource Matcher</div>
        <div className={s.stepBadge}>{step} / {TOTAL_STEPS}</div>
      </div>

      {/* Progress */}
      <div className={s.progressWrap}>
        {Array.from({ length: TOTAL_STEPS }, (_, i) => (
          <div key={i} className={`${s.progressBar} ${i < step ? s.progressDone : ''} ${i === step - 1 ? s.progressActive : ''}`} />
        ))}
      </div>

      {/* Form Card */}
      <div className={s.card}>
        <div className={s.stepLabel}>{STEP_LABELS[step - 1]}</div>

        {step === 1 && <Step1 form={form} set={set} toggle={toggle} />}
        {step === 2 && <Step2 form={form} set={set} toggle={toggle} />}
        {step === 3 && <Step3 form={form} set={set} toggle={toggle} />}
        {step === 4 && <Step4 form={form} set={set} toggle={toggle} />}
        {step === 5 && <Step5 form={form} set={set} toggle={toggle} />}
        {step === 6 && <Step6 form={form} set={set} toggle={toggle} />}
        {step === 7 && <Step7 form={form} set={set} toggle={toggle} />}

        {error && <div className={s.error}>{error}</div>}

        <div className={s.actions}>
          {step < TOTAL_STEPS ? (
            <button className={s.btnPrimary} onClick={() => canNext() ? setStep(step + 1) : setError('Veuillez remplir les champs obligatoires.')} disabled={!canNext()}>
              Continuer →
            </button>
          ) : (
            <button className={s.btnSubmit} onClick={submit} disabled={loading}>
              {loading ? '⚡ Analyse en cours…' : '🔍 Analyser ma startup'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

/* ── Step labels ── */
const STEP_LABELS = [
  '🏢 Identité de la startup',
  '📈 Stade & maturité',
  '👥 Équipe',
  '⚖️ Statut juridique',
  '💰 Financement',
  '🔬 Profil technologique',
  '💡 Proposition de valeur',
]

/* ── Step 1: Identity ── */
function Step1({ form, set }) {
  return (
    <div className={s.fields}>
      <Field label="Nom de la startup *" required>
        <input className={s.input} value={form.startup_name} onChange={e => set('startup_name', e.target.value)} placeholder="ex. SaisIAR, Trip Hive…" maxLength={80} />
      </Field>
      <div className={s.row}>
        <Field label="Secteur d'activité">
          <select className={s.select} value={form.sector} onChange={e => set('sector', e.target.value)}>
            <option value="tech">Tech / Digital</option>
            <option value="fintech">Fintech</option>
            <option value="healthtech">Healthtech / MedTech</option>
            <option value="edtech">Edtech</option>
            <option value="agritech">Agritech</option>
            <option value="cleantech">Cleantech / GreenTech</option>
            <option value="saas">SaaS</option>
            <option value="marketplace">Marketplace</option>
            <option value="commerce">Commerce / Retail</option>
            <option value="industry">Industrie / Manufacturing</option>
            <option value="other">Autre</option>
          </select>
        </Field>
        <Field label="Relations commerciales">
          <select className={s.select} value={form.business_model} onChange={e => set('business_model', e.target.value)}>
            <option value="b2c">B2C (grand public)</option>
            <option value="b2b">B2B (entreprises)</option>
            <option value="b2b2c">B2B2C</option>
            <option value="marketplace">Marketplace</option>
            <option value="other">Autre / Mixte</option>
          </select>
        </Field>
      </div>
      <div className={s.row}>
        <Field label="Type de modèle">
          <select className={s.select} value={form.business_model_type} onChange={e => set('business_model_type', e.target.value)}>
            <option value="saas">SaaS (abonnement)</option>
            <option value="service">Service / Conseil</option>
            <option value="product">Produit physique</option>
            <option value="marketplace">Marketplace / Plateforme</option>
            <option value="other">Autre / Mixte</option>
          </select>
        </Field>
        <Field label="Marché cible">
          <select className={s.select} value={form.market_type} onChange={e => set('market_type', e.target.value)}>
            <option value="local">Local (Tunisie)</option>
            <option value="regional">Régional (Maghreb / Afrique)</option>
            <option value="international">International (Europe / Monde)</option>
          </select>
        </Field>
      </div>
      <div className={s.row}>
        <Field label="Taille de marché estimée">
          <select className={s.select} value={form.market_size} onChange={e => set('market_size', e.target.value)}>
            <option value="small">Petit (&lt; 1M TND)</option>
            <option value="medium">Moyen (1M – 50M TND)</option>
            <option value="large">Grand (&gt; 50M TND)</option>
          </select>
        </Field>
      </div>
      <div className={s.checks}>
        <Check label="👋 Je suis un entrepreneur de la diaspora tunisienne" checked={form.diaspora_founder} onChange={() => set('diaspora_founder', !form.diaspora_founder)} />
        <Check label="📍 Startup basée hors des grands hubs côtiers (hors Tunis, Sousse, Sfax, Médenine)" checked={form.outside_tunis} onChange={() => set('outside_tunis', !form.outside_tunis)} />
      </div>
    </div>
  )
}

/* ── Step 2: Stage ── */
function Step2({ form, set }) {
  const STAGES = [
    { val: 'ideation',  icon: '💡', label: 'Idéation', desc: 'Concept — pas encore de produit' },
    { val: 'pre-seed',  icon: '🔨', label: 'Pré-seed',  desc: 'Construction du MVP' },
    { val: 'seed',      icon: '🌱', label: 'Seed',      desc: 'Produit validé, premiers clients' },
    { val: 'growth',    icon: '📊', label: 'Croissance', desc: 'Revenus, mise à l\'échelle' },
    { val: 'scale',     icon: '🚀', label: 'Scale',     desc: 'Expansion nouveaux marchés' },
  ]
  return (
    <div className={s.fields}>
      <div className={s.stageGrid}>
        {STAGES.map(st => (
          <button key={st.val} className={`${s.stageCard} ${form.stage === st.val ? s.stageActive : ''}`} onClick={() => set('stage', st.val)}>
            <span className={s.stageIcon}>{st.icon}</span>
            <span className={s.stageName}>{st.label}</span>
            <span className={s.stageDesc}>{st.desc}</span>
          </button>
        ))}
      </div>
      <div className={s.sectionTitle}>Maturité actuelle</div>
      <div className={s.checkRow}>
        <Check label="✅ Nous avons un produit / MVP fonctionnel" checked={form.has_product} onChange={() => set('has_product', !form.has_product)} />
        <Check label="✅ Nous avons des clients actifs ou payants" checked={form.has_customers} onChange={() => set('has_customers', !form.has_customers)} />
        <Check label="✅ Nous générons du chiffre d'affaires" checked={form.has_revenue} onChange={() => set('has_revenue', !form.has_revenue)} />
      </div>
    </div>
  )
}

/* ── Step 3: Team ── */
function Step3({ form, set }) {
  return (
    <div className={s.fields}>
      <div className={s.row}>
        <Field label="Nombre de fondateurs">
          <input type="number" className={s.input} min={1} max={20} value={form.team_size} onChange={e => set('team_size', parseInt(e.target.value) || 1)} />
        </Field>
        <Field label="Personnes dédiées à 100%" hint="Fondateurs + employés temps plein sur le projet">
          <input type="number" className={s.input} min={0} max={20} value={form.full_time_count} onChange={e => set('full_time_count', parseInt(e.target.value) || 0)} />
        </Field>
      </div>
      <div className={s.checks}>
        <Check label="🔧 Nous avons un co-fondateur technique (CTO / dev lead)" checked={form.has_tech_cofounder} onChange={() => set('has_tech_cofounder', !form.has_tech_cofounder)} />
        <Check label="📊 Nous avons un co-fondateur commercial (business lead)" checked={form.has_business_cofounder} onChange={() => set('has_business_cofounder', !form.has_business_cofounder)} />
        <Check label="🏆 Nous avons un avantage concurrentiel identifié (techno propriétaire, IP, réseau exclusif…)" checked={form.has_competitive_advantage} onChange={() => set('has_competitive_advantage', !form.has_competitive_advantage)} />
        <Check label="🔒 Technologie brevetée ou propriété intellectuelle protégée" checked={form.has_ip_protection} onChange={() => set('has_ip_protection', !form.has_ip_protection)} />
      </div>
    </div>
  )
}

/* ── Step 4: Legal ── */
function Step4({ form, set }) {
  const OPTIONS = [
    { val: 'not_incorporated', icon: '❌', label: 'Non constitué', desc: 'Pas encore d\'entité juridique' },
    { val: 'in_progress',      icon: '⏳', label: 'En cours',      desc: 'Constitution en cours' },
    { val: 'incorporated_suarl', icon: '✅', label: 'SUARL',      desc: 'Société Unipersonnelle à Responsabilité Limitée' },
    { val: 'incorporated_sarl',  icon: '✅', label: 'SARL',       desc: 'Société À Responsabilité Limitée' },
    { val: 'incorporated_sa',    icon: '✅', label: 'SA',         desc: 'Société Anonyme' },
    { val: 'foreign_entity',   icon: '🌍', label: 'Entité étrangère', desc: 'Implantation en Tunisie depuis l\'étranger' },
  ]
  return (
    <div className={s.fields}>
      <div className={s.legalGrid}>
        {OPTIONS.map(o => (
          <button key={o.val} className={`${s.legalCard} ${form.legal_status === o.val ? s.legalActive : ''}`} onClick={() => set('legal_status', o.val)}>
            <span className={s.legalIcon}>{o.icon}</span>
            <span className={s.legalName}>{o.label}</span>
            <span className={s.legalDesc}>{o.desc}</span>
          </button>
        ))}
      </div>
      <div className={s.checks}>
        <Check label="🏷️ Nous détenons le label Startup Act tunisien" checked={form.has_startup_label} onChange={() => set('has_startup_label', !form.has_startup_label)} />
        <Check label="🎨 Nous avons une identité de marque établie (logo, charte, positionnement)" checked={form.has_branding} onChange={() => set('has_branding', !form.has_branding)} />
      </div>
    </div>
  )
}

/* ── Step 5: Funding ── */
function Step5({ form, set }) {
  const TYPES = [
    { val: 'none',        icon: '—',  label: 'Pas de levée active' },
    { val: 'grant',       icon: '🏛️', label: 'Subventions / SICAR' },
    { val: 'angel',       icon: '👼', label: 'Business angels' },
    { val: 'vc',          icon: '📈', label: 'Capital-risque (VC)' },
    { val: 'institutional', icon:'🏦', label: 'Institutionnel / PE' },
  ]
  const RANGES = [
    { val: 'none',      label: '—' },
    { val: 'under_50k', label: '< 50 000 TND' },
    { val: '50k_200k',  label: '50 000 – 200 000 TND' },
    { val: '200k_1m',   label: '200 000 – 1 000 000 TND' },
    { val: 'above_1m',  label: '> 1 000 000 TND' },
  ]
  return (
    <div className={s.fields}>
      <div className={s.sectionTitle}>Type de financement recherché</div>
      <div className={s.fundingGrid}>
        {TYPES.map(t => (
          <button key={t.val} className={`${s.fundingCard} ${form.funding_need === t.val ? s.fundingActive : ''}`} onClick={() => set('funding_need', t.val)}>
            <span className={s.fundingIcon}>{t.icon}</span>
            <span className={s.fundingLabel}>{t.label}</span>
          </button>
        ))}
      </div>
      <Field label="Montant recherché (TND)">
        <select className={s.select} value={form.funding_range} onChange={e => set('funding_range', e.target.value)}>
          {RANGES.map(r => <option key={r.val} value={r.val}>{r.label}</option>)}
        </select>
      </Field>
      <div className={s.checks}>
        <Check label="📊 Nous avons un pitch deck préparé pour des investisseurs" checked={form.has_pitch_deck} onChange={() => set('has_pitch_deck', !form.has_pitch_deck)} />
        <Check label="🤝 Nous cherchons activement des introductions auprès d'investisseurs" checked={form.seeking_investors} onChange={() => set('seeking_investors', !form.seeking_investors)} />
      </div>
    </div>
  )
}

/* ── Step 6: Tech profile ── */
function Step6({ form, set }) {
  const items = [
    { key: 'is_ai_startup',           icon: '🤖', label: 'Nous développons des solutions IA / ML' },
    { key: 'is_industry40',           icon: '🏭', label: 'Industrie 4.0 / IoT / Manufacturing' },
    { key: 'is_mobile_focused',       icon: '📱', label: 'Solution mobile-first' },
    { key: 'needs_workspace',         icon: '🏢', label: 'Besoin d\'espace de travail / bureau' },
    { key: 'needs_content_production',icon: '🎬', label: 'Besoin de studio design / vidéo' },
    { key: 'needs_events_space',      icon: '🎤', label: 'Besoin d\'espace événementiel / conférence' },
    { key: 'needs_mentorship',        icon: '🧠', label: 'En recherche de mentor ou conseiller senior' },
    { key: 'needs_market_access',     icon: '🌍', label: 'Besoin d\'aide pour accéder aux marchés' },
    { key: 'needs_legal_expert',      icon: '⚖️', label: 'Besoin d\'expertise juridique / fiscale (structuration, IP, pacte d\'associés…)' },
  ]
  return (
    <div className={s.fields}>
      <div className={s.checkGrid}>
        {items.map(({ key, icon, label }) => (
          <button key={key} className={`${s.techCard} ${form[key] ? s.techActive : ''}`} onClick={() => set(key, !form[key])}>
            <span className={s.techIcon}>{icon}</span>
            <span className={s.techLabel}>{label}</span>
            {form[key] && <span className={s.techCheck}>✓</span>}
          </button>
        ))}
      </div>
    </div>
  )
}

/* ── Step 7: Value proposition ── */
function Step7({ form, set }) {
  return (
    <div className={s.fields}>
      <Field label="Décrivez votre startup en 2–3 phrases (optionnel)" hint="Cette description améliore la précision du matching sémantique IA.">
        <textarea
          className={s.textarea}
          rows={5}
          value={form.value_proposition}
          onChange={e => set('value_proposition', e.target.value)}
          placeholder="Ex: SaisIAR automatise la saisie comptable par IA. Notre moteur propriétaire traite factures et relevés bancaires sans dépendance externe, garantissant confidentialité et conformité PCG tunisien. Nous ciblons les cabinets comptables B2B en Tunisie et Maghreb."
          maxLength={500}
        />
        <div className={s.charCount}>{form.value_proposition.length} / 500</div>
      </Field>
      <div className={s.summary}>
        <div className={s.summaryTitle}>Récapitulatif</div>
        <div className={s.summaryGrid}>
          <SumItem label="Startup" val={form.startup_name || '—'} />
          <SumItem label="Secteur" val={form.sector} />
          <SumItem label="Stade" val={form.stage} />
          <SumItem label="Marché" val={form.market_type} />
          <SumItem label="Équipe" val={`${form.team_size} fondateur${form.team_size > 1 ? 's' : ''}`} />
          <SumItem label="Financement" val={form.funding_need === 'none' ? 'Pas de levée' : form.funding_need} />
          <SumItem label="Statut" val={form.legal_status.replace('_', ' ')} />
          <SumItem label="IA / ML" val={form.is_ai_startup ? 'Oui ✓' : 'Non'} />
        </div>
      </div>
    </div>
  )
}

/* ── Helpers ── */
function Field({ label, hint, required, children }) {
  return (
    <div className={s.field}>
      <label className={s.label}>{label}{required && <span style={{color:'#f87171'}}> *</span>}</label>
      {hint && <div className={s.hint}>{hint}</div>}
      {children}
    </div>
  )
}

function Check({ label, checked, onChange }) {
  return (
    <button className={`${s.check} ${checked ? s.checkActive : ''}`} onClick={onChange}>
      <span className={s.checkBox}>{checked ? '✓' : ''}</span>
      <span className={s.checkLabel}>{label}</span>
    </button>
  )
}

function SumItem({ label, val }) {
  return (
    <div className={s.sumItem}>
      <span className={s.sumLabel}>{label}</span>
      <span className={s.sumVal}>{val}</span>
    </div>
  )
}
