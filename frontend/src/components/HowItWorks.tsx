import type { SafetyRuleProvenance, Settings, SystemConfig } from '../api'

export const HOW_IT_WORKS_TOPIC_STEPS: Record<string, string[]> = {
  'Reading the watch': ['collect', 'store', 'sleep_window', 'features'],
  'Learning your normal': ['baseline'],
  'Deciding a night is worth looking at': ['subtract_explained', 'detect'],
  'Checking what you have told us, over time': ['safety_floor'],
  'Opening an investigation, and what the AI may do inside it': ['episode_open', 'preload', 'investigate'],
  'Working out the likely cause': ['believe'],
  'Deciding whether to interrupt you': ['decide', 'ask', 'answer'],
  'Writing the conclusion, and checking it before you see it': ['conclude', 'critique', 'review', 'deliver'],
  'The safety rules, which run before anything else': ['safety_phrase_rules', 'safety_triage'],
  'Where your data goes': [],
}

const STEP_NAMES: Record<string, string> = {
  collect: 'Collect from watch', store: 'Store the readings', sleep_window: 'Find your sleep',
  features: 'One number for the night', baseline: 'Your normal', subtract_explained: 'Subtract what is explained',
  detect: 'Judge the night', safety_floor: 'Check what you told us', episode_open: 'Open an investigation',
  preload: 'Fixed first readings', investigate: 'AI gathers evidence', believe: 'Weigh possible causes',
  decide: 'Worth asking you?', ask: 'Ask you', answer: 'Your answer', conclude: 'Draft a conclusion',
  critique: 'Remove unsourced claims', review: 'A person checks it', deliver: 'Send and save',
  safety_phrase_rules: 'Phrase rules', safety_triage: 'Published checklist',
}

