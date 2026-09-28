import { LEGACY_VISIBLE_LITERALS } from './legacyVisibleLiteralInventory'

export interface ParityItem {
  id: string
  source: string
  anchor: string
  destination: string
  verification: string
}

const HOME = 'HomeView'
const TODAY = 'TodayView'
const HISTORY = 'HistoryView'
const RECORD = 'RecordView'
const SETTINGS = 'SettingsView'

export const LEGACY_EXPLANATION_KEYS = [
  'home.what_it_is', 'home.emergency', 'home.can', 'home.cannot', 'home.judging',
  'home.provenance', 'home.nav.today', 'home.nav.history', 'home.nav.audit', 'home.nav.settings',
  'level.GREEN', 'level.YELLOW', 'level.RED', 'level.immature_note', 'level.NA',
  'level.GREEN.next', 'level.YELLOW.next', 'level.RED.next', 'level.NA.next', 'level.investigating',
  'safety.no_local_guidance', 'safety.what_it_cannot_catch', 'level.not_a_diagnosis',
  'rung.COLD', 'rung.PRIOR_DOMINATED', 'rung.SHRINKING', 'rung.PERSONAL', 'rung.MATURE',
  'metric.rhr', 'metric.baseline', 'metric.band', 'metric.gap', 'metric.sleep_hours', 'metric.coverage',
  'metric.window_source.sleep', 'metric.window_source.clock', 'chart.how_to_read',
  'citation.what_this_means', 'citation.quote_missing', 'pipeline.how_to_read', 'pipeline.unrecorded',
  'step.collect.what', 'step.collect.why', 'step.store.what', 'step.store.why',
  'step.sleep_window.what', 'step.sleep_window.why', 'step.features.what', 'step.features.why',
  'step.baseline.what', 'step.baseline.why', 'step.subtract_explained.what', 'step.subtract_explained.why',
  'step.detect.what', 'step.detect.why', 'step.safety_floor.what', 'step.safety_floor.why',
  'step.episode_open.what', 'step.episode_open.why', 'step.preload.what', 'step.preload.why',
  'step.investigate.what', 'step.investigate.why', 'step.believe.what', 'step.believe.why',
  'step.decide.what', 'step.decide.why', 'step.ask.what', 'step.ask.why',
  'step.answer.what', 'step.answer.why', 'step.conclude.what', 'step.conclude.why',
  'step.critique.what', 'step.critique.why', 'step.review.what', 'step.review.why',
  'step.deliver.what', 'step.deliver.why', 'step.safety_phrase_rules.what', 'step.safety_phrase_rules.why',
  'step.safety_triage.what', 'step.safety_triage.why', 'record.what_it_is', 'record.empty',
  'handover.what_it_is', 'status.what_it_is',
] as const

function destinationForExplanation(key: string): string {
  if (key.startsWith('home.')) return `${HOME} / navigation and landing disclosures`
  if (key.startsWith('level.') || key.startsWith('rung.') || key.startsWith('metric.') || key.startsWith('safety.')) {
    return `${TODAY} / ${HISTORY} / VerdictPanel`
  }
  if (key.startsWith('chart.')) return `${HISTORY} / HistoryChart`
  if (key.startsWith('citation.')) return `${TODAY} / CitationPanel`
  if (key.startsWith('pipeline.') || key.startsWith('step.')) return `${RECORD} / PipelineStepDetail / HowItWorks`
  if (key.startsWith('record.')) return `${RECORD} / audit record`
  if (key.startsWith('handover.')) return `${TODAY} / handover summary`
  return 'StatusBar'
}

export const EXPLANATION_ITEMS: ParityItem[] = LEGACY_EXPLANATION_KEYS.map((key) => ({
  id: key,
  source: 'src/wha/ui/explain.py',
  anchor: `TEXT[${JSON.stringify(key)}]`,
  destination: destinationForExplanation(key),
  verification: `copy:${key}`,
}))

