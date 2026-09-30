"""
Streamlit UI for the Dual-LLM Research Debate pipeline.

Live progress is driven by the LangGraph stream (run_research's on_phase
callback fires after every completed node) plus a log handler that tails
pipeline logs into the page while a run is in flight.
"""

import base64
import logging
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from src.workflow import run_research, setup_logging
from src.config import config
from src.schemas import DebateState
from src.run_store import list_runs, load_run, run_label

# ═══════════════════════════════════════════════════════════
# CHART PALETTE (validated categorical order — see dataviz notes)
# ═══════════════════════════════════════════════════════════

METRIC_COLORS = {
    "Symmetric consensus": "#2a78d6",   # blue  (official metric)
    "Gemini coverage": "#eb6834",       # orange
    "Claude coverage": "#1baf7a",       # aqua
    "Average coverage": "#eda100",      # yellow
}
THRESHOLD_COLOR = "#898781"  # muted ink, both themes

PHASES = [
    ("grounding", "Grounding"),
    ("parallel_drafting", "Drafting"),
    ("iterative_debate", "Debate"),
    ("intersection_synthesis", "Synthesis"),
    ("latex_generation", "LaTeX"),
    ("pdf_compilation", "Compile"),
    ("quality_assurance", "QA"),
    ("approval_decision", "Approval"),
]
PHASE_INDEX = {name: i for i, (name, _) in enumerate(PHASES)}

# ═══════════════════════════════════════════════════════════
# LOGGING SETUP (once per session)
# ═══════════════════════════════════════════════════════════

if "log_configured" not in st.session_state:
    log_file = config.LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    setup_logging(str(log_file))
    st.session_state.log_configured = True


class UILogHandler(logging.Handler):
    """Tails pipeline log records into a Streamlit placeholder.

    Records can arrive from worker threads (parallel agent calls); the
    placeholder is only touched from the main script thread, other threads
    just append to the buffer and their lines appear on the next
    main-thread emit or phase callback.
    """

    def __init__(self, placeholder, buffer: deque):
        super().__init__(level=logging.INFO)
        self.placeholder = placeholder
        self.buffer = buffer
        self.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))

    def emit(self, record):
        try:
            self.buffer.append(self.format(record))
            if threading.current_thread() is threading.main_thread():
                self.flush_to_ui()
        except Exception:
            pass

    def flush_to_ui(self):
        try:
            self.placeholder.code("\n".join(list(self.buffer)[-14:]), language=None)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════
# PAGE
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Dual-LLM Research Debate",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🎓 Dual-LLM Research Debate")
st.markdown(
    "Two LLMs from different vendors research the same question independently, "
    "debate each other's claims round by round, and a neutral referee distills "
    "their **locked agreements** into an academic PDF.  \n"
    "*Truth = A ∩ B — only what both models endorse survives.*"
)
st.markdown("---")

# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    # ── Past researches (chat-style history) ────────────────
    if st.button("➕ New research", use_container_width=True, type="primary"):
        st.session_state.pop("final_state", None)
        st.session_state.pop("loaded_from", None)
        st.session_state.pop("full_log", None)

    st.markdown("### 📂 Past researches")
    saved_runs = list_runs()
    if saved_runs:
        for run_path in saved_runs[:25]:
            if st.button(run_label(run_path), key=f"run_{run_path.name}",
                         use_container_width=True):
                loaded = load_run(run_path)
                if loaded:
                    st.session_state.final_state = loaded
                    st.session_state.loaded_from = str(run_path)
                    st.session_state.pop("full_log", None)
                else:
                    st.error("Could not load that run file")
        if len(saved_runs) > 25:
            st.caption(f"…and {len(saved_runs) - 25} older runs in `output/runs/`")
    else:
        st.caption("No past researches yet. Finished runs are saved "
                   "locally to `output/runs/` and will be listed here.")

    st.markdown("---")
    st.header("⚙️ Settings")

    research_mode = st.selectbox(
        "Research mode",
        options=["auto", "internet", "offline"],
        index=0,
        help="auto: keyword-based decision | internet: Tavily web search | offline: model knowledge only",
    )

    report_language = st.selectbox(
        "Report language",
        options=["auto", "tr", "en"],
        index=0,
        format_func=lambda v: {"auto": "Auto (follow the question)",
                               "tr": "Türkçe", "en": "English"}[v],
        help="Language of the final consensus report and PDF",
    )

    st.markdown("**Debate parameters**")

    max_rounds = st.slider(
        "Max debate rounds", min_value=1, max_value=5, value=3,
        help="The debate stops early if all four consensus metrics reach the threshold",
    )

    convergence_threshold = st.slider(
        "Convergence threshold (%)", min_value=85, max_value=99, value=95,
        help="All four metrics (symmetric consensus + both coverages + average) must reach this",
    ) / 100.0

    st.markdown("**Quality assurance**")
    st.info(f"QA threshold: {config.QA_THRESHOLD}/100")
    st.caption(
        "Below-threshold PDFs are regenerated (up to "
        f"{config.MAX_PDF_REGENERATIONS}×). If QA itself errors, the run is "
        "marked failed and the PDF is explicitly NOT approved — no silent auto-approval."
    )

    st.markdown("---")
    st.markdown("**Models**")
    st.caption(f"Explorer: `{config.GEMINI_MODEL}`  \nJudge/Referee: `{config.CLAUDE_MODEL}`")

    st.markdown("**API status**")
    missing_keys = config.validate_api_keys(mode=research_mode)
    if not missing_keys:
        st.success("All API keys configured")
    else:
        st.error("Missing API keys:")
        for key in missing_keys:
            st.text(f"  • {key}")
        st.info("Check your `.env` file")

