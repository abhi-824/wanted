import './dossier/dossier.css'

export default function DossierIndexPage() {
  return (
    <div className="dossier-page">
      <div className="scan-lines" />
      <div className="card-wrap">
        <div className="error-state">
          NO MP ID PROVIDED
          <br />
          <span className="error-muted">Usage: /dossier/&lt;myneta_id&gt;</span>
        </div>
      </div>
    </div>
  )
}
