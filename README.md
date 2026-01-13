# 🎓 Research & Publishing Machine

**Dual-LLM Debate System for Academic PDF Generation**

*Truth = A ∩ B | Doğruluk = İki bağımsız zekanın anlaşmazlık sonrası vardığı ortak paydadır*

---

## 📋 Overview

A state-of-the-art research system that uses **two frontier LLMs** (Claude Sonnet 4.5 & Gemini Pro 1.5) in an adversarial debate to generate **publication-ready academic PDFs** with verified, hallucination-free content.

### Key Features

- ✅ **Dual-Model Debate**: Two independent AI agents critique each other ruthlessly
- ✅ **Grounded Research**: V1 (Offline) or V2 (Tavily search) modes
- ✅ **Intersection Logic**: Only mutually agreed claims (A ∩ B) included
- ✅ **Academic PDF Output**: LaTeX → PDF with dual QA (Visual + Content)
- ✅ **Zero Hallucination**: All claims source-verified
- ✅ **Turkish & English**: Full bilingual support

---

## 🏗️ Architecture

### System Flow

```
User Question → [V1: Offline / V2: Tavily Search] →
Parallel Drafting (Isolated, no bias) →
Cross-Examination (Strict Critique - Ruthless) →
Iterative Revision (Fix or Defend) →
Intersection Synthesis (A ∩ B - Hakem) →
LaTeX Generation → PDF Compilation →
Visual QA (Gemini Vision) + Content QA (Claude Text) →
[APPROVED] → Final PDF | [REJECTED] → Regenerate (Max 2x)
```

### Agents

1. **Agent A - The Explorer** (Gemini Pro 1.5)
   - High creativity (temp=0.7)
   - Broad perspective, hypothesis generation
   - Finds connections and different angles

2. **Agent B - The Judge** (Claude Sonnet 4.5)
   - High precision (temp=0.5)
   - Analytical, critical, ruthless
   - Catches weak evidence and logic errors

3. **Hakem - The Referee** (Claude Sonnet 4.5)
   - Conservative intersection extractor (temp=0.2)
   - Philosophy: "When in doubt, exclude"
   - Outputs only A ∩ B (mutual agreement)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- LaTeX distribution (TeX Live or MiKTeX)
- API Keys:
  - Anthropic (Claude)
  - Google (Gemini)
  - Tavily (for V2 internet mode)

### Installation

1. **Clone the repository**
```bash
git clone <repo-url>
cd research-project-llm
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. **Run Streamlit app**
```bash
streamlit run app.py
```

6. **Open browser**: http://localhost:8501

---

## 🐳 Docker Deployment

### Build and Run

```bash
docker-compose up -d
```

### Access

- UI: http://localhost:8501
- Logs: `./output/logs/`
- PDFs: `./output/pdfs/`

---

## 📖 Usage

### Streamlit UI

1. Enter your research question (Turkish or English)
2. Select mode:
   - **Auto**: Keyword-based decision (recommended)
   - **Internet**: Always use Tavily search
   - **Offline**: Use only internal knowledge
3. Adjust debate parameters (max rounds, threshold)
4. Click "🔍 Araştır"
5. Download PDF when ready

### Python API

```python
from src import run_research, setup_logging

# Setup logging
setup_logging()

# Run research
final_state = run_research(
    topic="What are the applications of AI in medicine?",
    research_mode="auto",  # or "internet" or "offline"
    max_rounds=3,
    convergence_threshold=0.95
)

# Access results
print(f"PDF: {final_state.pdf_path}")
print(f"QA Score: {final_state.average_qa_score:.1f}/100")
print(f"Consensus: {final_state.similarity_score:.1%}")
```

---

## 🎯 Research Modes

### V1: Offline Mode
- **No internet search**
- Uses only LLM training data
- Fast, low-cost
- Best for: General knowledge, static topics

### V2: Internet Mode
- **Tavily API search** (advanced depth)
- Grounded in current web sources
- Higher cost, slightly slower
- Best for: Current events, recent data, specific facts

### Auto Mode (Recommended)
- **Keyword-based decision**
- Detects time-sensitive keywords (news, price, latest, 2024, etc.)
- Automatically switches between V1/V2
- Best for: General use

---

## 📊 Configuration

Edit `.env` file:

```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-xxx
GOOGLE_API_KEY=AIzaXXX
TAVILY_API_KEY=tvly-xxx

# Models
CLAUDE_MODEL=claude-sonnet-4-5-20250929
GEMINI_MODEL=gemini-1.5-pro-latest

# Debate Settings
MAX_ROUNDS=3
CONVERGENCE_THRESHOLD=0.95

