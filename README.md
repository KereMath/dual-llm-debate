# dual-llm-debate

Two LLMs from different vendors research the same question independently, debate each other's claims round by round, and a neutral referee distills their agreed claims into a LaTeX-compiled PDF report.

## What it is

A Python pipeline that answers a research question with two LLM agents instead of one. Gemini (default model `gemini-1.5-pro-latest`) plays the "Explorer" — broad, higher temperature (0.7) — and Claude (default model `claude-sonnet-4-5-20250929`) plays the "Judge" — strict, lower temperature (0.5). Both draft answers independently from the same evidence, then compare and revise claim by claim over several rounds. A referee stage (Claude at temperature 0.2) extracts a consensus report, which is rendered to an academic-style PDF through LaTeX and passed through an automated quality-assurance step. The project's working slogan, repeated across the code and the UI, is `Truth = A ∩ B`.

The pipeline is orchestrated as a LangGraph state machine (`src/workflow.py`) over a shared Pydantic `DebateState` (`src/schemas.py`) and driven from a Streamlit web UI (`app.py`, Turkish-language interface).

## Why it exists

A single model's answer inherits that model's blind spots. This project is an experiment in reducing that risk through cross-model consensus: if two independently prompted models from different vendors, given the same sources, both assert a claim, that claim is kept and anything only one asserts is meant to be dropped. This trades coverage for confidence rather than making the output hallucination-proof. The debate protocol has changed over time — the repo still carries an older adversarial "devil's advocate / cross-examination" implementation alongside the current collaborative-convergence one (see Status & caveats).

## How it works

The workflow builds a LangGraph `StateGraph` with these nodes: `grounding → parallel_drafting → iterative_debate → intersection_synthesis → latex_generation → pdf_compilation → quality_assurance → approval_decision`, plus a conditional `pdf_revision` edge that loops back to `latex_generation`.

1. **Grounding** (`src/phases/phase_1_grounding.py`) — three modes: `offline` (model knowledge only), `internet`, or `auto`. In auto mode a keyword check (`TIME_SENSITIVE_KEYWORDS` in `src/config.py`, e.g. "news", "price", "2025", "güncel") picks internet vs offline. Internet mode queries the Tavily search API (advanced depth, up to 5 results, with `pinterest.com` and `quora.com` excluded) and packs the results into a shared context of numbered, URL-tagged sources. Any search error — including a missing Tavily key — is caught and falls back to offline mode.
2. **Parallel drafting** (`src/phases/phase_2_parallel_drafting.py`) — both agents answer the same question from the same shared context concurrently (`asyncio.gather`), with no visibility into each other's output. Their system prompts (`src/prompts.py`) require every claim to carry a `[Source: ...]` tag. Gemini runs at 0.7, Claude at 0.5.
3. **Iterative debate** (`src/phases/phase_3_4_iterative_debate.py`) — for up to `MAX_ROUNDS` rounds (default 3), each agent is shown both agents' previous answers and must return a JSON block — a claim-by-claim comparison table marking each claim agree / partial / conflict, each with a 0–1 confidence and a source per side — followed by a plain-text revised answer. Claims that both agents mark "agree" with confidence at or above a per-round threshold (0.70 in round 1, 0.80 in round 2, 0.85 thereafter) are recorded as "locked"; from the next round on the agents are instructed to respect locked claims and focus on the disputed points. Four metrics are computed each round — a symmetric, intersection-based consensus plus each agent's individual coverage and their average — and the debate converges only when all four reach the convergence threshold (default 0.95). Otherwise the loop runs to max rounds and sets a `forced_stop` flag.
4. **Intersection synthesis** (`src/phases/phase_5_intersection.py`) — Claude, acting as a neutral referee at temperature 0.2, is asked to keep only claims both drafts assert, stated without hedging and supported by the sources; anything one-sided, uncertain, or contradicted is meant to be excluded ("when in doubt, exclude").
5. **LaTeX generation** (`src/agents/latex_generator.py`) — Claude converts the consensus report into an article-class LaTeX document with Turkish `babel` support. A `strip_citations()` pass then removes all `\cite`/`\citep`/`\citet` commands, inline `[n]` reference numbers, `natbib`, and any bibliography/References section.
6. **PDF compilation** (`src/agents/pdf_compiler.py`) — writes the LaTeX into a temp directory and runs `pdflatex -interaction=nonstopmode` twice; the whole compile is retried up to `MAX_LATEX_RETRIES` times (default 3) with a per-run timeout (`LATEX_TIMEOUT`, default 30s). Only the resulting PDF is copied into `./output/pdfs`.
7. **Quality assurance and approval** (`src/agents/qa_agents.py`) — Gemini Vision scores the *first* rendered page image (layout, typography, tables/figures, professional appearance) and Claude scores the extracted PDF text (question completeness, citation accuracy, structure, academic standards). If the average of the two scores is below `QA_THRESHOLD` (default 75) the pipeline regenerates the LaTeX/PDF, up to `MAX_PDF_REGENERATIONS` times (default 2). QA is intentionally non-blocking: if a QA model's JSON can't be parsed or the call errors, that stage auto-approves with a default score of 85, so a PDF is essentially always produced.

