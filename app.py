"""
Streamlit UI
Turkish interface for Research & Publishing Machine
"""

import streamlit as st
import time
import base64
from pathlib import Path
from datetime import datetime

from src.workflow import run_research, setup_logging
from src.config import config

# Setup logging
log_file = config.LOG_DIR / f"app_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
setup_logging(str(log_file))


# ═══════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════

st.set_page_config(
    page_title="Research & Publishing Machine",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ═══════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════

st.title("🎓 Research & Publishing Machine")
st.markdown("**Çift-Ajan Mutabakat Sistemi → Akademik PDF**")
st.markdown("*Truth = A ∩ B | Doğruluk = İki bağımsız zekanın ortak paydası*")

st.markdown("---")


# ═══════════════════════════════════════════════════════════
# SIDEBAR - SETTINGS
# ═══════════════════════════════════════════════════════════

with st.sidebar:
    st.header("⚙️ Ayarlar")

    # Research mode
    research_mode = st.selectbox(
        "Araştırma Modu",
        options=["auto", "internet", "offline"],
        index=0,
        help="Auto: Otomatik karar | Internet: Tavily arama | Offline: Internal knowledge"
    )

    st.markdown("**Debate Parametreleri**")

    max_rounds = st.slider(
        "Maksimum Tur",
        min_value=1,
        max_value=5,
        value=3,
        help="Maksimum debate döngüsü sayısı"
    )

    convergence_threshold = st.slider(
        "Mutabakat Eşiği (%)",
        min_value=85,
        max_value=99,
        value=95,
        help="Doğal mutabakat için benzerlik yüzdesi"
    ) / 100.0

    st.markdown("**PDF Kalite**")

    qa_threshold = st.slider(
        "QA Kabul Puanı",
        min_value=60,
        max_value=95,
        value=75,
        help="PDF onay için minimum kalite puanı"
    )

    st.markdown("---")

    # API Key Status
    st.markdown("**API Durumu**")

    missing_keys = config.validate_api_keys(mode=research_mode)

    if not missing_keys:
        st.success("✅ Tüm API anahtarları yapılandırıldı")
    else:
        st.error("❌ Eksik API anahtarları:")
        for key in missing_keys:
            st.text(f"  • {key}")

        st.info("`.env` dosyasını kontrol edin")


# ═══════════════════════════════════════════════════════════
# MAIN INPUT
# ═══════════════════════════════════════════════════════════

col1, col2 = st.columns([4, 1])

with col1:
    topic = st.text_input(
        "Araştırma Sorusu",
        placeholder="Örn: Yapay zekanın tıp alanındaki uygulamaları nelerdir?",
        help="Araştırmak istediğiniz soruyu buraya girin"
    )

with col2:
    st.markdown("<br>", unsafe_allow_html=True)  # Spacing
    research_button = st.button("🔍 Araştır", type="primary", use_container_width=True)


# ═══════════════════════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════════════════════

if research_button:
    if not topic:
        st.error("❌ Lütfen bir araştırma sorusu girin")
        st.stop()

    # Check API keys
    missing_keys = config.validate_api_keys(mode=research_mode)
    if missing_keys:
        st.error(f"❌ Eksik API anahtarları: {', '.join(missing_keys)}")
        st.stop()

    # Progress tracking
    st.markdown("---")
    st.markdown("### 🔄 İşlem Akışı")

    progress_bar = st.progress(0)
    status_text = st.empty()

    # Phase indicators
    phase_cols = st.columns(9)
    phases = [
        ("🌐", "Arama"),
        ("✍️", "Taslak"),
        ("💬", "Debate"),
        ("🤝", "Mutabakat"),
        ("📝", "LaTeX"),
        ("📄", "Derle"),
        ("🔍", "QA"),
        ("✅", "Onayla"),
        ("💾", "Bitti")
    ]

    phase_indicators = {}
    for idx, (icon, name) in enumerate(phases):
        with phase_cols[idx]:
            phase_indicators[name] = st.empty()
            phase_indicators[name].markdown(f"{icon}<br>{name}", unsafe_allow_html=True)

    # Run workflow
    try:
        with st.spinner("Araştırma yapılıyor..."):
            # Execute
            final_state = run_research(
                topic=topic,
                research_mode=research_mode,
                max_rounds=max_rounds,
                convergence_threshold=convergence_threshold
            )

        # Simulate progress animation (since workflow is blocking)
        progress_steps = [
            (0.11, "Arama", "🟢"),
            (0.22, "Taslak", "🟢"),
            (0.44, "Debate", "🟢"),
            (0.56, "Mutabakat", "🟢"),
            (0.67, "LaTeX", "🟢"),
            (0.78, "Derle", "🟢"),
            (0.89, "QA", "🟢"),
            (0.95, "Onayla", "🟢"),
            (1.0, "Bitti", "🟢")
        ]

        for prog, phase, status in progress_steps:
            progress_bar.progress(prog)
            status_text.text(f"İşlem: {phase}")
            phase_indicators[phase].markdown(f"{status}<br>{phase}", unsafe_allow_html=True)
            time.sleep(0.2)

        status_text.success("✅ Tamamlandı!")

        # ───────────────────────────────────────────────────────
        # RESULTS
        # ───────────────────────────────────────────────────────

        st.markdown("---")
        st.markdown("## 📊 Sonuçlar")

        # Metrics
        metric_cols = st.columns(5)

        with metric_cols[0]:
            st.metric("Debate Turları", final_state.iteration_counter)

        with metric_cols[1]:
            st.metric("Mutabakat", f"{final_state.similarity_score:.1%}")

        with metric_cols[2]:
            color = "🟢" if final_state.average_qa_score >= qa_threshold else "🔴"
            st.metric("QA Puanı", f"{color} {final_state.average_qa_score:.1f}/100")

        with metric_cols[3]:
            st.metric("LaTeX Retry", final_state.latex_retry_count)

        with metric_cols[4]:
            st.metric("PDF Regeneration", final_state.pdf_regeneration_count)

        # PDF Display
        st.markdown("### 📄 Final PDF")

        if final_state.pdf_path and Path(final_state.pdf_path).exists():
            with open(final_state.pdf_path, "rb") as pdf_file:
                pdf_bytes = pdf_file.read()

            col_pdf, col_download = st.columns([3, 1])

            with col_pdf:
                st.markdown(f"**Dosya:** `{Path(final_state.pdf_path).name}`")
                if final_state.pdf_approved:
                    st.success("✅ PDF kalite kontrolünden geçti")
                else:
                    st.warning("⚠️ PDF kalite eşiğinin altında")

            with col_download:
                st.download_button(
                    label="📥 PDF İndir",
                    data=pdf_bytes,
                    file_name=f"research_{int(time.time())}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            # PDF Preview
            st.markdown("**Önizleme:**")
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
            st.markdown(pdf_display, unsafe_allow_html=True)

        else:
            st.error("❌ PDF oluşturulamadı")

        # Consensus Report
        with st.expander("📝 Konsensus Raporu (Markdown)"):
            if final_state.consensus_report:
                st.markdown(final_state.consensus_report)
            else:
                st.warning("Konsensus raporu mevcut değil")

        # QA Details
        with st.expander("🔍 Kalite Detayları"):
            col_qa1, col_qa2 = st.columns(2)

            with col_qa1:
                st.markdown("**Görsel Kalite (Gemini Vision)**")
                st.metric("Puan", f"{final_state.visual_qa_score:.1f}/100")

            with col_qa2:
                st.markdown("**İçerik Kalitesi (Claude)**")
                st.metric("Puan", f"{final_state.content_qa_score:.1f}/100")

        # Statistics
        with st.expander("📈 İstatistikler"):
            duration = final_state.get_duration()
            st.markdown(f"**Toplam Süre:** {duration:.1f} saniye")
            st.markdown(f"**Başlangıç:** {final_state.start_time}")
            st.markdown(f"**Bitiş:** {final_state.end_time}")
            st.markdown(f"**Zorunlu Bitiş mi?** {'Evet' if final_state.forced_stop else 'Hayır'}")

        # Errors
        if final_state.errors:
            with st.expander("⚠️ Hata Logu"):
                for idx, error in enumerate(final_state.errors, 1):
                    st.warning(f"{idx}. {error}")

        st.success("🎉 Araştırma başarıyla tamamlandı!")

    except Exception as e:
        st.error(f"❌ Hata oluştu: {str(e)}")
        st.exception(e)


# ═══════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; font-size: 0.9em;'>
    Research & Publishing Machine v1.0 | Dual-LLM Debate System<br>
    Truth = A ∩ B | Powered by Claude Sonnet 4.5 & Gemini Pro 1.5
</div>
""", unsafe_allow_html=True)