# QA Settings
QA_THRESHOLD=75
MAX_PDF_REGENERATIONS=2
```

---

## 🔬 Technical Details

### State Machine

The system uses LangGraph's cyclic state graph:

- **Debate Loop**: Phases 2-4 repeat until convergence or max rounds
- **PDF Loop**: Regenerates if QA fails (max 2x)
- **State**: Single `DebateState` object passed through all nodes

### Key Algorithms

1. **Semantic Similarity** (LLM-based)
   - Claude evaluates semantic equivalence
   - Ignores surface form differences
   - Focuses on factual agreement

2. **Intersection Synthesis** (A ∩ B)
   - Conservative principle: "5 certain facts > 10 doubtful facts"
   - Excludes any claim with uncertainty
   - Requires mutual agreement + source support

3. **Dual QA**
   - Visual: Gemini Vision analyzes PDF page images
   - Content: Claude checks text completeness & citations
   - Average must pass threshold (default: 75/100)

---

## 📂 Project Structure

```
research-project-llm/
├── src/
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── schemas.py          # Pydantic models
│   ├── prompts.py          # All system prompts
│   ├── api_clients.py      # Claude & Gemini wrappers
│   ├── workflow.py         # LangGraph orchestration
│   ├── phases/             # 5 debate phases
│   │   ├── phase_1_grounding.py
│   │   ├── phase_2_parallel_drafting.py
│   │   ├── phase_3_cross_examination.py
│   │   ├── phase_4_convergence.py
│   │   └── phase_5_intersection.py
│   └── agents/             # PDF pipeline agents
│       ├── latex_generator.py
│       ├── pdf_compiler.py
│       └── qa_agents.py
├── output/
│   ├── pdfs/              # Generated PDFs
│   ├── latex/             # LaTeX source files
│   └── logs/              # Application logs
├── app.py                 # Streamlit UI
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── PLAN.md               # Original design document
└── README.md
```

---

## 🧪 Testing

### Manual Test

```bash
# Test offline mode
python -c "from src import run_research; run_research('Explain quantum computing', research_mode='offline')"

# Test internet mode
python -c "from src import run_research; run_research('Latest AI news 2024', research_mode='internet')"
```

### Check Output

```bash
ls -l output/pdfs/
```

---

## 🐛 Troubleshooting

### LaTeX Compilation Fails

**Problem**: `pdflatex not found`

**Solution**: Install LaTeX distribution
- **Linux**: `sudo apt-get install texlive-full`
- **macOS**: `brew install --cask mactex`
- **Windows**: Download MiKTeX from miktex.org

### API Key Errors

**Problem**: Missing or invalid API keys

**Solution**:
1. Check `.env` file exists
2. Verify key format (no quotes, no spaces)
3. Test keys individually

### PDF2Image Errors

**Problem**: `poppler not found`

**Solution**: Install Poppler
- **Linux**: `sudo apt-get install poppler-utils`
- **macOS**: `brew install poppler`
- **Windows**: Download from poppler.freedesktop.org

---

## 📈 Performance

**Typical Execution:**
- Debate: 2-3 minutes
- LaTeX generation: 10-20 seconds
- PDF compilation: 5-10 seconds
- QA: 20-30 seconds
- **Total: ~3-5 minutes**

**Cost (V2 Mode):**
- ~$0.15-0.25 per query
- Depends on: question complexity, debate rounds, regenerations

---

## 🔒 Security

- API keys stored in `.env` (never commit!)
- No user data persistence
- LaTeX sandboxed execution
- Output files isolated in `./output/`

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Streaming output (real-time progress)
- [ ] Multi-language support (beyond Turkish/English)
- [ ] Custom agent personalities
- [ ] Benchmark on academic datasets (TruthfulQA, FactScore)
- [ ] Cost optimization (caching, prompt compression)
- [ ] Performance optimization (async everything)

---

## 📄 License

MIT License - See LICENSE file

---

## 🙏 Acknowledgments

- **Anthropic** for Claude Sonnet 4.5
- **Google** for Gemini Pro 1.5
- **Tavily** for advanced search API
- **LangChain/LangGraph** for orchestration

---

## 📞 Contact

For issues and questions:
- GitHub Issues: [Create an issue]
- Documentation: See `PLAN.md` for detailed architecture

---

## 🎯 Roadmap

**v1.0** (Current)
- ✅ Core debate system
- ✅ PDF generation
- ✅ Dual QA
- ✅ Streamlit UI

**v1.1** (Planned)
- ⏳ Streaming responses
- ⏳ Multi-format export (Word, HTML)
- ⏳ Citation graph visualization

**v2.0** (Future)
- 🔮 Multi-agent (3+ models)
- 🔮 Specialized domain agents (medical, legal, etc.)
- 🔮 Interactive debate viewer

---

**Built with ❤️ using the power of adversarial AI debate**

*"Truth emerges when independent minds rigorously test each other's claims."*
#   r e s e a r c h - a g e n t  
 