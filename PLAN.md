# 🎯 Research & Publishing Machine - Final System Design v4.0

> **Historical design document.** This file records a mid-development plan/status snapshot and is kept for context. Parts of it describe features that were later removed or changed (e.g. devil's-advocate alternation, cross-examination phases, citation validator). See README.md for the current behavior.

**Version:** 4.0 FINAL (Aligned with lastplan.md)
**Architecture:** Multi-Agent Debate with Grounded Intersection → Academic PDF Publication
**Core Philosophy:** "Doğruluk, iki bağımsız zekanın anlaşmazlık sonrası vardığı ortak paydadır."
**Mathematical Truth:** Truth = A ∩ B

**Status:** ✅ FINAL SPECIFICATION - READY TO CODE

---

## 🎓 Temel Felsefe ve Yaklaşım

### Sistem Mantığı (Core Logic)

Bu sistem, **Döngüsel Durum Makinesi (Cyclic State Machine)** prensibiyle çalışır.

**Lineer değil, döngüsel:**
```
Traditional RAG: Question → Search → Generate → Output
Our System:      Question → Search → Generate → Critique → Revise → Critique → ... → Consensus → PDF
```

**Truth = A ∩ B** prensibi:
- Sadece **her iki ajanın da kesinlikle kabul ettiği** bilgiler çıktıya dahil edilir
- Bir ajanın şüphe duyduğu, reddettiği veya bahsetmediği her türlü bilgi **silinir**
- Sonuç: **%100 doğrulanmış, "Saf Bilgi"**

---

## 📋 Executive Summary

### System Goal
İki frontier LLM (Claude Sonnet 4.5 & Gemini Pro 1.5) arasında **acımasız bir çapraz sorgu (strict cross-examination)** yaparak, web kaynaklarına dayalı, karşılıklı eleştiri sonucu doğrulanmış bilgileri içeren, **publication-ready akademik PDF** üretmek.

### Revolutionary Pipeline
```
User Question → [V1: Offline / V2: Tavily Search] (Grounding) →
Parallel Drafting (Isolated, no bias) →
Cross-Examination (Strict Critique - Acımasız) →
Iterative Revision (Fix or Defend) →
Intersection Synthesis (A ∩ B - Hakem) →
LaTeX Generation → PDF Compilation →
Visual QA (Gemini Vision) + Content QA (Claude Text) →
[APPROVED] → Final PDF | [REJECTED] → Regenerate (Max 2x)
```

### Why This is State-of-the-Art (SOTA)
**Traditional RAG sistemleri:**
- Tek model cevap verir ("Ben böyle düşünüyorum")
- Halüsinasyon riski yüksek
- Bias kontrol edilemez

**Bu sistem:**
- ✅ Güncel Veriye dayanan (V2: Tavily) veya Internal Knowledge (V1: Offline)
- ✅ Karşıt görüşle sınanmış (Strict Debate)
- ✅ Şüpheli kısımları tıraşlanmış (Intersection)
- ✅ Görsel ve içerik kalitesi doğrulanmış (Dual QA)
- ✅ Akademik formatta, indirilebilir PDF

---

## 🏛️ System Architecture

### Components

#### 1. Orchestrator (LangGraph StateGraph)
- **Role:** Merkezi beyin - Akışı yöneten, durumu (state) tutan, ajanlar arası veri trafiği sağlayan
- **Technology:** LangGraph with cyclic graph support
- **Philosophy:** "Durum Makinesi" - Her node state'i alır, değiştirir, döndürür

#### 2. Grounding Layer (V1: Offline / V2: Tavily)
- **Role:** Zemin Katmanı - LLM'lerin halüsinasyon görmesini engelleyen dış dünya bağlantısı
- **V1 Mode (Offline):** İnternet araması YOK, sadece internal knowledge
- **V2 Mode (Internet):** **Tavily API** kullanılır (advanced search depth)
- **Auto Mode:** Keyword-based karar (time-sensitive → V2, static → V1)
- **Critical:** V2'de tüm iddialar Tavily'den gelen verilere dayalı olmalı

#### 3. Agent A - The Explorer (Gemini Pro 1.5)
- **Role:** Yüksek yaratıcılık (High Temperature - 0.7)
- **Mission:** Geniş kapsamlı veri toplar, hipotez üretir, farklı açıları keşfeder
- **Personality:** Kapsamlı, yaratıcı, bağlantıları gören
- **Weakness:** Bazen spekülatif olabilir
- **NEW ROLE:** Visual QA - PDF sayfa görsellerini analiz eder

#### 4. Agent B - The Judge (Claude Sonnet 4.5)
- **Role:** Yüksek mantık (Low Temperature - 0.5)
- **Mission:** Analitik inceleme yapar, açıkları bulur, mantık zincirlerini kontrol eder
- **Personality:** Kesin, mantıksal, eleştirel, acımasız
- **Strength:** Zayıf kanıtları ve mantık hatalarını anında yakalar
- **NEW ROLE:** LaTeX generation + Content QA

#### 5. Hakem (Synthesizer) - Claude Sonnet 4.5
- **Role:** Tarafsız kesişim çıkarıcı
- **Temperature:** 0.2 (Minimal creativity)
- **Philosophy:** **"Kesişim Sentezi" - Truth = A ∩ B**
- **Algorithm:** İki ajanın metnini karşılaştır, sadece her ikisinin de kesinlikle kabul ettiği cümleleri al
- **Conservative Principle:** "Şüphe varsa çıkar"

---

## 📊 State Management (Simplified Architecture)

### State Structure (Basitleştirilmiş)

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime

# ═══════════════════════════════════════════════════════════
# CORE STATE (The RAM)
# ═══════════════════════════════════════════════════════════

class DebateState(BaseModel):
    """
    Minimal, clean state structure
    Based on lastplan.md principles
    """

    # ───────────────────────────────────────────────────────
    # IMMUTABLE INPUTS (Sabit)
    # ───────────────────────────────────────────────────────

    topic: str = Field(description="User's research question")

    # NEW: Research Mode Selection
    research_mode: Literal["offline", "internet", "auto"] = Field(
        default="auto",
        description="V1=offline (no search), V2=internet (Tavily), auto=keyword-based decision"
    )

    shared_context: str = Field(
        default="",
        description="Web search results or offline notice"
    )

    max_rounds: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum debate iterations (Default: 3)"
    )

    convergence_threshold: float = Field(
        default=0.95,
        ge=0.85,
        le=0.99,
        description="Semantic similarity target (Default: 95%)"
    )

    # ───────────────────────────────────────────────────────
    # AGENT OUTPUTS (Değişken - Her turda güncellenir)
    # ───────────────────────────────────────────────────────

    gemini_draft: str = Field(default="", description="Explorer's current draft")
    claude_draft: str = Field(default="", description="Judge's current draft")

    gemini_critique: str = Field(default="", description="Explorer's critique of Judge")
    claude_critique: str = Field(default="", description="Judge's critique of Explorer")

    # ───────────────────────────────────────────────────────
    # LOOP CONTROL (Sayaç)
    # ───────────────────────────────────────────────────────

    iteration_counter: int = Field(
        default=0,
        ge=0,
        description="Current iteration (0, 1, 2, ...)"
    )

    similarity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Semantic agreement between drafts"
    )

    converged: bool = Field(default=False, description="Natural consensus reached?")
    forced_stop: bool = Field(default=False, description="Stopped due to max_rounds?")

    # ───────────────────────────────────────────────────────
    # CONSENSUS OUTPUT
    # ───────────────────────────────────────────────────────

    consensus_report: Optional[str] = Field(
        default=None,
        description="Final intersection report (A ∩ B)"
    )

    # ───────────────────────────────────────────────────────
    # PDF GENERATION (NEW)
    # ───────────────────────────────────────────────────────

    latex_code: Optional[str] = Field(default=None, description="Generated LaTeX source")
    pdf_path: Optional[str] = Field(default=None, description="Compiled PDF file path")

    latex_retry_count: int = Field(default=0, description="LaTeX compilation retries")
    pdf_regeneration_count: int = Field(default=0, description="PDF quality regenerations")

    visual_qa_score: float = Field(default=0.0, description="Gemini Vision QA score")
    content_qa_score: float = Field(default=0.0, description="Claude Text QA score")
    average_qa_score: float = Field(default=0.0, description="Average QA score")

    pdf_approved: bool = Field(default=False, description="PDF passed QA?")

    # ───────────────────────────────────────────────────────
    # METADATA
    # ───────────────────────────────────────────────────────

    errors: List[str] = Field(default_factory=list, description="Error log")
    statistics: Dict = Field(default_factory=dict, description="Performance metrics")
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
```

---

## 🎭 Complete Prompt Library (UPDATED with Strict Critique Philosophy)

### System Prompts

```python
# ═══════════════════════════════════════════════════════════
# AGENT A: THE EXPLORER (Gemini)
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT_GEMINI_EXPLORER = """You are Agent A: The Explorer

COGNITIVE PROFILE:
- Role: Kapsamlı araştırmacı (Comprehensive Researcher)
- Personality: Yaratıcı, bağlantıları gören, geniş perspektifli
- Temperature: 0.7 (Yüksek yaratıcılık)
- Strength: Farklı açıları keşfetme, hipotez üretme

YOUR MISSION:
1. Verilen web kaynaklarını kullanarak soruyu en kapsamlı şekilde cevapla
2. Farklı perspektifleri, bağlantıları, ilişkileri gör
3. Her iddianı mutlaka kaynak ile destekle
4. Yaratıcı düşün ama spekülatif olma

CRITICAL RULES:
✓ SADECE verilen web kaynaklarında olan bilgileri kullan
✓ Her iddia için [Source: URL] formatında kaynak belirt
✓ Eğer kaynaklar çelişiyorsa, her iki perspektifi de sun
✓ Belirsiz durumlarda "may", "likely", "suggests" gibi ifadeler kullan

FORBIDDEN:
✗ ASLA kaynak olmadan iddiada bulunma
✗ ASLA kendi bilgine dayanma (sadece verilen context)
✗ ASLA kesin dil kullanma belirsiz konularda

OUTPUT STYLE:
- İyi yapılandırılmış paragraflar
- Net konu cümleleri
- Açık kaynak atıfları: [Source: URL]
- Dengeli ton (ne çok temkinli ne çok iddialı)
"""

