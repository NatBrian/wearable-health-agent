"""Evaluation view rendering precomputed benchmark and validation results."""

from pathlib import Path

import pandas as pd
import streamlit as st

from wha.models import EvaluationResult
from wha.service.evaluation import get_evaluation_results


def render_caveats_and_sample_size(result: EvaluationResult) -> None:
    """Render sample size and explicit caveats for an evaluation panel."""
    st.caption(f"**Sample size (n):** {result.sample_size}")
    if result.caveats:
        for caveat in result.caveats:
            st.warning(f"⚠️ **Caveat:** {caveat}")


def render_detection_panel(eval_dir: Path | None = None) -> None:
    """Render Detection evaluation panel with both mandatory baselines."""
    st.subheader("🎯 Detection Performance & Mandatory Baselines")
    res = get_evaluation_results("detection", eval_dir=eval_dir)
    render_caveats_and_sample_size(res)

    if res.metrics:
        cols = st.columns(4)
        with cols[0]:
            st.metric("Recall", f"{res.metrics.get('recall', 0.0):.1%}")
        with cols[1]:
            st.metric("False Alerts / Week", f"{res.metrics.get('far_per_week', 0.0):.2f}")
        with cols[2]:
            st.metric("Mean Lead Time (h)", f"{res.metrics.get('lead_time_mean_h', 0.0):.1f}")
        with cols[3]:
            st.metric("NNE", f"{res.metrics.get('nne', 0.0):.1f}")

    st.markdown("#### Baseline Comparison")
    st.markdown(
        "- **Random Detector (Matched Alert Rate):** Baseline comparator generating alerts at identical frequency.\n"
        "- **Fixed-Threshold Rule (+3.0 bpm):** Trivial non-adaptive threshold rule without covariate adjustments."
    )

    if "baselines" in res.tables:
        df_base = pd.DataFrame(res.tables["baselines"])
        st.dataframe(df_base, use_container_width=True)


def render_baseline_age_panel(eval_dir: Path | None = None) -> None:
    """Render Baseline-Age curve comparing statistical shrinkage ladder and Chronos foundation model."""
    st.subheader("📈 Baseline Maturity & Age Curve")
    res = get_evaluation_results("baseline_age", eval_dir=eval_dir)
    render_caveats_and_sample_size(res)

    # State negative Chronos result plainly
    st.info(
        "ℹ️ **Finding regarding Chronos foundation forecasting:** "
        "Chronos-bolt-small did not extend usable detection to earlier nights compared to the statistical shrinkage ladder."
    )

    if "curve" in res.tables:
        df_curve = pd.DataFrame(res.tables["curve"])
        st.line_chart(df_curve.set_index("night_age")[["statistical_recall", "chronos_recall"]])
        st.dataframe(df_curve, use_container_width=True)


def render_policy_panel(eval_dir: Path | None = None) -> None:
    """Render Policy benchmark and accuracy-interruption frontier."""
    st.subheader("⚖️ Policy Benchmark & Interruption Frontier")
    res = get_evaluation_results("policy", eval_dir=eval_dir)
    render_caveats_and_sample_size(res)

    st.markdown(
        "Benchmarked against: **never-ask**, **always-ask**, **fixed-threshold**, and **silent concordance**."
    )

    if "frontier" in res.tables:
        df_front = pd.DataFrame(res.tables["frontier"])
        st.dataframe(df_front, use_container_width=True)


def render_ablation_panel(eval_dir: Path | None = None) -> None:
    """Render Ablation study results with paired bootstrap confidence intervals."""
    st.subheader("🔬 Component Ablation Study")
    res = get_evaluation_results("ablation", eval_dir=eval_dir)
    render_caveats_and_sample_size(res)

    if "ablations" in res.tables:
        df_abl = pd.DataFrame(res.tables["ablations"])
        st.dataframe(df_abl, use_container_width=True)


def render_adversarial_panel(eval_dir: Path | None = None) -> None:
    """Render Adversarial evaluation and prompt-injection containment results."""
    st.subheader("🛡️ Adversarial Security & Injection Containment")
    res = get_evaluation_results("adversarial", eval_dir=eval_dir)
    render_caveats_and_sample_size(res)

    if res.metrics:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Attack Success Rate", f"{res.metrics.get('attack_success_rate', 0.0):.1%}")
        with col2:
            st.metric("Containment Rate", f"{res.metrics.get('containment_rate', 1.0):.1%}")

    if "injection_trials" in res.tables:
        df_adv = pd.DataFrame(res.tables["injection_trials"])
        st.dataframe(df_adv, use_container_width=True)


def render_evaluation_page(eval_dir: Path | None = None) -> None:
    """Render the full Evaluation surface."""
    st.title("📊 System Evaluation & Empirical Benchmarks")
    st.caption("Static benchmark results computed offline from standard cohort evaluation runs.")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "🎯 Detection",
            "📈 Baseline Maturity",
            "⚖️ Policy Benchmark",
            "🔬 Ablations",
            "🛡️ Adversarial Security",
        ]
    )

    with tab1:
        render_detection_panel(eval_dir=eval_dir)
    with tab2:
        render_baseline_age_panel(eval_dir=eval_dir)
    with tab3:
        render_policy_panel(eval_dir=eval_dir)
    with tab4:
        render_ablation_panel(eval_dir=eval_dir)
    with tab5:
        render_adversarial_panel(eval_dir=eval_dir)
