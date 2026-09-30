# dual-llm-debate

Two LLMs from different vendors research the same question independently, debate each other's claims round by round, and a neutral referee distills their agreed claims into a LaTeX-compiled PDF report.

## What it is

A Python pipeline that answers a research question with two LLM agents instead of one. Gemini (default model `gemini-1.5-pro-latest`) plays the "Explorer" — broad, higher temperature (0.7) — and Claude (default model `claude-sonnet-4-5-20250929`) plays the "Judge" — strict, lower temperature (0.5). Both draft answers independently from the same evidence, then compare and revise claim by claim over several rounds. A referee stage (Claude at temperature 0.2) extracts a consensus report, which is rendered to an academic-style PDF through LaTeX and passed through an automated quality-assurance step. The project's working slogan, repeated across the code and the UI, is `Truth = A ∩ B`.

The pipeline is orchestrated as a LangGraph state machine (`src/workflow.py`) over a shared Pydantic `DebateState` (`src/schemas.py`) and driven from a Streamlit web UI (`app.py`, Turkish-language interface).

## Why it exists

A single model's answer inherits that model's blind spots. This project is an experiment in reducing that risk through cross-model consensus: if two independently prompted models from different vendors, given the same sources, both assert a claim, that claim is kept and anything only one asserts is meant to be dropped. This trades coverage for confidence rather than making the output hallucination-proof. The debate protocol evolved during development from an adversarial "devil's advocate / cross-examination" design to the current collaborative-convergence one; the old implementation has been removed, and the `*PLAN*.md` / `IMPLEMENTATION_SUMMARY.md` files are kept as historical design snapshots.

## How it works

The workflow builds a LangGraph `StateGraph` with these nodes: `grounding → parallel_drafting → iterative_debate → intersection_synthesis → latex_generation → pdf_compilation → quality_assurance → approval_decision`, plus a conditional `pdf_revision` edge that loops back to `latex_generation`.

