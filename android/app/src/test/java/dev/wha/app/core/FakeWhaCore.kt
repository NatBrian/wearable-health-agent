package dev.wha.app.core

import kotlinx.serialization.json.JsonElement

/**
 * A WhaCore holding canned JSON per method name, for view model tests. Records calls
 * in order. Every view model test uses this instead of Python.
 */
class FakeWhaCore : WhaCore {
    val canned: MutableMap<String, String> = mutableMapOf()
    val calls: MutableList<String> = mutableListOf()

    private suspend inline fun <reified T> cannedAs(name: String): WhaResult<T> {
        calls.add(name)
        val raw = canned[name] ?: error("FakeWhaCore has no canned JSON for $name")
        return WhaResult.parse(raw)
    }

    override suspend fun config(): WhaResult<Map<String, JsonElement>> = cannedAs("config")
    override suspend fun wording(): WhaResult<Map<String, String>> = cannedAs("wording")
    override suspend fun lineage(): WhaResult<List<LineageEdge>> = cannedAs("lineage")
    override suspend fun status(subject: String): WhaResult<SystemStatus> = cannedAs("status")
    override suspend fun urgency(subject: String): WhaResult<Urgency> = cannedAs("urgency")
    override suspend fun acknowledgeUrgency(subject: String): WhaResult<Map<String, JsonElement>> = cannedAs("acknowledge_urgency")
    override suspend fun nights(subject: String, days: Int): WhaResult<List<NightRow>> = cannedAs("nights")
    override suspend fun night(subject: String, date: String): WhaResult<NightDetail?> = cannedAs("night")
    override suspend fun pipelineNights(subject: String, days: Int): WhaResult<List<PipelineNightRef>> = cannedAs("pipeline_nights")
    override suspend fun nightPipeline(subject: String, date: String): WhaResult<NightPipeline> = cannedAs("night_pipeline")
    override suspend fun episodes(subject: String): WhaResult<List<EpisodeSummary>> = cannedAs("episodes")
    override suspend fun episode(id: String): WhaResult<EpisodeDetail> = cannedAs("episode")
    override suspend fun pending(subject: String): WhaResult<PendingInteraction?> = cannedAs("pending")
    override suspend fun answer(episodeId: String, probeId: String, optionId: String?, freeText: String?, declined: Boolean): WhaResult<Recorded> = cannedAs("answer")
    override suspend fun review(episodeId: String, decision: String, editedProse: String?, rationale: String?): WhaResult<Recorded> = cannedAs("review")
    override suspend fun handover(subject: String, episodeId: String?): WhaResult<Handover> = cannedAs("handover")
    override suspend fun conversation(subject: String, limit: Int): WhaResult<List<Turn>> = cannedAs("conversation")
    override suspend fun say(subject: String, text: String, episodeId: String?): WhaResult<SayResult> = cannedAs("say")
    override suspend fun audit(subject: String, limit: Int, offset: Int): WhaResult<AuditPage> = cannedAs("audit")
    override suspend fun auditExport(subject: String): WhaResult<Exported> = cannedAs("audit_export")
    override suspend fun settings(): WhaResult<ServiceSettings> = cannedAs("settings")
    override suspend fun updateSettings(patchJson: String): WhaResult<JsonElement> = cannedAs("update_settings")
    override suspend fun knowledgeProvenance(): WhaResult<Map<String, Map<String, String>>> = cannedAs("knowledge_provenance")
    override suspend fun safetyProvenance(): WhaResult<List<Map<String, String>>> = cannedAs("safety_provenance")
    override suspend fun diagnose(component: String, overridesJson: String): WhaResult<JsonElement> = cannedAs("diagnose")
    override suspend fun doctor(): WhaResult<List<DoctorRow>> = cannedAs("doctor")
    override suspend fun retrievalReady(): WhaResult<Ready> = cannedAs("retrieval_ready")
    override suspend fun fetchCorpus(): WhaResult<Message> = cannedAs("fetch_corpus")
    override suspend fun runIngest(): WhaResult<JobResult> = cannedAs("run_ingest")
    override suspend fun runNightly(): WhaResult<JobResult> = cannedAs("run_nightly")
    override suspend fun runEpisodeTick(): WhaResult<JobResult> = cannedAs("run_episode_tick")
    override suspend fun runStartupCatchup(): WhaResult<JobResult> = cannedAs("run_startup_catchup")
}
