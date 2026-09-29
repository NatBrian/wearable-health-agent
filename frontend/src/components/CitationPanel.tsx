import { useState } from 'react'
import type { Citation, SystemConfig } from '../api'
import { legacyText } from '../content/legacyCopy'
import { isExternalSource, sourceLabel } from '../lib/format'

const MISSING_SOURCE_STATUS = 'No source or unsupported-content note was attached to this reply. Treat any health information here as unverified.'

export function CitationPanel({
  citations, uncited, config, showMissingStatus = false,
}: {
  citations: Citation[]
  uncited: string[]
  config: SystemConfig
  showMissingStatus?: boolean
}) {
  const [open, setOpen] = useState<string | null>(null)
  const hasExternal = citations.some((citation) => isExternalSource(citation.source_id, config))
  const attribution = typeof config.ATTRIBUTION_NOTE === 'string' ? config.ATTRIBUTION_NOTE : ''
  const missingStatus = showMissingStatus && citations.length === 0 && uncited.length === 0

  return (
    <div className="evidence-stack">
      {missingStatus && (
        <aside className="uncited-warning" aria-label="Source status unavailable">
          <strong>Source status unavailable</strong>
          <p>{MISSING_SOURCE_STATUS}</p>
        </aside>
      )}
      {uncited.length > 0 && (
        <aside className="uncited-warning" aria-label="Not from a cited source">
          <strong>Not from a cited source</strong>
          <p>The following came from the AI's general knowledge, not from anything held in this system. Treat it as a starting point to check.</p>
          <ul>{uncited.map((note, index) => <li key={`${note}-${index}`}>{note}</li>)}</ul>
          <p>The AI sorts cited and uncited content itself and can miss things. An absent warning does not prove a sentence has a source.</p>
        </aside>
      )}
      {citations.length > 0 && (
        <section className="citation-list" aria-label="Sources behind this reply">
          <div className="citation-list__heading">Sources behind this reply <span>{citations.length}</span></div>
          {citations.map((citation, index) => {
            const id = `${citation.source_id}-${index}`
            const expanded = open === id
            const quoteFound = Boolean(citation.quoted_span && citation.passage.includes(citation.quoted_span))
            const quoteMissing = !citation.quoted_span || !quoteFound
            return (
              <article className="citation-card" key={id}>
                <button className="citation-card__toggle" onClick={() => setOpen(expanded ? null : id)} aria-expanded={expanded}>
                  <span><strong>{citation.title || citation.source_id}</strong><small>{sourceLabel(citation.source_id, config)}</small></span>
                  <span aria-hidden="true">{expanded ? '−' : '+'}</span>
                </button>
                {expanded && (
                  <div className="citation-card__detail">
                    <div className="citation-card__source">Source identifier: <code>{citation.source_id}</code></div>
                    {citation.uri && /^https?:\/\//i.test(citation.uri) && <a href={citation.uri} target="_blank" rel="noreferrer">Open source</a>}
                    {quoteMissing && <p className="inline-notice inline-notice--warning">{legacyText('citation.quote_missing')}</p>}
                    {citation.quoted_span && quoteFound && <p className="quoted-span">Quoted words: “{citation.quoted_span}”</p>}
                    <blockquote>{citation.passage}</blockquote>
                    <p className="supporting-copy">{legacyText('citation.what_this_means')}</p>
                  </div>
                )}
              </article>
            )
          })}
          {hasExternal && attribution && <p className="supporting-copy">{attribution}</p>}
        </section>
      )}
    </div>
  )
}