# ═══════════════════════════════════════════════════════════
# AGENT B: THE JUDGE (Claude)
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT_CLAUDE_JUDGE = """You are Agent B: The Judge

COGNITIVE PROFILE:
- Role: Analitik hakim (Analytical Judge)
- Personality: Mantıksal, eleştirel, acımasız, kesin
- Temperature: 0.5 (Yüksek hassasiyet)
- Strength: Mantık hatalarını yakalama, zayıf kanıtları tespit etme

YOUR MISSION:
1. Verilen web kaynaklarını kullanarak soruyu en kesin şekilde cevapla
2. Sadece güçlü kanıt olan iddiaları dahil et
3. Mantık zincirlerini kontrol et, açıkları bul
4. Kesin olmayan her şeyi çıkar

CRITICAL RULES:
✓ SADECE kesin kanıt olan iddiaları yaz
✓ Her cümle için mutlaka [Source: URL] belirt
✓ Belirsizlik varsa iddayı ÇIKART (speküle etme)
✓ Mantık hatalarına SIFIR TOLERANS

FORBIDDEN:
✗ ASLA "genel bilgi" diye kaynak olmadan yazma
✗ ASLA "bazıları der ki", "inanılır ki" gibi zayıf ifadeler kullanma
✗ ASLA dairesel mantık veya desteksiz çıkarımlar yapma

OUTPUT STYLE:
- Kısa, kesin cümleler
- Her iddia için [Source: URL]
- Muhafazakar dil
- Yapılandırılmış mantık (A ise B, çünkü C)
"""

# ═══════════════════════════════════════════════════════════
# CROSS-EXAMINATION: Strict Critique (Acımasız Eleştiri)
# ═══════════════════════════════════════════════════════════

PROMPT_TEMPLATE_CRITIQUE = """CROSS-EXAMINATION TASK (ÇAPRAZ SORGU)

Sen bir hakimsin. Meslektaşının taslağını acımasızca (strictly) inceleyeceksin.

AMAÇ:
1. Hataları, zayıf kanıtları, mantık açıklarını TÜMLF (ruthlessly) bul
2. Onun senden iyi yaptığı şeyleri de kabul et
3. Kendi taslağını bu analize göre revize et

══════════════════════════════════════════════════════════
MESLEKTAŞINlN TASLAĞI:
{other_agent_draft}

══════════════════════════════════════════════════════════
ORIJINAL WEB KAYNAKLARI (Değişmez Gerçek):
{web_context}

══════════════════════════════════════════════════════════
SENIN ÖNCEKI TASLAGIN:
{own_draft}

══════════════════════════════════════════════════════════

ELEŞTIRI KONTROL LISTESI (Acımasız):
❌ Faktüel Hatalar: Kaynaklarda olmayan iddialar
❌ Mantık Hataları: Dairesel mantık, desteksiz çıkarımlar
❌ Eksik Kanıt: Kaynak olmadan yapılan ifadeler
❌ Aşırı Güven: Belirsiz konularda kesin dil
✅ Güçlü Yönler: Senin gözden kaçırdığın ama doğru olan şeyler

REVIZYON STRATEJISI:
- Meslektaşın eleştirisi haklıysa → Pozisyonunu güncelle
- Meslektaşın eleştirisi haksızsa → Daha güçlü kanıtla savun
- Meslektaşın senin gözden kaçırdığın boşlukları bulduysa → Doldur
- Meslektaşın hata yaptıysa → Sen aynı hatayı yapma

═══════════════════════════════════════════════════════════
ZORUNLU OUTPUT FORMATI (KATIBIR):
═══════════════════════════════════════════════════════════

CRITIQUE:
[Meslektaşın taslağının detaylı analizi - spesifik ol, satır/iddia belirt]

REVISED_ANSWER:
[Öğrendiklerini dahil eden geliştirilmiş taslağın]

═══════════════════════════════════════════════════════════
Bu iki bölümlü formatın dışına ÇIKMA.
NEZAKETYerine ACIMASıZCAELEŞTİR.
"""