1. **Grounding** (`src/phases/phase_1_grounding.py`) — three modes: `offline` (model knowledge only), `internet`, or `auto`. In auto mode a keyword check (`TIME_SENSITIVE_KEYWORDS` in `src/config.py`, e.g. "news", "price", "2025", "güncel") picks internet vs offline. Internet mode queries the Tavily search API (advanced depth, up to 5 results, with `pinterest.com` and `quora.com` excluded) and packs the results into a shared context of numbered, URL-tagged sources. Any search error — including a missing Tavily key — is caught and falls back to offline mode.
2. **Parallel drafting** (`src/phases/phase_2_parallel_drafting.py`) — both agents answer the same question from the same shared context concurrently (`asyncio.gather`), with no visibility into each other's output. Their system prompts (`src/prompts.py`) require every claim to carry a `[Source: ...]` tag. Gemini runs at 0.7, Claude at 0.5.
3. **Iterative debate** (`src/phases/phase_3_4_iterative_debate.py`) — for up to `MAX_ROUNDS` rounds (default 3), each agent is shown both agents' previous answers and must return a JSON block — a claim-by-claim comparison table marking each claim agree / partial / conflict, each with a 0–1 confidence and a source per side — followed by a plain-text revised answer. Claims that both agents mark "agree" with confidence at or above a per-round threshold (0.70 in round 1, 0.80 in round 2, 0.85 thereafter) are recorded as "locked"; from the next round on the agents are instructed to respect locked claims and focus on the disputed points. Four metrics are computed each round — a symmetric, intersection-based consensus plus each agent's individual coverage and their average — and the debate converges only when all four reach the convergence threshold (default 0.95). Otherwise the loop runs to max rounds and sets a `forced_stop` flag.
4. **Intersection synthesis** (`src/phases/phase_5_intersection.py`) — Claude, acting as a neutral referee at temperature 0.2, is fed the debate's output: the locked-claim list (with sources and confidence), each agent's final revised answer from the last debate round, and the still-disputed points. Locked claims are treated as the pre-verified backbone of the report and must all be included; additional claims are admitted only if both revised answers assert them with source support; disputed points are excluded outright ("when in doubt, exclude"). The pre-debate Phase-2 drafts are used only if no debate round was recorded.
5. **LaTeX generation** (`src/agents/latex_generator.py`) — Claude converts the consensus report into an article-class LaTeX document with Turkish `babel` support. A `strip_citations()` pass then removes all `\cite`/`\citep`/`\citet` commands, inline `[n]` reference numbers, `natbib`, and any bibliography/References section.
6. **PDF compilation** (`src/agents/pdf_compiler.py`) — writes the LaTeX into a temp directory and runs `pdflatex -interaction=nonstopmode` twice; the whole compile is retried up to `MAX_LATEX_RETRIES` times (default 3) with a per-run timeout (`LATEX_TIMEOUT`, default 30s). Only the resulting PDF is copied into `./output/pdfs`.
7. **Quality assurance and approval** (`src/agents/qa_agents.py`) — Gemini Vision scores the *first* rendered page image (layout, typography, tables/figures, professional appearance) and Claude scores the extracted PDF text (question completeness, citation accuracy, structure, academic standards). If the average of the two scores is below `QA_THRESHOLD` (default 75) the pipeline regenerates the LaTeX/PDF, up to `MAX_PDF_REGENERATIONS` times (default 2). QA failures are explicit: if a QA model errors or returns unparseable JSON, the run is marked `qa_failed` with zero scores, the PDF is *not* approved, and no regeneration is attempted (regeneration can't fix a QA infrastructure error) — there is no silent auto-approval. The PDF file still exists on disk either way; approval is a recorded verdict, not a gate on the file.

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

Tests (no API keys, LaTeX, or Poppler needed — the LLM calls are mocked):

```bash
pip install pytest
pytest tests/
```

The suite covers the debate's consensus math and claim locking, debate-response parsing (including the malformed-JSON fallbacks), the synthesis stage's inputs (locked claims + revised answers, not the pre-debate drafts), the explicit QA-failure path, and workflow graph compilation.

Docker (installs TeX Live packages and Poppler for you):

```bash
docker compose up --build
```

Configuration is environment-driven; `.env.example` lists every setting: model IDs (`CLAUDE_MODEL`, `GEMINI_MODEL`), `MAX_ROUNDS`, `CONVERGENCE_THRESHOLD`, `QA_THRESHOLD`, `DEFAULT_RESEARCH_MODE`, `LATEX_TIMEOUT`, `MAX_LATEX_RETRIES`, `MAX_PDF_REGENERATIONS`, and the output directories. Temperatures and token limits are hard-coded in `src/config.py`, not exposed as env vars.

## Status & caveats

A personal, experimental prototype. Remaining limitations visible in the code:

- **Debate JSON parsing is fragile.** Agents must emit strict JSON plus free text; `parse_comparison_response` falls back to regex when the JSON is malformed, and that fallback pegs a claim's consensus at 0.5 when no score can be recovered from the text. Because convergence needs all four metrics at or above 0.95, a fallback essentially guarantees the round cannot converge, so such runs end at max rounds ("forced stop"). The fallback behavior itself is covered by tests.
- **The final PDF has no citations, by design.** Sources are required in the drafts and debate tables, but `strip_citations()` removes all citation markers, reference numbers, and bibliographies from the final LaTeX.
- **Language.** The UI and most user-facing prompts are Turkish; reports compile with Turkish `babel` support. Agent system prompts are a mix of English scaffolding and Turkish instructions.
- **Design docs are historical.** `PLAN.md`, `MASTERPLAN.md`, `IMPLEMENTATION_SUMMARY.md` and `CONSENSUS_SYSTEM.md` are mid-development snapshots (marked as such) and describe some designs that were later changed or dropped; the README and the code are authoritative.
- **Dependency age.** `langgraph` is pinned to an old release (`0.0.32`), and the default `gemini-1.5-pro-latest` model id may need updating for a given account.

Previously documented gaps that have since been fixed (see git history): the synthesis stage now consumes the debate's locked claims and final revised answers instead of the pre-debate drafts; QA errors now fail the run explicitly instead of auto-approving with a default score of 85; the dead adversarial-protocol code (cross-examination/convergence phases, devil's-advocate prompts, unused citation validator, root-level ad-hoc scripts) has been removed; and a pytest suite now covers the consensus math, parsing fallbacks, synthesis inputs, and QA failure paths.

## License

MIT — Copyright (c) 2026 Kerem Gür. See [LICENSE](LICENSE).
