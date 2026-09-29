import { CAUSE_LABELS } from '../api'
import type { BackendData } from '../useBackend'
import { dateLabel, measuredValue } from '../lib/format'

const layers = [
  {
    id: 'detection', title: 'Detection layer', tone: 'detection',
    summary: 'Measures each night against the person’s own baseline.',
    details: [
      'Checks whether a night has enough usable watch data.',
      'Accounts for recorded exercise before comparing the remaining heart-rate signal with the baseline.',
      'Uses a persistence rule before opening an investigation.',
    ],
  },
  {
    id: 'reasoning', title: 'Reasoning layer', tone: 'reasoning',
    summary: 'Updates possible explanations from the available evidence.',
    details: [
      'Keeps a probability for each supported cause in the differential.',
      'Uses an expected-value-of-information policy to decide whether a question is useful enough to ask.',
      'The model can write language; it cannot lower the deterministic safety floor.',
    ],
  },
  {
    id: 'retrieval', title: 'Retrieval layer', tone: 'retrieval',
    summary: 'Connects generated clinical statements to named source passages.',
    details: [
      'Screens retrieved material before it reaches the model and names sources where they are shown.',
      'Checks that supported clinical statements contain a verbatim span from a retrieved passage.',
      'That check proves the span exists; it does not prove the surrounding sentence is fair to the source.',
    ],
  },
] as const

function provenanceTone(provenance: string): string {
  switch (provenance.trim().toUpperCase()) {
    case 'CITED': return 'cited'
    case 'ASSUMED': return 'assumed'
    case 'DERIVED': return 'derived'
    default: return 'unknown'
  }
}

export function PipelineOverview({ data, timezone }: { data: BackendData; timezone: string }) {
  const episode = data.activeEpisode?.summary ?? data.episodes[0] ?? null
  const episodeContext = !episode ? 'System context' : episode.state === 'CLOSED' ? 'Most recent investigation' : 'Live system context'
  const rules = data.safetyRules
  const causes = data.activeEpisode?.belief_history.at(-1)?.[2].marginals
  const beliefTopCause = causes
    ? (Object.entries(causes) as [keyof typeof CAUSE_LABELS, number][]).sort((left, right) => right[1] - left[1])[0]
    : null
  const topCause = beliefTopCause ?? (episode?.top_cause && episode.top_probability !== null
    ? [episode.top_cause, episode.top_probability] as const
    : null)
  const causeContext = episode?.state === 'CLOSED' ? 'Leading cause in last recorded belief' : 'Leading cause in current belief'

  return (
    <div className="page-stack pipeline-overview">
      <section className="pipeline-layers" aria-label="Pipeline architecture">
        {layers.map((layer) => <article className={`pipeline-layer pipeline-layer--${layer.tone}`} key={layer.id}>
          <span className="eyebrow">{layer.id} layer</span>
          <h2>{layer.title}</h2>
          <p>{layer.summary}</p>
          <ul>{layer.details.map((detail) => <li key={detail}>{detail}</li>)}</ul>
        </article>)}
      </section>

      <section className="content-card episode-summary" aria-labelledby="pipeline-episode-title">
        <div className="section-heading"><div><span className="eyebrow">{episodeContext}</span><h2 id="pipeline-episode-title">Investigation summary</h2></div>{episode && <span className="level-pill level-na">{episode.state.replace(/_/g, ' ')}</span>}</div>
        {data.errors.activeEpisode ? <p className="inline-notice inline-notice--warning" role="alert">The current investigation could not be loaded. This is a fetch failure, not an empty history. {data.errors.activeEpisode}</p> : !episode ? <p>{data.episodes.length === 0 ? 'No investigation has been recorded.' : 'No investigation summary is available.'}</p> : <>
          <dl className="episode-summary__facts">
            <div><dt>Investigation</dt><dd>{episode.episode_id}</dd></div>
            <div><dt>Night span</dt><dd>{dateLabel(episode.night_span[0], timezone)} to {dateLabel(episode.night_span[1], timezone)}</dd></div>
            <div><dt>Opened</dt><dd>{dateLabel(episode.opened_on, timezone)}</dd></div>
            {episode.closed_on && <div><dt>Closed</dt><dd>{dateLabel(episode.closed_on, timezone)}</dd></div>}
            {topCause && <div><dt>{causeContext}</dt><dd>{CAUSE_LABELS[topCause[0]]} · {measuredValue(topCause[1] * 100, '%')}</dd></div>}
          </dl>
          {data.activeEpisode && <div className="pipeline-stage-list" aria-label="Investigation-wide stage status">
            <p className="supporting-copy">These stages describe the investigation as a whole, not one selected night.</p>
            {data.activeEpisode.stages.length > 0 ? data.activeEpisode.stages.map((stage) => <article key={stage.name}>
              <strong>{stage.name.replace(/_/g, ' ')}</strong><span>{stage.status}</span><p>{stage.reason}</p>
            </article>) : <p>No episode stages are recorded in this response.</p>}
          </div>}
        </>}
      </section>

      <section className="content-card safety-provenance" aria-labelledby="safety-provenance-title">
        <div className="section-heading"><div><span className="eyebrow">Deterministic safety layer</span><h2 id="safety-provenance-title">Safety rule provenance</h2></div></div>
        <p>These rules can raise urgency. The model cannot switch them off or lower their result.</p>
        {data.errors.safetyRules ? <p className="inline-notice inline-notice--warning" role="alert">Safety rule details could not be loaded. This is a fetch failure, not an empty rule set. {data.errors.safetyRules}</p> : rules.length === 0 ? <p>No safety rule details are available in this response.</p> : <div className="table-scroll" role="region" aria-label="Safety rule sources" tabIndex={0}>
          <table className="history-table"><thead><tr><th>Rule</th><th>Value</th><th>Source status</th><th>Basis and population scope</th></tr></thead><tbody>
            {rules.map((rule, index) => <tr key={`${rule.rule}-${rule.number}-${index}`}><td>{rule.rule}</td><td>{rule.number}</td><td><span className={`provenance-badge provenance-badge--${provenanceTone(rule.provenance)}`}>{rule.provenance}</span></td><td>{rule.basis}</td></tr>)}
          </tbody></table>
        </div>}
      </section>
    </div>
  )
}