export function HowItWorks({ config, settings, safetyRules, permittedTools }: {
  config: SystemConfig
  settings: Settings | null
  safetyRules: SafetyRuleProvenance[]
  permittedTools: string[]
}) {
  const value = (key: string) => displayConfigValue(config, key)
  const assumed = safetyRules.filter((rule) => rule.provenance.toUpperCase() === 'ASSUMED')
  return (
    <div className="page-stack">
      <section className="content-card how-works-intro"><span className="eyebrow">How the system works</span><h1>Same machinery, grouped by topic</h1><p>The tab beside this one walks one night through every step in the order they run. This is the same machinery grouped by topic, and each heading says which of those steps it covers. Every number below is read from the running system rather than written into this page.</p></section>
      {Object.entries(HOW_IT_WORKS_TOPIC_STEPS).map(([topic, stepIds]) => (
        <details className="how-topic" key={topic} open={topic === 'Opening an investigation, and what the AI may do inside it' || topic === 'Deciding whether to interrupt you'}>
          <summary><span>{topic}</span><small>{stepIds.length ? stepIds.map((id) => STEP_NAMES[id] ?? id).join(' · ') : 'Applies to every step'}</small></summary>
          <div className="how-topic__body">
            {topic === 'Reading the watch' && <>
              <p>The reading is taken over the sleep your watch recorded, because daytime heart rate reflects whatever you were doing. When the watch reports no sleep for a night, the window falls back to midnight to seven in the morning and the night says so.</p>
              <ul><li>At least <strong>{value('MIN_NOCTURNAL_MINUTES')} minutes</strong> of contact are needed, or the night is marked unusable rather than guessed at.</li><li>Readings below <strong>{value('HR_PLAUSIBLE_MIN_BPM')} bpm</strong> or above <strong>{value('HR_PLAUSIBLE_MAX_BPM')} bpm</strong> are treated as sensor error and dropped.</li></ul>
            </>}
            {topic === 'Learning your normal' && <>
              <p>Your baseline is the middle of your recent nights, not an average, so one bad night cannot drag it. Before there are enough of your own readings, the starting range is a population estimate rather than a measured personal normal. The source and population scope are available in the baseline step on The record.</p>
              <div className="table-scroll"><table className="history-table"><thead><tr><th>Baseline stage</th><th>Upper bound in the running system</th><th>What it uses</th></tr></thead><tbody><tr><td>COLD</td><td>{value('RUNG_COLD_MAX_NIGHTS')} nights</td><td>Nothing is judged yet</td></tr><tr><td>PRIOR_DOMINATED</td><td>{value('RUNG_PRIOR_MAX_NIGHTS')} nights</td><td>Mostly typical adults</td></tr><tr><td>SHRINKING</td><td>{value('RUNG_SHRINKING_MAX_NIGHTS')} nights</td><td>A blend</td></tr><tr><td>PERSONAL</td><td>{value('RUNG_PERSONAL_MAX_NIGHTS')} nights</td><td>Mostly you</td></tr><tr><td>MATURE</td><td>No upper bound</td><td>You alone</td></tr></tbody></table></div>
              <p>The measure of your night-to-night spread never goes below <strong>{value('BASELINE_SCALE_FLOOR_BPM')} bpm</strong>. Watches report whole numbers, so a run of identical nights would otherwise give a spread of exactly zero and make every later night look infinitely unusual.</p>
            </>}
            {topic === 'Deciding a night is worth looking at' && <ul><li>Anything a recorded workout would be expected to add is subtracted first.</li><li>What remains is compared with your usual: <strong>{value('DETECT_YELLOW_BPM')} bpm</strong> above is slightly raised, <strong>{value('DETECT_RED_BPM')} bpm</strong> above is clearly raised.</li><li>A single raised night is not enough. It takes <strong>{value('DETECT_PERSISTENCE_NIGHTS')} nights</strong> in a row, both clearly raised, before anything opens. That is what keeps a late drink from starting an investigation, and it is exactly the rule the study these thresholds come from used.</li></ul>}
            {topic === 'Checking what you have told us, over time' && <>
              <p>Anything you say about how you feel is checked against a fixed list of symptoms. This is plain rules, not AI, and it can only ever make the system more cautious, never less.</p>
              <p>Three things can happen, and the first two need a memory of what you have said before rather than just tonight's message:</p>
              <ul><li><strong>One symptom that keeps going.</strong> Each symptom has its own number of nights, and the count runs from the first night you mentioned it. A night you say nothing does not reset it, because going quiet is not the same as getting better. It stops when you say the symptom has gone, or after <strong>{value('SYMPTOM_RUN_GAP_DAYS')} days</strong> with no mention.</li><li><strong>Two symptoms close together.</strong> Two of these within <strong>{value('SYMPTOM_COOCCURRENCE_WINDOW_NIGHTS')} nights</strong> of each other is enough, whether you mentioned them in one message or on different nights. Feeling dizzy on Monday and feverish on Tuesday counts as both.</li><li><strong>A symptom that goes straight to urgent care</strong>, on its own, with no waiting.</li></ul>
              <p>Symptoms with no good evidence behind a rule, such as dizziness, are still written down so the system can ask you about them. Recording something is a much smaller claim than deciding where you should be treated, and it is the honest place for a symptom nobody has measured a threshold for.</p>
              <p>While any symptom of yours is still going, an investigation will not close as “nothing points towards illness”, however settled your heart rate looks. Your readings coming back to normal is evidence about your readings.</p>
            </>}
            {topic === 'Opening an investigation, and what the AI may do inside it' && <>
              <p><strong>When one opens.</strong> Only after <strong>{value('DETECT_PERSISTENCE_NIGHTS')} clearly raised nights in a row</strong>, both of them at that level. A clearly raised night next to a slightly raised one does not open anything, in either order, and slightly raised nights never open anything however many there are. Nothing opens at all until the system has at least <strong>{value('BASELINE_MIN_NIGHTS_PERSONAL')} of your own measured nights</strong>, because before that your normal is still mostly a general estimate.</p>
              <p><strong>What it is.</strong> A single piece of work about one run of raised nights. Only one runs at a time, so a stretch of raised nights is looked at as one thing rather than as a series of separate alarms. It ends by concluding, or by your nights going quiet again.</p>
              <p><strong>Linking a recurrence.</strong> A recurrence within {value('EPISODE_RECURRENCE_LINK_DAYS')} days is linked to the same investigation. This is a record-linking convention, not proof that two episodes are medically the same illness.</p>
              <p><strong>What it does not mean.</strong> It is not a finding, and not a statement that anything is wrong. It means the system thinks the readings are worth explaining, and it is going to try.</p>
              <p>Inside one, the model can only call the following read-only tools, and nothing else. Any other request is refused and recorded:</p>
              {permittedTools.length > 0 ? <ul>{permittedTools.map((tool) => <li key={tool}><code>{tool}</code></li>)}</ul> : <p>The permitted tool list could not be loaded.</p>}
              <p>It cannot write to your record, send you anything, or decide whether to interrupt you.</p>
            </>}
            {topic === 'Working out the likely cause' && <>
              <p>The system tracks <strong>{value('N_CAUSES')} possible causes</strong> at once and considers every combination of them being present or absent, which is {new Intl.NumberFormat().format(config.dashboard.cause_combinations)} possibilities. This is ordinary arithmetic, not a model, so the same evidence always gives the same answer.</p>
              <p>The clinical tables used here were assembled with language-model assistance rather than written by a clinician. Each figure is labelled with its source or with an explicit assumed or derived status. Some cause weights are not measured; their provenance appears beside the cause.</p>
              <p>The cutoff for showing a cause as large enough to explain a night is a presentation rule, not a clinical threshold. The Chronos forecast is not part of this pipeline; its engineering evaluation is recorded in the forecasting experiment archive and is not clinical evidence.</p>
            </>}
            {topic === 'Deciding whether to interrupt you' && <>
              <p>This is the one decision the AI does not make. Before asking anything, the system works out how much the answer could actually change what it does. If that is worth less than the cost of interrupting you, it stays quiet.</p>
              <p><strong>The question likelihoods are assumptions, not measured accuracy.</strong> No study measured how often a person's next-morning answer to this system's question is correct. The value-of-asking score is therefore a policy estimate.</p>
              <p>A symptom follow-up can be asked at most <strong>{value('SYMPTOM_FOLLOWUP_MAX_PER_EPISODE')} times during one investigation</strong>. This limit is assumed, not measured. There is also a hard limit of <strong>{settings?.interruption_budget_per_week ?? 'not available'} unsolicited questions a week</strong>. The weekly cap is a backstop; the expected-value comparison decides whether the question is worth asking.</p>
              <p className="supporting-copy">Project-specific performance measurements belong in the experiment records, with their own caveats.</p>
            </>}
            {topic === 'Writing the conclusion, and checking it before you see it' && <ul><li>Every clinical sentence in a conclusion has to quote a span that really appears in a passage this system holds. A sentence that quotes nothing is removed before you see it.</li><li>The model then reads its own draft back, and at that point it can only remove claims, never add them. This step can make a conclusion smaller and never larger.</li><li>A person approves, edits, rejects or escalates the draft. Nothing reaches you as a settled conclusion without passing that checkpoint.</li><li>What is kept is saved to your record, this dashboard and the tamper-evident log at the same time, so the copy you read is the copy that was kept.</li></ul>}
            {topic === 'Writing the conclusion, and checking it before you see it' && <p><strong>What this check does not do.</strong> It proves the quoted words are really in the passage. It does not prove the sentence built around them describes that passage fairly, so every citation opens to the whole passage for you to read.</p>}
            {topic === 'The safety rules, which run before anything else' && <>
              <p>If you describe certain symptoms in your own words, the system stops and tells you to seek care. That check is plain pattern matching against a fixed list, it runs before any model is consulted, and no amount of model output can switch it off. A language model can only add a flag to that list, never remove one.</p>
              <p>Some presentations have a validated rule that asks questions before it decides. The rule and its source are shown in the table. Other presentations have no suitable rule and escalate without waiting for questions. If a rule cannot be completed within the configured reply limit, the system escalates anyway; that limit is unevidenced.</p>
              {safetyRules.length > 0 ? <div className="table-scroll"><table className="history-table"><thead><tr><th>Rule</th><th>When it fires</th><th>Where its number came from</th><th>Basis</th></tr></thead><tbody>{safetyRules.map((rule) => <tr key={`${rule.rule}-${rule.number}`}><td>{rule.rule}</td><td>{rule.number}</td><td>{rule.provenance === 'ASSUMED' ? 'no published source found' : rule.provenance === 'DERIVED' ? 'worked out from other figures here' : 'a published study'}</td><td>{rule.basis}</td></tr>)}</tbody></table></div> : <p>The safety-rule provenance could not be loaded.</p>}
              {assumed.length > 0 && <p className="inline-notice inline-notice--warning">{assumed.length} of these {safetyRules.length} numbers have no published source behind them, and the table says which. No study was found measuring how many nights a symptom should persist before it is worth a same-day appointment, so those windows were chosen rather than measured. They are set short, which means they err towards sending you to a doctor sooner rather than later. This is disclosed because a number nobody measured must not look the same as one somebody did.</p>}
            </>}
            {topic === 'Where your data goes' && <>
              <p>Readings, nightly figures and the full record stay in a database file on this machine.</p>
              <p>The one exception is the language model. Unless it is set to the offline recorded provider, the text of a question or summary is sent to whichever model endpoint is configured, which may be a remote service. The Settings page shows which is in use.</p>
              {settings && <p className="provider-status">Current model provider: <strong>{settings.llm_provider}</strong>. Model name: <strong>{settings.llm_model}</strong>. Configured endpoint: <strong>{settings.llm_base_url ?? 'not set'}</strong>.</p>}
            </>}
          </div>
        </details>
      ))}
    </div>
  )
}

function displayConfigValue(config: SystemConfig, key: string): string {
  const value = config[key]
  if (typeof value !== 'number') return 'not available'
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 3 }).format(value)
}