# ═══════════════════════════════════════════════════════════
# HAKEM (SYNTHESIZER): Intersection Logic (A ∩ B)
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT_SYNTHESIZER = """You are the Hakem (Neutral Referee)

COGNITIVE PROFILE:
- Role: Tarafsız kesişim çıkarıcı (Intersection Extractor)
- Personality: Muhafazakar, kesin, tarafsız
- Philosophy: "Şüphe varsa çıkar" (When in doubt, exclude)
- Temperature: 0.2 (Minimal yaratıcılık)
- Mathematical: Truth = A ∩ B

YOUR MISSION:
İki AI ajanının taslağından SADECE kesişim kümesini (intersection set) çıkar.
Yani: HER İKİ AJANIN DA kesinlikle kabul ettiği iddiaları al.

DAHIL ETME KRITERLERI (HEPSİ gerekli):
✓ Her iki ajan da bahsediyor (kelimesi kelimesine veya anlamsal olarak)
✓ Her iki ajan da kesin (belirsiz dil kullanmamış: "belki", "olabilir" gibi)
✓ İddia orijinal web kaynaklarında açıkça destekleniyor
✓ Ajanlar arasında semantik çelişki YOK

ÇIKARMA KRITERLERI (HERHANGİ BİRİ yeterli):
✗ Sadece bir ajan bahsediyor
✗ Ajanlardan biri belirsiz dil kullanmış
✗ Orijinal kaynaklarda bulunamıyor
✗ Ajanlar çelişiyor (ince farklar bile)
✗ İddia kaynaklardaki veriden çıkarım/yorumlama

ANLAŞMAZLIK TESPİTI:
[DISPUTED] olarak işaretle eğer:
- Ajanlar aynı konu hakkında farklı gerçekler söylüyorsa
- Biri onaylıyor, diğeri reddediyorsa
- Sayısal/tarih uyuşmazlığı varsa

MUHAFAZAKAR İLKE:
5 kesin gerçek, 10 şüpheli gerçekten iyidir.
İddiaların semantik olarak eşleşip eşleşmediğinden emin değilsen → ÇIKART.

OUTPUT GEREKLİLİKLERİ:
- Her kabul edilen iddia için MUTLAKA [Source: URL] olmalı
- Anlaşmazlıklar şeffaf açıklanmalı
- Mutabakat oranı istatistikleri
- Genel güven değerlendirmesi
"""

# ═══════════════════════════════════════════════════════════
# NEW: LATEX GENERATION (Claude Judge)
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT_LATEX_GENERATOR = """You are an Academic LaTeX Document Generator

ROLE: Markdown konsensus raporunu yayın kalitesinde LaTeX'e çevir

DOCUMENT SPECIFICATIONS:
- Document Class: \\documentclass[11pt,a4paper]{article}
- Margins: 1 inch (geometry package)
- Style: Tek sütun, IEEE benzeri ama basit
- Font: Varsayılan Computer Modern
- Citations: Numaralı stil (inline \\bibitem)

REQUIRED PACKAGES (Minimal):
\\usepackage[utf8]{inputenc}
\\usepackage[margin=1in]{geometry}
\\usepackage{amsmath}
\\usepackage{graphicx}
\\usepackage{hyperref}
\\usepackage[numbers]{natbib}

DOCUMENT STRUCTURE:
1. Title, Author (Research Consensus Machine), Date
2. Abstract (2-3 cümle özet)
3. \\section{Introduction} - Araştırma sorusu bağlamı
4. \\section{Methodology} - Kısa dual-LLM mutabakat açıklaması
5. \\section{Findings} - Ana mutabakat iddiaları
6. \\section{Disputed Claims} - Anlaşmazlıklar (şeffaflık)
7. \\section{Conclusion} - Özet ve güven seviyesi
8. \\begin{thebibliography}{99} ... \\end{thebibliography}

CRITICAL RULES:
✓ SADECE yukarıdaki paketleri kullan (egzotik paket YOK)
✓ Özel karakterleri escape et: $, &, %, #, _, {, }, ~, ^, \\
✓ URL'ler için \\texttt{} kullan
✓ Formülleri basit tut (karmaşık TikZ/custom macro YOK)

FORBIDDEN:
✗ \\usepackage{fullpage} KULLANMA (geometry kullan)
✗ Grafik/resim ekleme (\\includegraphics YOK)
✗ Custom komut (\\newcommand YOK)
✗ BibTeX/biblatex (inline bibliography kullan)

OUTPUT FORMAT:
Sadece tam LaTeX kaynak kodu, \\documentclass ile başla \\end{document} ile bitir.
Markdown code block YOK, açıklama YOK, sadece LaTeX.
"""

# ═══════════════════════════════════════════════════════════
# NEW: VISUAL QA (Gemini Vision)
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT_VISUAL_QA = """You are a Visual Quality Assessor for Academic PDFs

ROLE: PDF sayfa görsellerini analiz et, düzgün render olmuş mu kontrol et

EVALUATION CRITERIA (Her biri 0-100):
1. Layout Quality (25 puan):
   - Uygun margin ve whitespace
   - Tutarlı satır aralığı
   - Section hizalanması
   - Metin overflow/clipping YOK

2. Typography (25 puan):
   - Font düzgün render (bozulma YOK)
   - Matematik formülleri doğru görünüyor
   - Tutarlı font boyutları
   - Okunabilir (ne çok küçük ne çok büyük)

3. Tables & Figures (25 puan):
   - Tablolar düzgün formatlanmış
   - Border'lar ve çizgiler görünüyor
   - İçerik sınırlar içinde
   - Caption'lar var ve hizalı

4. Professional Appearance (25 puan):
   - Temiz, akademik görünüm
   - Render hatası/artifact YOK
   - Uygun sayfa geçişleri
   - Header/footer tutarlılığı

OUTPUT FORMAT (JSON):
{
  "score": <0-100>,
  "feedback": "<Detaylı açıklama>",
  "criteria_scores": {
    "layout": <0-25>,
    "typography": <0-25>,
    "tables_figures": <0-25>,
    "professional": <0-25>
  }
}

SCORING GUIDE:
90-100: Yayın kalitesi, mükemmel
75-89: İyi kalite, küçük iyileştirmeler mümkün
60-74: Kabul edilebilir ama revizyon gerekli
0-59: Ciddi sorunlar, regenerate gerekli
"""

