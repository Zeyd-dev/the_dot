import { useNavigate } from 'react-router-dom'
import styles from './Home.module.css'

export default function Home() {
  const nav = useNavigate()
  return (
    <div className={styles.wrap}>
      <div className={styles.hero}>
        <div className={styles.eyebrow}>The Dot — Tunisia's Leading Startup Hub</div>
        <h1 className={styles.title}>
          Trouvez votre programme<br/>
          <span className={styles.accent}>au sein de The Dot</span>
        </h1>
        <p className={styles.sub}>
          Répondez à 7 questions sur votre startup. Obtenez un radar de maturité personnalisé, des conseils stratégiques et les meilleurs programmes recommandés — propulsé par l'IA.
        </p>
        <div className={styles.stats}>
          <div className={styles.stat}><span className={styles.statVal}>9</span><span className={styles.statLabel}>Programmes analysés</span></div>
          <div className={styles.stat}><span className={styles.statVal}>7</span><span className={styles.statLabel}>Dimensions de maturité</span></div>
          <div className={styles.stat}><span className={styles.statVal}>~3s</span><span className={styles.statLabel}>Analyse IA</span></div>
        </div>
        <button className={styles.cta} onClick={() => nav('/diagnostic')}>
          Démarrer le diagnostic →
        </button>
      </div>

      <div className={styles.programs}>
        <div className={styles.sectionLabel}>Programmes disponibles</div>
        <div className={styles.programGrid}>
          {PROGRAMS.map(p => (
            <div key={p.id} className={styles.programCard}>
              <div className={styles.programIcon}>{p.icon}</div>
              <div className={styles.programName}>{p.name}</div>
              <div className={styles.programDesc}>{p.desc}</div>
            </div>
          ))}
        </div>
      </div>

      <div className={styles.footer}>
        <span>The Dot Resource Matcher v2.0</span>
        <a href="/admin" style={{color:'rgba(255,255,255,0.2)',fontSize:'0.72rem'}}>Admin →</a>
      </div>
    </div>
  )
}

const PROGRAMS = [
  { id:'R001', icon:'🏕️', name:'Dot Camp', desc:'Incubation flagship 1 an — espace de travail, réseau investisseurs' },
  { id:'R002', icon:'📍', name:'Dot Camp+', desc:'Pré-incubation 4 mois pour fondateurs régionaux hors hubs' },
  { id:'R003', icon:'✈️', name:'Dot Landing', desc:'Programme diaspora — implantation en Tunisie en 4 mois' },
  { id:'R004', icon:'🧠', name:'Executives in Residence', desc:'25+ cadres seniors pour mentorship stratégique' },
  { id:'R005', icon:'⚖️', name:'Dot Expert', desc:'Sessions 1-on-1 avec experts certifiés (droit, finance, stratégie)' },
  { id:'R006', icon:'🤝', name:'Dot Community', desc:'Services peer-to-peer entre membres de la communauté' },
  { id:'R007', icon:'🤖', name:'AI Hub', desc:'Infra GPU + mentorship InstaDeep pour startups IA' },
  { id:'R008', icon:'🌐', name:'Dot Support', desc:'Réseau de 50+ SSOs et partenaires institutionnels' },
  { id:'R009', icon:'🇪🇺', name:'TECH216', desc:'Nearshoring IT vers l\'Europe — clients allemands, BMW Group' },
]
