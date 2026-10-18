import { useEffect } from 'react'

import GridBackground from '../../components/GridBackground'
import ChamberPreview from './ChamberPreview'
import Hero from './Hero'
import HowToGuide from './HowToGuide'
import StatusBar from './StatusBar'
import './home.css'

const PAGE_TITLE = 'Neta Check — Know Your Parliament'

export default function HomePage() {
  useEffect(() => {
    const prevTitle = document.title
    const prevOverflow = document.body.style.overflow
    document.title = PAGE_TITLE
    document.body.style.overflow = 'hidden'
    return () => {
      document.title = prevTitle
      document.body.style.overflow = prevOverflow
    }
  }, [])

  return (
    <div className="home-page">
      <GridBackground />
      <div className="corner tl" aria-hidden="true" />
      <div className="corner tr" aria-hidden="true" />
      <div className="corner bl" aria-hidden="true" />
      <div className="corner br" aria-hidden="true" />

      <div className="page">
        <Hero />
        <div className="right">
          <HowToGuide />
          <ChamberPreview />
        </div>
      </div>

      <StatusBar />
    </div>
  )
}