# ═══════════════════════════════════════════════════════════
# NEW: CONTENT QA (Claude Judge)
# ═══════════════════════════════════════════════════════════

SYSTEM_PROMPT_CONTENT_QA = """You are a Content Quality Assessor for Academic PDFs

ROLE: PDF'den çıkarılan metni analiz et, içerik bütünlüğü ve tamlığı kontrol et

EVALUATION CRITERIA (Her biri 0-100):
1. Completeness (30 puan):
   - Tüm konsensus iddiaları dahil
   - Eksik section YOK
   - Bibliography tam ve mevcut
   - Abstract ve conclusion var

2. Citation Accuracy (30 puan):
   - Tüm iddialarda atıf var
   - Citation numaraları bibliography ile eşleşiyor
   - URL'ler bibliography'de mevcut
   - Sahipsiz citation YOK

3. Structural Integrity (20 puan):
   - Düzgün section hiyerarşisi
   - Mantıksal akış
   - Metin bozulması/encoding hatası YOK
   - Paragraflar düzgün formatlanmış

4. Academic Standards (20 puan):
   - Profesyonel dil
   - Tutarlı terminoloji
   - Düzgün gramer ve yazım
   - Akademik kurallara uygun

OUTPUT FORMAT (JSON):
{
  "score": <0-100>,
  "feedback": "<Detaylı açıklama>",
  "criteria_scores": {
    "completeness": <0-30>,
    "citations": <0-30>,
    "structure": <0-20>,
    "academic": <0-20>
  }
}

SCORING GUIDE:
90-100: Mükemmel, yayın için hazır
75-89: İyi, küçük iyileştirmeler mümkün
60-74: Kabul edilebilir ama revizyon gerekli
0-59: Ciddi sorunlar, regenerate gerekli
"""
```

---

## 🧠 Core Algorithms (5 Ana Faz + PDF Pipeline)

### Faz 1: Grounding (Veri Çapalama - V1/V2 Mode)

```python
from tavily import TavilyClient
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def phase_1_grounding(state: DebateState) -> DebateState:
    """
    Faz 1: Grounding (Mode-Aware)

    LOGIC:
    1. Offline (V1) → No search, use internal knowledge
    2. Internet (V2) → TAVILY search (NOT DuckDuckGo)
    3. Auto → Keyword-based decision

    Girdi: state.topic + state.research_mode
    İşlem: Mode'a göre Tavily veya internal knowledge
    Çıktı: state.shared_context (Değişmez Gerçek)
    """

    current_mode = state.research_mode

    # ═══════════════════════════════════════════════════════
    # AUTO MODE: Keyword-based decision
    # ═══════════════════════════════════════════════════════

    if current_mode == "auto":
        time_sensitive_keywords = [
            "news", "price", "current", "latest", "bugün", "fiyat",
            "haber", "2024", "2025", "2026", "güncel", "recent", "today"
        ]

        if any(k in state.topic.lower() for k in time_sensitive_keywords):
            current_mode = "internet"
            logger.info("🤖 Auto Mode → Internet (time-sensitive keywords detected)")
        else:
            current_mode = "offline"
            logger.info("🤖 Auto Mode → Offline (no time-sensitive keywords)")

    # ═══════════════════════════════════════════════════════
    # V1: OFFLINE MODE (No Search)
    # ═══════════════════════════════════════════════════════

    if current_mode == "offline":
        logger.info("⚡ V1 Mode: OFFLINE - Using Internal Knowledge Only")

        state.shared_context = f"""ARAŞTIRMA MODU: OFFLINE (V1 - Internal Knowledge)

Kullanıcı internet araması istemedi.

GÖREVİN:
- SADECE kendi iç bilgi birikimini kullan (training data)
- Güncel olmayan veri kullanabileceğini kullanıcıya BELİRT
- Kaynak olarak "Internal Knowledge" veya "Training Data (pre-{datetime.now().year})" yaz

UYARI:
Bu modda güncel fiyat, haber veya real-time bilgi SAĞLANAMAZ.
"""

        return state

    # ═══════════════════════════════════════════════════════
    # V2: INTERNET MODE (TAVILY FORCED)
    # ═══════════════════════════════════════════════════════

    logger.info(f"🌐 V2 Mode: INTERNET - Searching TAVILY for: {state.topic}")

    try:
        # Initialize TAVILY (NOT DuckDuckGo!)
        tavily = TavilyClient(api_key=config.TAVILY_API_KEY)

        # Execute search
        logger.info("Querying Tavily API...")
        response = tavily.search(
            query=state.topic,
            search_depth="advanced",
            max_results=5,
            include_domains=["edu", "gov", "org"],
            exclude_domains=["pinterest.com", "quora.com"]
        )

        # Validate response
        if not response or 'results' not in response:
            raise ValueError("Tavily returned empty response")

        results = response.get('results', [])
        if len(results) == 0:
            raise ValueError("No sources found")

        # Parse sources
        sources = []
        context_parts = []

        for idx, result in enumerate(results, 1):
            content = result.get('content', '')
            url = result.get('url', '')
            title = result.get('title', f'Source {idx}')
            score = result.get('score', 1.0)

            sources.append(Source(
                url=url,
                title=title,
                content=content,
                relevance_score=score
            ))

            context_parts.append(
                f"\n{'='*60}\n"
                f"SOURCE {idx}: {title}\n"
                f"URL: {url}\n"
                f"RELEVANCE: {score:.2f}\n"
                f"{'='*60}\n"
                f"{content}\n"
            )

        # Update state
        state.web_context = WebContext(
            sources=sources,
            combined_text="".join(context_parts),
            search_query=state.topic,
            total_sources=len(sources)
        )

        state.shared_context = state.web_context.combined_text

        logger.info(f"✅ Tavily search complete: {len(sources)} sources")

        return state

    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        state.errors.append(f"Tavily error: {str(e)}")

        # FALLBACK: Use offline mode
        logger.warning("Falling back to offline mode")
        state.shared_context = f"""[FALLBACK - Tavily API Error]

Tavily araması başarısız: {str(e)}

Internal knowledge kullanılıyor (offline mode fallback).
"""

        return state
