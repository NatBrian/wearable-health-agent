"""Episode panel component rendering Summary, Trace, Conversation, and Evidence tabs."""

import pandas as pd
import streamlit as st

from wha.models import EpisodeDetail
from wha.service.episodes import ask_about_episode
from wha.ui.components.pipeline_trace import render_pipeline_trace


def render_summary_tab(detail: EpisodeDetail) -> None:
    """Render Tab 1: Episode outcome summary card, differential, and honesty metrics."""
    outcome = detail.outcome
    if not outcome:
        st.info("This episode is currently in progress. Outcome will appear upon conclusion.")
        return

    st.subheader(f"📋 Outcome: `{outcome.disposition.value}`")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Confidence", outcome.confidence.upper())
    with col2:
        st.metric("Recommended Action", outcome.action.replace("_", " ").title())
    with col3:
        st.metric(
            "Baseline Maturity", f"{outcome.baseline_nights}d ({outcome.baseline_rung.value})"
        )
    with col4:
        st.metric("Unsupported Claims", outcome.unsupported_claims)

    st.markdown("### 📝 Clinical Observation")
    st.info(outcome.observation)

    if outcome.escalation_criteria:
        st.markdown("### 🚨 Escalation Criteria")
        for crit in outcome.escalation_criteria:
            st.warning(f"• {crit}")

    if outcome.differential:
        st.markdown("### 📊 Cause Differential")
        diff_data = []
        for d in outcome.differential:
            diff_data.append(
                {
                    "Cause": d.cause.value,
                    "Probability": d.probability,
                    "Supporting Evidence": "; ".join(d.supporting) or "None",
                    "Contradicting Evidence": "; ".join(d.contradicting) or "None",
                }
            )
        df_diff = pd.DataFrame(diff_data).sort_values("Probability", ascending=False)
        st.bar_chart(df_diff.set_index("Cause")["Probability"])
        st.dataframe(df_diff, use_container_width=True)

    st.caption(
        f"Budget used: {outcome.interruptions_used_this_week} interruptions this week, "
        f"depth {outcome.depth_used_this_episode} questions for this episode."
    )


def render_conversation_tab(detail: EpisodeDetail) -> None:
    """Render Tab 3: Question transcript with EVSI and rejected alternatives, plus bounded Q&A."""
    st.subheader("💬 Question Transcript")
    if not detail.interactions:
        st.caption("No user questions were asked during this episode.")
    else:
        for idx, inter in enumerate(detail.interactions):
            with st.chat_message("assistant"):
                st.markdown(f"**Question {idx + 1}:** {inter.question_text}")
                st.caption(
                    f"Probe served: `{inter.probe_id}` | EVSI: `{inter.evsi:.3f}` | "
                    f"Interruption Cost: `{inter.interruption_cost:.3f}` | Source: `{inter.text_source}`"
                )
                if inter.rejected:
                    with st.expander("Alternatives Considered & Rejected"):
                        for alt_probe, score in inter.rejected:
                            st.write(f"• `{alt_probe}` (score: {score:.3f})")

            with st.chat_message("user"):
                if inter.status == "DECLINED":
                    st.markdown("*Declined (`Not now`)*")
                elif inter.answer_option_id:
                    ans_text = f"**Option selected:** `{inter.answer_option_id}`"
                    if inter.free_text:
                        ans_text += f"\n\n*Notes:* {inter.free_text}"
                    st.markdown(ans_text)
                else:
                    st.markdown(f"Status: `{inter.status}`")
                if inter.answered_at_utc:
                    st.caption(
                        f"Answered at: {inter.answered_at_utc.strftime('%Y-%m-%d %H:%M UTC')}"
                    )

    st.write("---")
    st.subheader("❓ Ask About This Episode")
    st.caption(
        "Answers are strictly bounded to this episode's stored evidence and knowledge citations."
    )

    user_q = st.text_input(
        "Ask a follow-up question...", key=f"followup_{detail.summary.episode_id}"
    )
    if st.button("Submit Follow-up", key=f"btn_followup_{detail.summary.episode_id}") and user_q:
        answer = ask_about_episode(detail.summary.episode_id, user_q)
        if answer.refused:
            st.warning(f"⚠️ **Refused to answer:** {answer.refusal_reason or answer.text}")
        else:
            st.success(answer.text)
            if answer.citations:
                st.markdown("**Evidence Citations:**")
                for c in answer.citations:
                    st.caption(f'• **{c.title}** (`{c.source_id}`): *"{c.passage}"*')


def render_evidence_tab(detail: EpisodeDetail) -> None:
    """Render Tab 4: Retrieved knowledge passages and deliberately visible stripped claims."""
    st.subheader("📚 Knowledge Citations & Evidence")

    # What the agent is able to look up at all, said plainly next to what it did look up.
    # A person reading a citation is entitled to know the shape of the shelf it came off.
    with st.expander("What this system can and cannot look up"):
        st.markdown(
            "**It can cite three things, all written by a person and kept in this "
            "repository:** why a night counted as elevated and how the baseline is "
            "formed; the evidence behind each competing explanation, with the study and "
            "the effect size; and the rule behind any advice to seek care.\n\n"
            "**It cannot cite general health information about a condition.** No consumer "
            "health reference has been loaded, and it is not permitted to search the web "
            "or to write clinical text of its own. If you ask it what a fever means, it "
            "has nothing to quote and will not invent something.\n\n"
            "**The numbers behind the questions it asks are assumed, not measured.** No "
            "published study measures how accurately people report drinking, stress or "
            "early symptoms to an app the next morning. Those figures are set "
            "deliberately cautious so the system interrupts less rather than more.\n\n"
            "**Whether a cause is 'large enough' to explain a night is a display rule, "
            "not a clinical finding.** The effect sizes it compares are cited; the "
            "cut-off for calling the fit good or poor was chosen to be readable and has "
            "no evidence behind it.\n\n"
            "Every figure in the material it quotes was checked against the published "
            "paper. What held up, and the three places it did not, are in "
            "`docs/CORPUS-VERIFICATION.md`."
        )

    if not detail.citations:
        st.info("No knowledge base citations linked to this episode.")
    else:
        for idx, c in enumerate(detail.citations):
            uri_str = f" ([Link]({c.uri}))" if c.uri else ""
            st.markdown(
                f"**{idx + 1}. {c.title}** (`{c.source_id}`){uri_str} — Score: `{c.retrieval_score:.3f}`"
            )
            st.info(f'"{c.passage}"')

    st.write("---")
    st.subheader("🛡️ Stripped Claims")
    st.caption(
        "Assertions drafted by the LLM that were stripped because they could not be grounded in cited evidence."
    )

    if not detail.stripped_claims:
        st.success(
            "✅ No claims were stripped — all generated statements were successfully grounded."
        )
    else:
        for claim in detail.stripped_claims:
            st.warning(f'⚠️ Stripped: "{claim}"')


def render_episode_panel(detail: EpisodeDetail) -> None:
    """Render 4-tab drill-down panel for an episode."""
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Summary", "🔍 Trace", "💬 Conversation", "📚 Evidence"])

    with tab1:
        render_summary_tab(detail)

    with tab2:
        render_pipeline_trace(detail)

    with tab3:
        render_conversation_tab(detail)

    with tab4:
        render_evidence_tab(detail)
