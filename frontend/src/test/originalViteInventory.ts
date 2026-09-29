export const ORIGINAL_VITE_INVENTORY = {
  shell: {
    brand: 'Vital Agent',
    tagline: 'health triage',
    destinations: ['Dashboard', 'Pipeline', 'Settings'],
    dashboardTitle: 'Health Overview',
    pipelineTitle: 'System Pipeline',
    subjectSummary: 'Selected subject and baseline',
    sessionSummary: 'Session summary',
    openSession: 'Open session',
    lastClosedSession: 'Last closed',
  },
  dashboard: {
    metrics: ['Resting HR', 'Sleep', 'Steps (7d avg)', 'SpO₂'],
    chart: 'Resting HR trend',
    episodeStatus: 'Episode status',
    sleepStreak: 'worsening',
    latestNight: 'Last measured night',
    differential: 'Cause differential',
    differentialChange: 'Change since the investigation opened',
    oxygenSpotChecks: 'Recent oxygen spot checks',
  },
  pipeline: {
    layers: ['Detection layer', 'Reasoning layer', 'Retrieval layer'],
    sections: ['System overview', 'This night, step by step', 'Everything the system did', 'How this works'],
    safetyRules: 'Safety rule provenance',
    nightTrace: 'Night trace',
  },
  settings: {
    sections: ['Device & Data', 'Agent Behavior', 'Model & RAG', 'Privacy'],
  },
  chat: {
    open: 'Open Agent Chat',
    close: 'Close chat',
    panel: 'Agent chat',
    unread: 'Reply waiting',
    citationPanel: 'Sources behind this reply',
  },
} as const