# ═══════════════════════════════════════════════════════════
# INPUT
# ═══════════════════════════════════════════════════════════

col1, col2 = st.columns([4, 1])
with col1:
    topic = st.text_input(
        "Research question",
        placeholder="e.g. What are the applications of AI in medicine?",
    )
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    run_clicked = st.button("🔍 Research", type="primary", use_container_width=True)

# ═══════════════════════════════════════════════════════════
# RUN
# ═══════════════════════════════════════════════════════════

if run_clicked:
    if not topic:
        st.error("Please enter a research question")
        st.stop()
    if missing_keys:
        st.error(f"Missing API keys: {', '.join(missing_keys)}")
        st.stop()

    st.markdown("### 🔄 Pipeline progress")
    phase_cols = st.columns(len(PHASES))
    phase_slots = []
    for idx, (_, label) in enumerate(PHASES):
        with phase_cols[idx]:
            slot = st.empty()
            slot.markdown(f"⚪ {label}")
            phase_slots.append(slot)

    progress_bar = st.progress(0.0)
    status_line = st.empty()
    log_placeholder = st.empty()

    log_buffer: deque = deque(maxlen=400)
    ui_handler = UILogHandler(log_placeholder, log_buffer)
    logging.getLogger().addHandler(ui_handler)

    def render_phases(done_upto: int, revising: bool = False):
        """done_upto = index of last completed phase (-1 = none)."""
        for i, (_, label) in enumerate(PHASES):
            if i <= done_upto:
                phase_slots[i].markdown(f"🟢 {label}")
            elif i == done_upto + 1:
                phase_slots[i].markdown(f"🔵 **{label}**")
            else:
                phase_slots[i].markdown(f"⚪ {label}")
        if revising:
            status_line.warning("QA rejected the PDF — regenerating LaTeX/PDF…")

    def on_phase(node_name: str, snapshot: DebateState):
        if node_name == "pdf_revision":
            # QA rejected on score: LaTeX/compile/QA phases run again
            for i in range(PHASE_INDEX["latex_generation"], len(PHASES)):
                phase_slots[i].markdown(f"⚪ {PHASES[i][1]}")
            render_phases(PHASE_INDEX["intersection_synthesis"], revising=True)
            return
        idx = PHASE_INDEX.get(node_name)
        if idx is None:
            return
        render_phases(idx)
        progress_bar.progress((idx + 1) / len(PHASES))
        if node_name == "iterative_debate":
            status_line.info(
                f"Debate finished: {snapshot.iteration_counter} round(s), "
                f"{len(snapshot.locked_agreements)} locked claims, "
                f"consensus {snapshot.similarity_score:.0%}"
            )
        ui_handler.flush_to_ui()

    render_phases(-1)
    status_line.info("Starting pipeline…")

    try:
        final_state = run_research(
            topic=topic,
            research_mode=research_mode,
            max_rounds=max_rounds,
            convergence_threshold=convergence_threshold,
            report_language=report_language,
            on_phase=on_phase,
        )
        st.session_state.final_state = final_state
        st.session_state.pop("loaded_from", None)
        st.session_state.full_log = "\n".join(log_buffer)
        progress_bar.progress(1.0)
        status_line.empty()
        log_placeholder.empty()
    except Exception as e:
        st.error(f"Pipeline failed: {e}")
        st.exception(e)
        st.stop()
    finally:
        logging.getLogger().removeHandler(ui_handler)