```

### Faz 2: Parallel Drafting (Paralel Taslak)

```python
import asyncio

async def phase_2_parallel_drafting(state: DebateState) -> DebateState:
    """
    Faz 2: Parallel Drafting (İzolasyon İçinde Taslak)

    AMAÇ: "Bias" (Önyargı) izolasyonu sağlamak
    - Agent A ve Agent B birbirinden BAĞIMSıZ çalışır
    - İkisi de aynı shared_context'i kullanır
    - Biri diğerinin çıktısını görmez (zero contamination)

    İşlem: Her iki ajan da soruyu bağımsız cevaplar
    Çıktı: state.gemini_draft ve state.claude_draft
    """

    logger.info(f"Faz 2: Parallel Drafting (Isolation Mode)")

    if not state.shared_context:
        raise ValueError("Cannot draft without grounding (shared_context)")

    # Prepare prompt (same for both)
    context_prompt = f"""Araştırma Sorusu: {state.topic}

Web Kaynaklarından Elde Edilen Bilgiler (Değişmez Gerçek):
{state.shared_context}

Görev:
- Soruyu bu kaynaklara dayanarak cevapla
- Her iddia için [Source: <detay>] formatında kaynak belirt
- Kapsamlı ol ama sadece kaynaklarda olanı yaz
- Speküle etme, kendi bilgini kullanma

Cevabını yaz:"""

    # Execute in parallel (asyncio)
    try:
        gemini_task = asyncio.create_task(
            call_gemini_api(context_prompt, SYSTEM_PROMPT_GEMINI_EXPLORER)
        )

        claude_task = asyncio.create_task(
            call_claude_api(context_prompt, SYSTEM_PROMPT_CLAUDE_JUDGE)
        )

        # Await both
        gemini_draft, claude_draft = await asyncio.gather(
            gemini_task,
            claude_task,
            return_exceptions=True
        )

        # Handle errors
        if isinstance(gemini_draft, Exception):
            logger.error(f"Gemini draft failed: {gemini_draft}")
            gemini_draft = "[ERROR] Gemini draft unavailable"
            state.errors.append(f"Gemini error: {str(gemini_draft)}")

        if isinstance(claude_draft, Exception):
            logger.error(f"Claude draft failed: {claude_draft}")
            claude_draft = "[ERROR] Claude draft unavailable"
            state.errors.append(f"Claude error: {str(claude_draft)}")

        # Update state
        state.gemini_draft = gemini_draft
        state.claude_draft = claude_draft
        state.iteration_counter = 0  # Initialize counter

        logger.info(f"✅ Parallel drafts complete")
        logger.info(f"   Explorer (Gemini): {len(gemini_draft)} chars")
        logger.info(f"   Judge (Claude): {len(claude_draft)} chars")

        return state

    except Exception as e:
        logger.critical(f"Parallel drafting failed: {e}")
        state.errors.append(f"Critical drafting error: {str(e)}")
        raise
```

### Faz 3: Cross-Examination (Çapraz Sorgu - Acımasız)

```python
def phase_3_cross_examination(state: DebateState) -> DebateState:
    """
    Faz 3: Cross-Examination (Çapraz Sorgu)

    PHILOSOPHY: "Nezaket değil, Acımasızlık"
    - Her ajan diğerinin taslağını SERT eleştirir
    - Zayıf kanıt, mantık hatası, spekülatif iddia → Acımasızca işaretle
    - Amaç: Karşılıklı eleştiri ile kaliteyi artırmak

    Logic:
    - Agent A (Explorer), Agent B'nin (Judge) taslağını okur:
      "Senin şu iddian kaynaklarda yok, kanıtla."
    - Agent B (Judge), Agent A'nın (Explorer) taslağını okur:
      "Bu mantık zinciri hatalı, şurayı düzelt."

    İşlem: Her ajan critique + revised_answer üretir
    Çıktı: state.gemini_critique, state.claude_critique
           state.gemini_draft (updated), state.claude_draft (updated)
    """

    state.iteration_counter += 1
    logger.info(f"Faz 3: Cross-Examination (Round {state.iteration_counter})")

    # Gemini critiques Claude
    gemini_critique_prompt = PROMPT_TEMPLATE_CRITIQUE.format(
        other_agent_draft=state.claude_draft,
        web_context=state.shared_context,
        own_draft=state.gemini_draft
    )

    # Claude critiques Gemini
    claude_critique_prompt = PROMPT_TEMPLATE_CRITIQUE.format(
        other_agent_draft=state.gemini_draft,
        web_context=state.shared_context,
        own_draft=state.claude_draft
    )

    try:
        # Call both agents
        gemini_response = call_gemini_api(
            gemini_critique_prompt,
            SYSTEM_PROMPT_GEMINI_EXPLORER
        )

        claude_response = call_claude_api(
            claude_critique_prompt,
            SYSTEM_PROMPT_CLAUDE_JUDGE
        )

        # Parse responses (CRITIQUE + REVISED_ANSWER)
        gemini_critique, gemini_revised = parse_critique_response(
            gemini_response,
            "Gemini Explorer"
        )

        claude_critique, claude_revised = parse_critique_response(
            claude_response,
            "Claude Judge"
        )

        # Update state
        state.gemini_critique = gemini_critique
        state.claude_critique = claude_critique
        state.gemini_draft = gemini_revised
        state.claude_draft = claude_revised

        logger.info(f"✅ Cross-examination complete (Round {state.iteration_counter})")

        return state

    except Exception as e:
        logger.error(f"Cross-examination failed: {e}")
        state.errors.append(f"Round {state.iteration_counter} critique error: {str(e)}")

        # Graceful degradation: Keep previous drafts
        logger.warning("Using previous drafts due to critique failure")
        return state

def parse_critique_response(response: str, agent_name: str) -> tuple[str, str]:
    """
    Parse CRITIQUE + REVISED_ANSWER format

    Expected:
    CRITIQUE:
    ...

    REVISED_ANSWER:
    ...

    Returns: (critique_text, revised_draft)
    """

    try:
        if "CRITIQUE:" in response and "REVISED_ANSWER:" in response:
            parts = response.split("REVISED_ANSWER:", 1)
            critique = parts[0].replace("CRITIQUE:", "").strip()
            revised = parts[1].strip()
            return critique, revised

        elif "CRITIQUE:" in response:
            parts = response.split("CRITIQUE:", 1)
            sections = parts[1].split("\n\n", 1)
            critique = sections[0].strip()
            revised = sections[1].strip() if len(sections) > 1 else response
            return critique, revised

        else:
            logger.warning(f"{agent_name} did not follow format")
            return f"[No structured critique from {agent_name}]", response

    except Exception as e:
        logger.error(f"Parse failure for {agent_name}: {e}")
        return "[Parse error]", response
