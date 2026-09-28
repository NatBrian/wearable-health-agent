"""Service layer providing all public application operations."""

from wha.errors import (
    ConfigError,
    SourceUnavailable,
)

# Re-exported so the CLI can name a passage's source without importing below the
# service layer, which its own boundary test forbids.
from wha.retrieve.attribution import source_label
from wha.service.audit import (
    count_audit_events,
    export_audit,
    get_permitted_tool_names,
    list_plain_records,
    query_audit,
    verify_hash_chain,
)
from wha.service.belief import (
    BeliefNightRecord,
    explain_belief,
    get_knowledge_provenance,
    get_knowledge_provenance_summary,
    get_safety_rule_provenance,
)
from wha.service.conversation import (
    acknowledge_urgency,
    get_conversation_sessions,
    get_transcript,
    latest_urgency,
    latest_urgency_reason,
    send_message,
    urgency_banner,
)
from wha.service.corpus import (
    build_corpus_file,
    search_corpus,
)
from wha.service.dashboard import get_dashboard_configuration
from wha.service.data_fetch import fetch_data
from wha.service.demo import (
    DEMO_DB_PATH,
    DemoRunResult,
    run_demo,
)
from wha.service.doctor import (
    DoctorItem,
    run_doctor,
)
from wha.service.episodes import (
    get_episode,
    get_pending_interaction,
    list_episodes,
    step_episode,
    submit_answer,
    submit_human_decision,
    submit_measurement_done,
)
from wha.service.evaluation import (
    get_evaluation_results,
    run_evaluation_suite,
    write_evaluation_report,
)
from wha.service.handover import Handover, build_handover
from wha.service.ingest import DEFAULT_INGEST_DAYS, describe_device_capability, run_ingest
from wha.service.nightly import (
    get_monitoring_since,
    parse_date_range,
    run_nightly,
)
from wha.service.nights import (
    filter_history_nights,
    get_dashboard_summary,
    get_night_detail,
    latest_recorded_night,
    list_nights,
    list_oxygen_readings,
)
from wha.service.pipeline import (
    get_night_pipeline,
    list_pipeline_nights,
)
from wha.service.scheduler import (
    create_scheduler,
    run_episode_tick,
)
from wha.service.settings import (
    delete_all_subject_data,
    get_service_settings,
    get_subject_profile,
    update_settings,
    update_subject_profile,
)
from wha.service.status import (
    get_system_status,
    record_component_status,
    test_bridge_connection,
    test_llm_connection,
    test_telegram_connection,
)
from wha.service.subjects import (
    list_subjects,
)
from wha.service.symptom_report import SymptomReportResult, report_symptoms

__all__ = [
    "DEFAULT_INGEST_DAYS",
    "DEMO_DB_PATH",
    "BeliefNightRecord",
    "ConfigError",
    "DemoRunResult",
    "DoctorItem",
    "Handover",
    "SourceUnavailable",
    "SymptomReportResult",
    "acknowledge_urgency",
    "build_corpus_file",
    "build_handover",
    "count_audit_events",
    "create_scheduler",
    "delete_all_subject_data",
    "describe_device_capability",
    "explain_belief",
    "export_audit",
    "fetch_data",
    "filter_history_nights",
    "get_conversation_sessions",
    "get_dashboard_configuration",
    "get_dashboard_summary",
    "get_episode",
    "get_evaluation_results",
    "get_knowledge_provenance",
    "get_knowledge_provenance_summary",
    "get_monitoring_since",
    "get_night_detail",
    "get_night_pipeline",
    "get_pending_interaction",
    "get_permitted_tool_names",
    "get_safety_rule_provenance",
    "get_service_settings",
    "get_subject_profile",
    "get_system_status",
    "get_transcript",
    "latest_recorded_night",
    "latest_urgency",
    "latest_urgency_reason",
    "list_episodes",
    "list_nights",
    "list_oxygen_readings",
    "list_pipeline_nights",
    "list_plain_records",
    "list_subjects",
    "parse_date_range",
    "query_audit",
    "record_component_status",
    "report_symptoms",
    "run_demo",
    "run_doctor",
    "run_episode_tick",
    "run_evaluation_suite",
    "run_ingest",
    "run_nightly",
    "search_corpus",
    "send_message",
    "source_label",
    "step_episode",
    "submit_answer",
    "submit_human_decision",
    "submit_measurement_done",
    "test_bridge_connection",
    "test_llm_connection",
    "test_telegram_connection",
    "update_settings",
    "update_subject_profile",
    "urgency_banner",
    "verify_hash_chain",
    "write_evaluation_report",
]
