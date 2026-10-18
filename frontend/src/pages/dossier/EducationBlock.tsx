interface EducationBlockProps {
  educationLevel: string | null
  educationDetails: string | null
  fallbackEducation: string | null
}

export default function EducationBlock({
  educationLevel,
  educationDetails,
  fallbackEducation,
}: EducationBlockProps) {
  const level = educationLevel?.trim() || null
  const details = educationDetails?.trim() || null
  const fallback = fallbackEducation?.trim() || null

  if (!level && !details && !fallback) return null

  return (
    <div className="education-block animate-in stagger-3">
      <div className="section-title">// education</div>
      {level ? <div className="edu-level">{level}</div> : null}
      {details ? <div className="edu-details">{details}</div> : null}
      {!level && !details && fallback ? (
        <div className="edu-details">{fallback}</div>
      ) : null}
    </div>
  )
}
