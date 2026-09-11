package dev.wha.app.core

import android.content.Context
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.JsonElement

interface WhaCore {
    suspend fun config(): WhaResult<Map<String, JsonElement>>
    suspend fun wording(): WhaResult<Map<String, String>>
    suspend fun lineage(): WhaResult<List<LineageEdge>>
    suspend fun status(subject: String): WhaResult<SystemStatus>
    suspend fun urgency(subject: String): WhaResult<Urgency>
    suspend fun acknowledgeUrgency(subject: String): WhaResult<Map<String, JsonElement>>
    suspend fun nights(subject: String, days: Int): WhaResult<List<NightRow>>
    suspend fun night(subject: String, date: String): WhaResult<NightDetail?>
    suspend fun pipelineNights(subject: String, days: Int): WhaResult<List<PipelineNightRef>>
    suspend fun nightPipeline(subject: String, date: String): WhaResult<NightPipeline>
    suspend fun episodes(subject: String): WhaResult<List<EpisodeSummary>>
    suspend fun episode(id: String): WhaResult<EpisodeDetail>
    suspend fun pending(subject: String): WhaResult<PendingInteraction?>
    suspend fun answer(episodeId: String, probeId: String, optionId: String?, freeText: String?, declined: Boolean): WhaResult<Recorded>
    suspend fun review(episodeId: String, decision: String, editedProse: String?, rationale: String?): WhaResult<Recorded>
    suspend fun handover(subject: String, episodeId: String?): WhaResult<Handover>
    suspend fun conversation(subject: String, limit: Int): WhaResult<List<Turn>>
    suspend fun say(subject: String, text: String, episodeId: String?): WhaResult<SayResult>
    suspend fun audit(subject: String, limit: Int, offset: Int): WhaResult<AuditPage>
    suspend fun auditExport(subject: String): WhaResult<Exported>
    suspend fun settings(): WhaResult<ServiceSettings>
    suspend fun updateSettings(patchJson: String): WhaResult<JsonElement>
    suspend fun knowledgeProvenance(): WhaResult<Map<String, Map<String, String>>>
    suspend fun safetyProvenance(): WhaResult<List<Map<String, String>>>
    suspend fun diagnose(component: String, overridesJson: String): WhaResult<JsonElement>
    suspend fun doctor(): WhaResult<List<DoctorRow>>
    suspend fun retrievalReady(): WhaResult<Ready>
    suspend fun fetchCorpus(): WhaResult<Message>
    suspend fun runIngest(): WhaResult<JobResult>
    suspend fun runNightly(): WhaResult<JobResult>
    suspend fun runEpisodeTick(): WhaResult<JobResult>
    suspend fun runStartupCatchup(): WhaResult<JobResult>
}

class PythonWhaCore(private val context: Context) : WhaCore {
    private val facade by lazy { PythonBoot.ensureStarted(context) }
    private suspend inline fun <reified T> call(name: String, vararg args: Any?): WhaResult<T> =
        withContext(Dispatchers.IO) { WhaResult.parse(facade.callAttr(name, *args).toString()) }

    override suspend fun config() = call<Map<String, JsonElement>>("config")
    override suspend fun wording() = call<Map<String, String>>("wording")
    override suspend fun lineage() = call<List<LineageEdge>>("lineage")
    override suspend fun status(subject: String) = call<SystemStatus>("status", subject)
    override suspend fun urgency(subject: String) = call<Urgency>("urgency", subject)
    override suspend fun acknowledgeUrgency(subject: String) = call<Map<String, JsonElement>>("acknowledge_urgency", subject)
    override suspend fun nights(subject: String, days: Int) = call<List<NightRow>>("nights", subject, days)
    override suspend fun night(subject: String, date: String) = call<NightDetail?>("night", subject, date)
    override suspend fun pipelineNights(subject: String, days: Int) = call<List<PipelineNightRef>>("pipeline_nights", subject, days)
    override suspend fun nightPipeline(subject: String, date: String) = call<NightPipeline>("night_pipeline", subject, date)
    override suspend fun episodes(subject: String) = call<List<EpisodeSummary>>("episodes", subject)
    override suspend fun episode(id: String) = call<EpisodeDetail>("episode", id)
    override suspend fun pending(subject: String) = call<PendingInteraction?>("pending", subject)
    override suspend fun answer(episodeId: String, probeId: String, optionId: String?, freeText: String?, declined: Boolean) =
        call<Recorded>("answer", episodeId, probeId, optionId, freeText, declined)
    override suspend fun review(episodeId: String, decision: String, editedProse: String?, rationale: String?) =
        call<Recorded>("review", episodeId, decision, editedProse, rationale)
    override suspend fun handover(subject: String, episodeId: String?) = call<Handover>("handover", subject, episodeId)
    override suspend fun conversation(subject: String, limit: Int) = call<List<Turn>>("conversation", subject, limit)
    override suspend fun say(subject: String, text: String, episodeId: String?) = call<SayResult>("say", subject, text, episodeId)
    override suspend fun audit(subject: String, limit: Int, offset: Int) = call<AuditPage>("audit", subject, limit, offset)
    override suspend fun auditExport(subject: String) = call<Exported>("audit_export", subject)
    override suspend fun settings() = call<ServiceSettings>("settings")
    override suspend fun updateSettings(patchJson: String) = call<JsonElement>("update_settings", patchJson)
    override suspend fun knowledgeProvenance() = call<Map<String, Map<String, String>>>("knowledge_provenance")
    override suspend fun safetyProvenance() = call<List<Map<String, String>>>("safety_provenance")
    override suspend fun diagnose(component: String, overridesJson: String) = call<JsonElement>("diagnose", component, overridesJson)
    override suspend fun doctor() = call<List<DoctorRow>>("doctor")
    override suspend fun retrievalReady() = call<Ready>("retrieval_ready")
    override suspend fun fetchCorpus() = call<Message>("fetch_corpus")
    override suspend fun runIngest() = call<JobResult>("run_ingest")
    override suspend fun runNightly() = call<JobResult>("run_nightly")
    override suspend fun runEpisodeTick() = call<JobResult>("run_episode_tick")
    override suspend fun runStartupCatchup() = call<JobResult>("run_startup_catchup")
}
