export function HomeDisclosure({ baselineMinimum }: { baselineMinimum: number }) {
  return (
    <details className="disclosure-card">
      <summary>What the system cannot see or detect</summary>
      <div className="disclosure-card__body">
        <p><strong>It needs {baselineMinimum} nights before it can alert at all.</strong> Until there are enough measured nights, your personal normal is not established.</p>
        <p><strong>Only a raised heart rate is investigated.</strong> A low reading does not open an investigation.</p>
        <p><strong>Naps are excluded.</strong> The system uses the sleep period recorded by your watch.</p>
        <p><strong>Sleep apnoea cannot be detected.</strong> A raised heart rate over time can become part of the personal normal.</p>
        <p>These limits are also explained beside the relevant history and record details.</p>
      </div>
    </details>
  )
}