Supporting modules: `src/api_clients.py` wraps the Anthropic and `google-genai` SDKs with `tenacity` retry/backoff and enables Google Search grounding on the (text) Gemini calls; `src/prompts.py` holds every agent persona and the debate handshake prompt; `src/schemas.py` defines `DebateState` and the `DebateRound` / `ComparisonClaim` / `LockedClaim` records.

## Building & running

Prerequisites:

- Python 3.11 (the Docker image is `python:3.11-slim`; `SETUP_GUIDE.md` targets 3.11+)
- A LaTeX distribution providing `pdflatex` (TeX Live or MiKTeX) — the compiler raises `"pdflatex not found. Please install TeX Live or MiKTeX."` if it is missing
- Poppler utilities (`pdf2image` uses them to rasterize the PDF for visual QA)
- API keys: `ANTHROPIC_API_KEY` and `GOOGLE_API_KEY` are always required; `TAVILY_API_KEY` is additionally required for `internet` and `auto` modes (`config.validate_api_keys`)

Local run:

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY, GOOGLE_API_KEY, TAVILY_API_KEY
streamlit run app.py
```

The UI serves on `http://localhost:8501`. Compiled PDFs are written to `./output/pdfs` and run logs to `./output/logs` (the generated LaTeX source is compiled in a temporary directory and is not persisted).

Docker (installs TeX Live packages and Poppler for you):

```bash
docker compose up --build
```

Configuration is environment-driven; `.env.example` lists every setting: model IDs (`CLAUDE_MODEL`, `GEMINI_MODEL`), `MAX_ROUNDS`, `CONVERGENCE_THRESHOLD`, `QA_THRESHOLD`, `DEFAULT_RESEARCH_MODE`, `LATEX_TIMEOUT`, `MAX_LATEX_RETRIES`, `MAX_PDF_REGENERATIONS`, and the output directories. Temperatures and token limits are hard-coded in `src/config.py`, not exposed as env vars.

## Status & caveats

A personal, experimental prototype, rough in several places. Limitations visible in the code:

- **Debate JSON parsing is fragile.** Agents must emit strict JSON plus free text; `parse_comparison_response` falls back to regex when the JSON is malformed, and that fallback pegs a claim's consensus at 0.5. Because convergence needs all four metrics at or above 0.95, a fallback essentially guarantees the round cannot converge, so such runs end at max rounds ("forced stop").
- **The debate's output is not what gets published.** `intersection_synthesis` is given the original Phase-2 drafts (`state.gemini_draft` / `state.claude_draft`), not the revised answers or the locked-claim list produced by the debate loop — those currently only drive the convergence check.
- **The final PDF has no citations, by design.** Sources are required in the drafts and debate tables, but `strip_citations()` removes all citation markers, reference numbers, and bibliographies from the final LaTeX.
- **QA can auto-approve.** On any QA JSON-parse failure or API error the visual/content scorer returns 85 and passes; the Streamlit sidebar states outright that QA will not block PDF generation.
- **Docs and code disagree on the convergence default.** The code default is `0.95` (`src/config.py` and `.env.example`); the design note `CONSENSUS_SYSTEM.md` discusses `0.85`. The code value is what runs.
- **Language.** The UI and most user-facing prompts are Turkish; reports compile with Turkish `babel` support. Agent system prompts are a mix of English scaffolding and Turkish instructions.
- **Dead / stray code.** `phase_3_cross_examination.py` and `phase_4_convergence.py`, plus the `DEVIL_ADVOCATE_STRICT` / `DEVIL_ADVOCATE_OPEN` and `PROMPT_TEMPLATE_CRITIQUE` prompts, are leftovers from the earlier adversarial protocol — still imported by `src/phases/__init__.py` but not used by the workflow, which runs the collaborative `run_debate_loop`. `src/utils/citation_validator.py` is unused (and would error, since it calls `call_claude_api` without the required `system_prompt`). `IMPLEMENTATION_SUMMARY.md` still describes some removed pieces as active. Ad-hoc scripts (`test_api.py`, `test_gemini_*.py`, `test_simple.py`, `list_models_new.py`) sit at the repo root; there is no automated test suite.
- **Dependency age.** Some pins are old (e.g. `langgraph==0.0.32`), and the default `gemini-1.5-pro-latest` model id may need updating for a given account.

## License

MIT — Copyright (c) 2026 Kerem Gür. See [LICENSE](LICENSE).
