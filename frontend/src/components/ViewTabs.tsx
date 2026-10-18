import { NavLink } from 'react-router'

function tabClass({ isActive }: { isActive: boolean }) {
  return isActive ? 'view-tab active' : 'view-tab'
}

export default function ViewTabs() {
  return (
    <nav className="view-tabs" aria-label="Primary views">
      <NavLink to="/map" className={tabClass} end>
        MAP
      </NavLink>
      <NavLink to="/parliament" className={tabClass}>
        PARLIAMENT
      </NavLink>
    </nav>
  )
}
