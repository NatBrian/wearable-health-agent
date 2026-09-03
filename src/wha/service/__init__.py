"""Service layer providing all public application operations."""

from wha.errors import (
    ConfigError,
    SourceUnavailable,
)
from wha.service.audit import (
    export_audit,
    get_permitted_tool_names,
    list_plain_records,
    query_audit,
    verify_hash_chain,
)
from wha.service.belief import (
    BeliefNightRecord,
    explain_belief,
)
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
    ask_about_episode,
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
from wha.service.ingest import DEFAULT_INGEST_DAYS, describe_device_capability, run_ingest
from wha.service.nightly import (
    get_monitoring_since,
    parse_date_range,
    run_nightly,
)
from wha.service.nights import (
    get_night_detail,
    list_nights,
)
from wha.service.scheduler import (
    create_scheduler,
    run_episode_tick,
)
from wha.service.settings import (
    delete_all_subject_data,
    get_service_settings,
    update_settings,
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
    "SourceUnavailable",
    "SymptomReportResult",
    "ask_about_episode",
    "create_scheduler",
    "delete_all_subject_data",
    "describe_device_capability",
    "explain_belief",
    "export_audit",
    "fetch_data",
    "get_episode",
    "get_evaluation_results",
    "get_monitoring_since",
    "get_night_detail",
    "get_pending_interaction",
    "get_permitted_tool_names",
    "get_service_settings",
    "get_system_status",
    "list_episodes",
    "list_nights",
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
    "step_episode",
    "submit_answer",
    "submit_human_decision",
    "submit_measurement_done",
    "test_bridge_connection",
    "test_llm_connection",
    "test_telegram_connection",
    "update_settings",
    "verify_hash_chain",
    "write_evaluation_report",
]