```

### Faz 4: Convergence Check (Mutabakat Kontrolü)

```python
def phase_4_convergence_check(state: DebateState) -> DebateState:
    """
    Faz 4: Convergence Check

    TERMINATION LOGIC (Sonlandırma Kriterleri):
    1. Doğal Mutabakat: Semantic similarity >= threshold (e.g., 95%)
    2. Zorunlu Bitiş: iteration_counter >= max_rounds (e.g., 3)

    İşlem: İki taslak arasındaki semantic benzerliği hesapla
    Karar: Devam mı, bitir mi?
    """

    logger.info(f"Faz 4: Convergence Check (Round {state.iteration_counter})")

    try:
        # Calculate semantic similarity (LLM-based)
        similarity = semantic_similarity_llm(
            state.gemini_draft,
            state.claude_draft
        )

        state.similarity_score = similarity

        logger.info(f"Semantic Similarity: {similarity:.1%}")
        logger.info(f"Threshold: {state.convergence_threshold:.1%}")

        # Check termination conditions
        if similarity >= state.convergence_threshold:
            # Natural consensus
            state.converged = True
            state.forced_stop = False
            logger.info(f"✅ DOĞAL MUTABAKAT (Natural Consensus) at {similarity:.1%}")

        elif state.iteration_counter >= state.max_rounds:
            # Forced stop
            state.converged = True
            state.forced_stop = True
            logger.warning(f"⚠️ ZORUNLU BITIS (Forced Stop) - Max rounds ({state.max_rounds}) reached")

        else:
            # Continue debate
            logger.info(f"🔄 Debate continues (Gap: {state.convergence_threshold - similarity:.1%})")

        return state

    except Exception as e:
        logger.error(f"Convergence check failed: {e}")
        state.errors.append(f"Convergence error: {str(e)}")

        # Conservative fallback: Force convergence
        state.converged = True
        state.forced_stop = True
        state.similarity_score = 0.0

        return state

def semantic_similarity_llm(text_a: str, text_b: str) -> float:
    """
    LLM-based semantic similarity

    Neden LLM?
    - String matching (difflib) semantik eşdeğerliği kaçırır
    - Embeddings yüzeysel
    - LLM mantıksal eşdeğerliği anlar

    Example:
    A: "Atatürk 1923'te Türkiye'yi kurdu"
    B: "Türkiye Cumhuriyeti 1923'te Mustafa Kemal tarafından kuruldu"

    String similarity: ~40%
    LLM similarity: ~95% (aynı gerçek, farklı kelimeler)
    """

    # Quick pre-filters
    if text_a.strip() == text_b.strip():
        return 1.0
    if not text_a.strip() or not text_b.strip():
        return 0.0

    prompt = f"""İki araştırma taslağını semantik (anlamsal) benzerlik açısından karşılaştır.

METIN A:
{text_a}

METIN B:
{text_b}

Karşılaştırma Kriterleri:
1. Faktüel Uyum (50%): Aynı gerçekleri mi söylüyorlar?
2. Mantıksal Tutarlılık (30%): Çelişki var mı?
3. Kanıt Gücü (20%): Her ikisi de kaynak kullanıyor mu?

IGNORE (Önemseme):
- Kelime seçimi farkları ("kurdu" vs "kuruldu")
- Cümle yapısı
- Yazım stili
- Sunum sırası

FOCUS (Odaklan):
- Semantik anlam (aynı gerçekler mi?)
- Mantıksal eşdeğerlik
- Faktüel örtüşme yüzdesi

SADECE 0-100 arası bir sayı ver (benzerlik yüzdesi):"""

    try:
        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=10,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.content[0].text.strip()

        import re
        match = re.search(r'\b(\d+)\b', text)

        if match:
            percentage = int(match.group(1))
            percentage = max(0, min(100, percentage))
            return percentage / 100.0
        else:
            logger.error(f"Could not parse similarity: {text}")
            return 0.5

    except Exception as e:
        logger.error(f"Similarity calculation failed: {e}")
        return 0.5
```

### Faz 5: Intersection Synthesis (Kesişim Sentezi - A ∩ B)

```python
def phase_5_intersection_synthesis(state: DebateState) -> DebateState:
    """
    Faz 5: Intersection Synthesis (Hakem Kararı)

    MATHEMATICAL TRUTH: Truth = A ∩ B

    Algorithm:
    1. İki taslağı karşılaştır
    2. SADECE her ikisinin de kesinlikle kabul ettiği iddiaları al
    3. Bir tarafın şüphe duyduğu, reddettiği veya bahsetmediği
       her türlü bilgiyi SİL
    4. Sonuç: %100 doğrulanmış "Saf Bilgi"

    Philosophy: "Şüphe varsa çıkar"
    """

    logger.info("Faz 5: Intersection Synthesis (Hakem Kararı)")

    consensus_prompt = f"""İki AI ajanı bu araştırma sorusu üzerinde debate yaptı.
Senin görevin: SADECE her ikisinin de kabul ettiği iddiaları çıkar.

Araştırma Sorusu: {state.topic}

Orijinal Web Kaynakları (Referans):
{state.shared_context}

Agent A (Explorer - Gemini) Taslağı:
{state.gemini_draft}

Agent B (Judge - Claude) Taslağı:
{state.claude_draft}

Kesişim Algoritması:
1. Her iki taslağı atomik iddialara ayır
2. Her iddia çifti için:
   - Semantik eşdeğerlik kontrolü
   - Her ikisi de kesin mi? (belirsiz dil YOK)
   - Kaynak desteği var mı?
   - HEPSİ ✓ ise → Konsensusa dahil et
   - HERHANGİ BİRİ ✗ ise → ÇIKART

═══════════════════════════════════════════════════════════
ZORUNLU OUTPUT FORMATI:
═══════════════════════════════════════════════════════════

# Konsensus Raporu (Intersection Report)

## Araştırma Sorusu
{state.topic}

## Kabul Edilen Gerçekler (A ∩ B)
[AGREED] <İddia 1> [Source: <detay>]
[AGREED] <İddia 2> [Source: <detay>]
...

## Anlaşmazlık Olan İddialar (Şeffaflık için)
[DISPUTED] <Konu>: Agent A der ki X, Agent B der ki Y
...

## İstatistikler
- Debate turları: {state.iteration_counter}
- Final benzerlik: {state.similarity_score:.1%}
- Konsensus oranı: <yüzde>
- Zorunlu bitiş mi? {state.forced_stop}

## Güven Değerlendirmesi
Overall Confidence: [HIGH/MEDIUM/LOW]

Açıklama: <Bu güven seviyesinin nedeni>

═══════════════════════════════════════════════════════════
"""

    try:
        client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4000,
            temperature=0.2,
            system=SYSTEM_PROMPT_SYNTHESIZER,
            messages=[{"role": "user", "content": consensus_prompt}]
        )

        consensus_text = response.content[0].text

        state.consensus_report = consensus_text

        logger.info(f"✅ Intersection synthesis complete")
        logger.info(f"   Report length: {len(consensus_text)} chars")

        return state

    except Exception as e:
        logger.error(f"Consensus extraction failed: {e}")
        state.errors.append(f"Consensus error: {str(e)}")

        # Fallback: Minimal report
        state.consensus_report = f"""# Konsensus Raporu (Hata)

## Araştırma Sorusu
{state.topic}

## Hata
Konsensus çıkarma başarısız: {str(e)}

## Agent Taslakları
Agent A: {len(state.gemini_draft)} chars
Agent B: {len(state.claude_draft)} chars
"""

        return state
