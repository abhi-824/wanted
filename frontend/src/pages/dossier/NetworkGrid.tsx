interface NetworkPerson {
  name: string
  rel: string
}

interface NetworkGridProps {
  people: NetworkPerson[]
}

export default function NetworkGrid({ people }: NetworkGridProps) {
  return (
    <div className="animate-in stagger-5">
      <div className="section-title">// connections & influence network</div>
      <div className="network-grid">
        {people.map((p) => (
          <div className="person-chip" key={`${p.rel}-${p.name}`}>
            <div className="person-chip-name">{p.name}</div>
            <div className="person-chip-rel">{p.rel}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