# ═══════════════════════════════════════════════════════════
# RESULTS (rendered from session state so downloads/expanders
# don't re-trigger a run). A fresh session starts clean — past
# researches are opened from the sidebar, chat-app style.
# ═══════════════════════════════════════════════════════════

if "final_state" not in st.session_state and not run_clicked:
    st.info("👋 Ask a research question above — or open one of your past "
            "researches from the sidebar on the left.")

if "final_state" in st.session_state:
    fs: DebateState = st.session_state.final_state

    st.markdown("---")
    st.markdown(f"## ❓ {fs.topic}")
    meta_bits = [f"Mode: {fs.research_mode}"]
    if fs.report_language != "auto":
        meta_bits.append(f"Report language: {fs.report_language}")
    if fs.start_time:
        meta_bits.append(fs.start_time.strftime("%Y-%m-%d %H:%M"))
    if st.session_state.get("loaded_from"):
        meta_bits.append(f"loaded from `{st.session_state.loaded_from}`")
    st.caption(" · ".join(meta_bits))
    st.markdown("## 📊 Results")

    # Verdict banner
    if fs.synthesis_failed:
        st.error(
            "❌ **Consensus synthesis failed** — the report is a degraded "
            "locked-claims fallback and the PDF is explicitly NOT approved. "
            "See the error log below."
        )
    elif fs.qa_failed:
        st.error(
            "❌ **Quality assurance could not be performed** (API/parse error). "
            "The PDF was generated but is explicitly NOT approved. See the error log below."
        )
    elif fs.pdf_approved:
        st.success(f"✅ **PDF approved** — QA score {fs.average_qa_score:.1f}/100")
    else:
        st.warning(
            f"⚠️ **PDF not approved** — QA score {fs.average_qa_score:.1f}/100 "
            f"is below the threshold of {config.QA_THRESHOLD} after "
            f"{fs.pdf_regeneration_count} regeneration(s)."
        )

    # Stat tiles
    tiles = st.columns(5)
    tiles[0].metric("Debate rounds", fs.iteration_counter)
    tiles[1].metric("Final consensus", f"{fs.similarity_score:.0%}",
                    delta="converged" if fs.converged else "forced stop",
                    delta_color="normal" if fs.converged else "off")
    tiles[2].metric("Locked claims", len(fs.locked_agreements))
    tiles[3].metric("QA score", "failed" if fs.qa_failed else f"{fs.average_qa_score:.0f}/100")
    tiles[4].metric("Duration", f"{fs.get_duration():.0f}s")

    # ── Debate section ──────────────────────────────────────
    st.markdown("### 💬 Debate")

    if fs.debate_rounds:
        rows = []
        for r in fs.debate_rounds:
            rows += [
                {"Round": r.round_num, "Metric": "Symmetric consensus", "Value": r.consensus_score},
                {"Round": r.round_num, "Metric": "Gemini coverage", "Value": r.gemini_coverage},
                {"Round": r.round_num, "Metric": "Claude coverage", "Value": r.claude_coverage},
                {"Round": r.round_num, "Metric": "Average coverage", "Value": r.avg_coverage},
            ]
        df = pd.DataFrame(rows)

        col_chart, col_rounds = st.columns([3, 2])
        with col_chart:
            base = alt.Chart(df).encode(
                x=alt.X("Round:O", title="Round"),
                y=alt.Y("Value:Q", title="Consensus", axis=alt.Axis(format="%"),
                        scale=alt.Scale(domain=[0, 1])),
                color=alt.Color(
                    "Metric:N",
                    scale=alt.Scale(domain=list(METRIC_COLORS.keys()),
                                    range=list(METRIC_COLORS.values())),
                    legend=alt.Legend(orient="bottom", columns=2, title=None),
                ),
                tooltip=["Round:O", "Metric:N", alt.Tooltip("Value:Q", format=".1%")],
            )
            chart = (base.mark_line(strokeWidth=2) + base.mark_point(size=70, filled=True))
            threshold_rule = alt.Chart(
                pd.DataFrame({"y": [fs.convergence_threshold]})
            ).mark_rule(strokeDash=[5, 4], color=THRESHOLD_COLOR, strokeWidth=1.5).encode(y="y:Q")
            st.altair_chart(
                (chart + threshold_rule).properties(
                    title=f"Convergence per round (threshold {fs.convergence_threshold:.0%})",
                    height=280,
                ),
                use_container_width=True, theme="streamlit",
            )

        with col_rounds:
            for r in fs.debate_rounds:
                with st.expander(f"Round {r.round_num} — {r.consensus_score:.0%} consensus"):
                    st.markdown(f"**New agreements:** {len(r.new_agreements)}")
                    for a in r.new_agreements[:8]:
                        if a.strip():
                            st.markdown(f"- {a}")
                    st.markdown(f"**Still disputed:** {len(r.disputed_points)}")
                    for d in r.disputed_points[:8]:
                        if d.strip():
                            st.markdown(f"- {d}")

    # Locked claims table
    st.markdown("#### 🔒 Locked claims (endorsed by both models)")
    if fs.locked_agreements:
        def agents_wording(c):
            canonical = c.statement.strip().lower()
            parts = [w.strip() for w in (c.resolution_gemini, c.resolution_claude)
                     if w and w.strip().lower() != canonical]
            return " | ".join(dict.fromkeys(parts)) or "—"

        st.dataframe(
            pd.DataFrame([
                {
                    "Claim (canonical)": c.statement,
                    "Agents' wording (if narrowed)": agents_wording(c),
                    "Round": c.locked_round,
                    "Confidence": round(c.confidence_avg, 2),
                    "Source (Gemini)": c.source_gemini or "—",
                    "Source (Claude)": c.source_claude or "—",
                }
                for c in fs.locked_agreements
            ]),
            use_container_width=True, hide_index=True,
        )
    else:
        st.caption("No claims were locked — the consensus report is built only from "
                   "the intersection of the final revised answers.")

    if fs.current_disputed_points:
        with st.expander(f"⚔️ Excluded from the report — {len(fs.current_disputed_points)} disputed point(s)"):
            for d in fs.current_disputed_points:
                st.markdown(f"- {d}")

    # ── Report & PDF ────────────────────────────────────────
    st.markdown("### 📄 Consensus report & PDF")

    col_pdf, col_dl = st.columns([3, 1])
    pdf_ok = fs.pdf_path and Path(fs.pdf_path).exists()
    with col_pdf:
        if pdf_ok:
            st.markdown(f"**File:** `{Path(fs.pdf_path).name}`")
        else:
            st.error("PDF could not be generated")
            if fs.latex_code:
                with st.expander("Show generated LaTeX"):
                    st.code(fs.latex_code, language="latex")
    with col_dl:
        if pdf_ok:
            with open(fs.pdf_path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button(
                "📥 Download PDF", data=pdf_bytes,
                file_name=f"research_{int(time.time())}.pdf",
                mime="application/pdf", use_container_width=True,
            )

    if fs.consensus_report:
        with st.expander("Consensus report (markdown)", expanded=not pdf_ok):
            st.markdown(fs.consensus_report)

    if pdf_ok:
        with st.expander("PDF preview", expanded=True):
            b64 = base64.b64encode(pdf_bytes).decode("utf-8")
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{b64}" '
                f'width="100%" height="720" type="application/pdf"></iframe>',
                unsafe_allow_html=True,
            )

    # ── QA panel ────────────────────────────────────────────
    with st.expander("🔍 Quality assurance details"):
        if fs.qa_failed:
            st.error("QA failed — the scores below are zeros, not assessments.")
        qa1, qa2 = st.columns(2)
        qa1.metric("Visual QA (Gemini Vision)", f"{fs.visual_qa_score:.1f}/100")
        qa2.metric("Content QA (Claude)", f"{fs.content_qa_score:.1f}/100")
        st.caption(f"PDF regenerations: {fs.pdf_regeneration_count} · "
                   f"LaTeX retries: {fs.latex_retry_count}")

    # ── Diagnostics ─────────────────────────────────────────
    if fs.errors:
        with st.expander(f"⚠️ Error log ({len(fs.errors)})"):
            for i, err in enumerate(fs.errors, 1):
                st.warning(f"{i}. {err}")

    if st.session_state.get("full_log"):
        with st.expander("🧾 Pipeline log"):
            st.code(st.session_state.full_log, language=None)

# ═══════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════

st.markdown("---")
st.markdown(
    f"""
<div style='text-align: center; color: #898781; font-size: 0.9em;'>
    Dual-LLM Research Debate · LangGraph state machine · Truth = A ∩ B<br>
    {config.CLAUDE_MODEL} (Judge/Referee) × {config.GEMINI_MODEL} (Explorer)
</div>
""",
    unsafe_allow_html=True,
)