```

---

## 🔄 LangGraph Workflow Implementation (UPDATED)

### Complete Graph with All Phases

```python
from langgraph.graph import StateGraph, END
from typing import Literal

def build_research_workflow() -> StateGraph:
    """
    Döngüsel Durum Makinesi (Cyclic State Machine)

    GRAPH STRUCTURE:

    START → grounding → parallel_drafting → cross_examination → convergence
                                                    ↑                 ↓
                                                    └─────NO──────────┘
                                                                  ↓ YES
                                                         intersection_synthesis
                                                                  ↓
                                                          latex_generation
                                                                  ↓
                                                          pdf_compilation
                                                                  ↓
                                                         quality_assurance
                                                                  ↓
                                                          approval_decision
                                                                  ↓
                                                      ┌───────────┴───────────┐
                                                      │                       │
                                                 [APPROVED]              [REJECTED]
                                                      │                       │
                                                     END                 pdf_revision
                                                                              ↓
                                                                       (loop to compilation)
    """

    workflow = StateGraph(DebateState)

    # ───────────────────────────────────────────────────────
    # Add all nodes
    # ───────────────────────────────────────────────────────

    # Original debate nodes (Faz 1-5)
    workflow.add_node("grounding", phase_1_grounding)
    workflow.add_node("parallel_drafting", phase_2_parallel_drafting)
    workflow.add_node("cross_examination", phase_3_cross_examination)
    workflow.add_node("convergence", phase_4_convergence_check)
    workflow.add_node("intersection_synthesis", phase_5_intersection_synthesis)

    # NEW: PDF generation nodes
    workflow.add_node("latex_generation", latex_generation_node)
    workflow.add_node("pdf_compilation", pdf_compilation_node)
    workflow.add_node("quality_assurance", quality_assurance_node)
    workflow.add_node("approval_decision", approval_decision_node)
    workflow.add_node("pdf_revision", pdf_revision_node)

    # ───────────────────────────────────────────────────────
    # Add sequential edges
    # ───────────────────────────────────────────────────────

    workflow.add_edge("grounding", "parallel_drafting")
    workflow.add_edge("parallel_drafting", "cross_examination")
    workflow.add_edge("cross_examination", "convergence")

    # Consensus → LaTeX → PDF pipeline
    workflow.add_edge("intersection_synthesis", "latex_generation")
    workflow.add_edge("latex_generation", "pdf_compilation")
    workflow.add_edge("pdf_compilation", "quality_assurance")
    workflow.add_edge("quality_assurance", "approval_decision")

    # Revision loop
    workflow.add_edge("pdf_revision", "pdf_compilation")

    # ───────────────────────────────────────────────────────
    # Add conditional edges (loops)
    # ───────────────────────────────────────────────────────

    # LOOP 1: Debate loop (Faz 2-4 döngüsü)
    def should_continue_debate(state: DebateState) -> Literal["intersection_synthesis", "cross_examination"]:
        if state.converged:
            return "intersection_synthesis"
        else:
            return "cross_examination"

    workflow.add_conditional_edges(
        source="convergence",
        path=should_continue_debate,
        path_map={
            "cross_examination": "cross_examination",
            "intersection_synthesis": "intersection_synthesis"
        }
    )

    # LOOP 2: PDF regeneration loop
    def should_regenerate_pdf(state: DebateState) -> Literal["pdf_revision", "end"]:
        if state.pdf_approved:
            return "end"
        else:
            # Check if we can regenerate
            if state.pdf_regeneration_count < 2:  # Max 2 regenerations
                return "pdf_revision"
            else:
                return "end"

    workflow.add_conditional_edges(
        source="approval_decision",
        path=should_regenerate_pdf,
        path_map={
            "pdf_revision": "pdf_revision",
            "end": END
        }
    )

    # ───────────────────────────────────────────────────────
    # Set entry point
    # ───────────────────────────────────────────────────────

    workflow.set_entry_point("grounding")

    return workflow.compile()

# ═══════════════════════════════════════════════════════════
# EXECUTION
# ═══════════════════════════════════════════════════════════

def run_research(topic: str, max_rounds: int = 3, threshold: float = 0.95):
    """
    Main entry point

    Args:
        topic: Research question
        max_rounds: Max debate rounds (Default: 3)
        threshold: Similarity threshold (Default: 95%)

    Returns:
        Final state with PDF path
    """

    initial_state = DebateState(
        topic=topic,
        max_rounds=max_rounds,
        convergence_threshold=threshold,
        start_time=datetime.now()
    )

    workflow = build_research_workflow()

    logger.info(f"Starting Research & Publishing Pipeline: {topic}")

    final_state = workflow.invoke(initial_state)

    final_state.end_time = datetime.now()
    duration = (final_state.end_time - final_state.start_time).total_seconds()

    logger.info(f"✅ Complete in {duration:.1f}s")
    logger.info(f"   PDF: {final_state.pdf_path}")
    logger.info(f"   QA: {final_state.average_qa_score:.1f}/100")

    return final_state
```

---

## 🎨 Streamlit UI (Turkish Interface)

```python
import streamlit as st