const disclosureDestinations: Record<string, string> = {
  'Not a medical device; cannot diagnose': `${HOME} / standing disclaimer`,
  'Needs 7 nights before it can alert at all': `${HOME} / ${TODAY} / ${HISTORY} baseline maturity`,
  'Compares against your own median, not an average adult': `${HISTORY} / chart explanation / baseline source in ${RECORD}`,
  'A repeat notice can follow worsening or a sustained reading that has not improved': `${TODAY} / conversation and notification limits`,
  'Dizziness and light-headedness raise no alarm on their own, but are now tracked over time': `${TODAY} / ${RECORD} safety explanation`,
  'Two symptoms count as co-occurring within 2 nights of each other': `${RECORD} / safety step detail`,
  "A symptom's run ends after 7 days of silence, or when you say it has gone": `${RECORD} / safety step detail`,
  'At most 3 symptom follow-ups per investigation': `${RECORD} / question decision explanation`,
  'A recurrence within 7 days is treated as the same illness, not a new one': `${HISTORY} / linked investigation / ${RECORD}`,
  'Green nights do not close an investigation while a symptom is outstanding': `${RECORD} / HowItWorks safety topic`,
  'A long run of mildly raised nights opens nothing': `${RECORD} / HowItWorks detection topic`,
  'The system holds no guidance about any specific illness, including ones common where the user lives': `${TODAY} / VerdictPanel safety note`,
  'Symptom phrases are matched exactly, so unusual wording can be missed': `${RECORD} / HowItWorks safety topic`,
  'Only a *raised* heart rate is investigated': `${HOME} / ${HISTORY} chart notes`,
  'Naps are excluded': `${HOME} / ${HISTORY} chart notes`,
  'Sleep apnoea cannot be detected': `${HOME} / ${HISTORY} chart notes`,
  'Only sleep heart rate is used; waking heart rate never is': `${HISTORY} / chart notes / sleep-window source in ${RECORD}`,
  'Measured over recorded sleep, with a clock fallback': `${HISTORY} / chart caption / Record night detail`,
  'The starting range is a population figure': `${HISTORY} / chart notes / baseline source in ${RECORD}`,
  'Nights with no reading are not judged': `${TODAY} / measurement state`,
  'General health information comes from MedlinePlus, is about a condition in general, and is never about you': `${TODAY} / CitationPanel attribution`,
  'The likelihood behind every question is assumed, not measured': `${RECORD} / HowItWorks and question-value detail`,
  '**Several causes rest on a guess, and which ones is now shown**': `${TODAY} / per-cause provenance`,
  '**The clinical tables were generated by a language model, not written by a person**': `${RECORD} / HowItWorks and ${TODAY} / cause provenance`,
  '**The uncited labelling is done by the AI and can miss things**': `${TODAY} / uncited response caption`,
  '**Blood oxygen thresholds come from a pathway for people already diagnosed with COVID-19**': `${TODAY} / oxygen result context`,
  'Pulse oximeters overestimate oxygen saturation for everybody, not only for darker skin': `${TODAY} / every oxygen result`,
  '**The Chronos forecast is not part of the current pipeline**': `${RECORD} / HowItWorks current architecture`,
  "Whether a cause is 'large enough' to explain a night is a presentation rule, not a clinical one": `${RECORD} / HowItWorks`,
  'A chest pain report is assessed by questions, not by matching the words': `${TODAY} / question rationale and source`,
  'Some presentations still escalate with no questions at all, on purpose': `${TODAY} / escalation and handover recommendation`,
  'The AI may say things with no source behind them, and they are labelled as such': `${TODAY} / uncited response panel`,
  'The labelling of uncited content is best effort, not guaranteed': `${TODAY} / conversation caption`,
  '**A sentence with a source shown can still misdescribe that source**': `${TODAY} / CitationPanel limitation`,
  'The AI can never make anything less urgent': `${TODAY} / urgency and conversation caption`,
  'Conversation length and weekly unsolicited interruptions use configured limits': `${TODAY} / conversation and notification limits`,
  'Blood oxygen can raise urgency but never lowers it, and cannot say what is wrong': `${TODAY} / oxygen rule and source`,
  'Blood oxygen readings are biased HIGH, and by more on darker skin': `${TODAY} / every oxygen result`,
  'Blood oxygen says nothing at all unless the watch recorded a night of it': `${TODAY} / oxygen no-opinion state`,
  'A question that is asked and never answered leaves the episode UNRESOLVED, not benign': `${HISTORY} / investigation outcome`,
  'If it cannot establish enough to run the rule within three replies, it escalates anyway': `${TODAY} / cautious escalation`,
}

export const DISCLOSURE_ITEMS: ParityItem[] = Object.entries(disclosureDestinations).map(([title, destination]) => ({
  id: title,
  source: 'docs/DISCLOSURES.md',
  anchor: `limitation row: ${title}`,
  destination,
  verification: `disclosure:${title}`,
}))

