import { Link } from 'react-router'

import StatChip from '../../components/StatChip'

export default function Hero() {
  return (
    <div className="left">
      <div className="sys-label">CROREPATI SEVAK // v1.0 // 18TH LOK SABHA</div>

      <div className="brand">
        NETA<span>CHECK</span>
      </div>

      <p className="tagline">
        India&apos;s parliament, mapped like a war room.
        <br />
        <strong>543 MPs. Real criminal records. Real assets.</strong>
        <br />
        All sourced from ECI affidavits via ADR — public data, made visible.
      </p>

      <div className="stats-strip">
        <StatChip value="543" label="MPs mapped" tone="blue" />
        <StatChip value="251" label="With cases" tone="red" />
        <StatChip value="₹46 Cr" label="Avg assets" tone="gold" />
        <StatChip value="46%" label="Crorepatis" tone="red" />
      </div>

      <div className="cta-row">
        <Link className="btn-enter" to="/map">
          ENTER THE CHAMBER
          <span className="arrow">→</span>
        </Link>
        <a className="btn-source" href="https://www.myneta.info/" target="_blank" rel="noreferrer">
          ↗ DATA SOURCE
        </a>
      </div>

      <p className="disclaimer">
        All data sourced from self-declared ECI affidavits (2024 General Election)
        <br />
        via myneta.info / ADR. Information is public domain. Cases are pending
        <br />
        unless marked convicted. This tool does not claim legal accuracy.
      </p>
    </div>
  )
}