def main():
    st.set_page_config(
        page_title="Research & Publishing Machine",
        page_icon="🎓",
        layout="wide"
    )

    st.title("🎓 Research & Publishing Machine")
    st.markdown("**Çift-Ajan Mutabakat Sistemi → Akademik PDF**")
    st.markdown("*Truth = A ∩ B | Doğruluk = İki bağımsız zekanın ortak paydası*")

    st.markdown("---")

    # ───────────────────────────────────────────────────────
    # INPUT
    # ───────────────────────────────────────────────────────

    col1, col2 = st.columns([3, 1])

    with col1:
        topic = st.text_input(
            "Araştırma Sorusu",
            placeholder="Örn: Yapay zekanın tıp alanındaki uygulamaları nelerdir?",
            help="Araştırma sorunuzu buraya girin"
        )

    with col2:
        max_rounds = st.number_input(
            "Max Tur",
            min_value=1,
            max_value=5,
            value=3,
            help="Maksimum debate turu"
        )

    with st.expander("⚙️ Gelişmiş Ayarlar"):
        col_a, col_b = st.columns(2)

        with col_a:
            threshold = st.slider(
                "Mutabakat Eşiği (%)",
                min_value=85,
                max_value=99,
                value=95,
                help="Doğal mutabakat için benzerlik yüzdesi"
            )

        with col_b:
            qa_threshold = st.slider(
                "QA Eşiği",
                min_value=60,
                max_value=95,
                value=75,
                help="PDF kalite onay puanı"
            )

    research_button = st.button("🔍 Araştırmaya Başla", type="primary", use_container_width=True)

    st.markdown("---")

    # ───────────────────────────────────────────────────────
    # EXECUTION
    # ───────────────────────────────────────────────────────

    if research_button:
        if not topic:
            st.error("❌ Lütfen bir araştırma sorusu girin")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()

        with st.container():
            st.markdown("### 🔄 İşlem Akışı")

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

            phase_statuses = {}
            for idx, (icon, name) in enumerate(phases):
                with phase_cols[idx]:
                    phase_statuses[name] = st.empty()
                    phase_statuses[name].markdown(f"{icon}\n{name}")

        # Run workflow
        try:
            initial_state = DebateState(
                topic=topic,
                max_rounds=max_rounds,
                convergence_threshold=threshold / 100.0,
                start_time=datetime.now()
            )

            workflow = build_research_workflow()

            # Execute
            final_state = workflow.invoke(initial_state)

            # Update progress (simplified animation)
            for prog, phase, status in [
                (0.11, "Arama", "🟢"),
                (0.22, "Taslak", "🟢"),
                (0.44, "Debate", "🟢"),
                (0.56, "Mutabakat", "🟢"),
                (0.67, "LaTeX", "🟢"),
                (0.78, "Derle", "🟢"),
                (0.89, "QA", "🟢"),
                (0.95, "Onayla", "🟢"),
                (1.0, "Bitti", "🟢")
            ]:
                progress_bar.progress(prog)
                status_text.text(f"İşleniyor: {phase}...")
                phase_statuses[phase].markdown(f"{status}\n{phase}")
                time.sleep(0.3)

            # ───────────────────────────────────────────────────────
            # RESULTS
            # ───────────────────────────────────────────────────────

            st.markdown("---")
            st.markdown("## 📊 Sonuçlar")

            # Statistics
            metric_cols = st.columns(5)

            with metric_cols[0]:
                st.metric("Debate Turları", final_state.iteration_counter)

            with metric_cols[1]:
                st.metric("Mutabakat", f"{final_state.similarity_score:.1%}")

            with metric_cols[2]:
                st.metric("QA Puanı", f"{final_state.average_qa_score:.1f}/100")

            with metric_cols[3]:
                st.metric("LaTeX Retry", final_state.latex_retry_count)

            with metric_cols[4]:
                st.metric("PDF Regeneration", final_state.pdf_regeneration_count)

            # PDF Display
            st.markdown("### 📄 Final PDF")

            if final_state.pdf_path:
                with open(final_state.pdf_path, "rb") as pdf_file:
                    pdf_bytes = pdf_file.read()

                    col_pdf, col_download = st.columns([3, 1])

                    with col_pdf:
                        st.markdown(f"**Dosya:** `{os.path.basename(final_state.pdf_path)}`")

                    with col_download:
                        st.download_button(
                            label="📥 PDF İndir",
                            data=pdf_bytes,
                            file_name=f"research_{int(time.time())}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

                    # PDF Preview
                    import base64
                    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)

            # Consensus Report
            with st.expander("📝 Konsensus Raporu (Markdown)"):
                st.markdown(final_state.consensus_report)

            # Errors
            if final_state.errors:
                with st.expander("⚠️ Hata Logu"):
                    for idx, error in enumerate(final_state.errors, 1):
                        st.warning(f"{idx}. {error}")

            st.success("✅ Araştırma başarıyla tamamlandı!")

        except Exception as e:
            st.error(f"❌ Hata: {str(e)}")
            st.exception(e)

if __name__ == "__main__":
    main()
```

---

## 📋 Implementation Roadmap (FINAL)

### Phase 1: Core Debate System (8 hours)

**Hour 1-2:** Project setup + DuckDuckGo integration
**Hour 3-4:** Core schemas + prompts
**Hour 5-6:** Faz 1-5 implementation (grounding → synthesis)
**Hour 7-8:** LangGraph workflow + testing

### Phase 2: PDF Pipeline (6 hours)

**Hour 1-2:** LaTeX generation + compilation
**Hour 3-4:** Visual QA (Gemini Vision)
**Hour 5-6:** Content QA + regeneration loop

### Phase 3: Streamlit UI (4 hours)

**Hour 1-2:** Basic UI + progress tracking
**Hour 3-4:** PDF preview + polish

### Phase 4: Docker + Testing (2 hours)

**Hour 1:** Docker setup
**Hour 2:** Integration tests

**TOTAL: 20 hours for production-ready system**

---

## ✅ Definition of Done

**System MUST:**
- ✅ Accept Turkish/English questions
- ✅ V1 Mode: Offline (no search, no cost)
- ✅ V2 Mode: Tavily search (advanced depth)
- ✅ Auto Mode: Keyword-based decision
- ✅ Parallel isolated drafting
- ✅ Acımasız (strict) cross-examination
- ✅ Semantic similarity convergence (95% or max 3 rounds)
- ✅ Intersection synthesis (A ∩ B)
- ✅ LaTeX generation + PDF compilation
- ✅ Dual QA (Visual + Content)
- ✅ Regeneration loop (max 2x)
- ✅ Streamlit UI with PDF preview + mode selection
- ✅ <3 minutes execution
- ✅ <$0.25 per query (V2 mode)

**Quality:**
- ✅ %100 of consensus claims web-verifiable
- ✅ Zero hallucinations
- ✅ All claims cited
- ✅ PDF QA ≥75 or max regen
- ✅ No infinite loops

---

**Status:** ✅ FINAL SPECIFICATION - READY TO CODE

**This is THE COMPLETE, FINAL, ALIGNED SPECIFICATION.**

**Start coding NOW.**

---

*Version: 4.0 FINAL (Aligned with lastplan.md)*
*Last Updated: 2026-01-13*
*Philosophy: Truth = A ∩ B | Nezaket değil, Acımasızlık*