export const VISIBLE_LITERAL_SURFACES: ParityItem[] = [
  ['src/wha/ui/Home.py', 'page title, welcome text, emergency banner, subject state, evidence summary, navigation labels', HOME],
  ['src/wha/ui/pages/1_Today.py', 'page title, metric labels, night/status messages, oxygen, pending question, review, handover controls', TODAY],
  ['src/wha/ui/pages/2_History.py', 'page title, time window, filters, table headings, empty states, trace action', HISTORY],
  ['src/wha/ui/pages/3_The_record.py', 'page title, record tabs, night selector, integrity, event filters, export, conversation archive', RECORD],
  ['src/wha/ui/pages/4_Settings.py', 'profile, bridge, model, notification, budgets, diagnostics, deletion, save actions', SETTINGS],
  ['src/wha/ui/components/api.py', 'connection and request error messages', 'shared API error state'],
  ['src/wha/ui/components/chat.py', 'chat title, send action, source count, uncited warning, limitations, urgency context', 'ChatPanel'],
  ['src/wha/ui/components/citations.py', 'source title, attribution, quote status, passage open/close labels', 'CitationPanel'],
  ['src/wha/ui/components/how_it_works.py', 'topic headings, explanatory prose, safety provenance table, assumed-value warnings, data destinations', 'HowItWorks'],
  ['src/wha/ui/components/night_chart.py', 'chart title, empty states, chart explanation and accessible point labels', 'HistoryChart'],
  ['src/wha/ui/components/pipeline_graph.py', 'layer/status labels, pipeline help, safety-floor caption, step selection', 'PipelineTrace'],
  ['src/wha/ui/components/status_bar.py', 'service, ingest, scheduler, baseline and freshness states', 'StatusBar'],
  ['src/wha/ui/components/step_detail.py', 'step detail headings, symptom timeline, causes, questions, sources, raw record', 'PipelineStepDetail'],
  ['src/wha/ui/components/subject.py', 'subject selection, loading, unavailable, and error messages', 'SubjectSelector'],
  ['src/wha/ui/components/verdict.py', 'verdict, next step, safety notes, oxygen caveat and per-reading explanations', 'VerdictPanel'],
  ['src/wha/ui/design.py', 'visible shared component text and design-generated labels', 'shared components'],
  ['src/wha/ui/format.py', 'user-visible status and missing-value labels', 'format helpers'],
  ['src/wha/ui/explain.py', 'all stable explanatory text keys', 'legacyCopy catalog'],
].map(([source, anchor, destination]) => ({
  id: source,
  source,
  anchor,
  destination,
  verification: `surface:${source}`,
}))

export const LEGACY_TEST_ASSERTION_MAP: ParityItem[] = [
  ['tests/ui/test_audit_pipeline.py', 'pipeline ordering, labels and visible detail', 'RecordView / PipelineTrace'],
  ['tests/ui/test_audit_record.py', 'integrity outcomes, event filtering and export', 'RecordView / AuditTable'],
  ['tests/ui/test_citations.py', 'citation labels, source drawer and missing quote', 'TodayView / CitationPanel'],
  ['tests/ui/test_history.py', 'window, filters, table, empty states and selected-night trace', 'HistoryView'],
  ['tests/ui/test_settings.py', 'profile/settings fields, save, diagnostics and deletion', 'SettingsView'],
  ['tests/ui/test_shell.py', 'navigation, subject selection, status and Home disclosures', 'DashboardShell / HomeView'],
  ['tests/ui/test_today.py', 'verdict, pending work, chat, oxygen and handover', 'TodayView'],
  ['tests/ui/test_ui_boundary.py', 'API-only data access and formatting boundary', 'api.ts / service API'],
  ['tests/unit/ui/test_citation_labels.py', 'source attribution labels', 'CitationPanel'],
  ['tests/unit/ui/test_client_results_are_used_as_returned.py', 'client does not reinterpret service results', 'api.ts / view formatting'],
  ['tests/unit/ui/test_wording_never_say.py', 'copy avoids forbidden reassurance wording', 'legacyCopy catalog'],
].map(([source, anchor, destination]) => ({
  id: source,
  source,
  anchor,
  destination,
  verification: `ported:${source}`,
}))

export const PARITY_INVENTORY = [
  ...EXPLANATION_ITEMS,
  ...DISCLOSURE_ITEMS,
  ...VISIBLE_LITERAL_SURFACES,
  ...LEGACY_VISIBLE_LITERALS,
  ...LEGACY_TEST_ASSERTION_MAP,
]
