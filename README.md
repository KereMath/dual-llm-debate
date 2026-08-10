# dual-llm-debate

Two LLMs research the same question independently, cross-examine each other's claims round by round, and only what both accept ends up in a LaTeX-compiled PDF report.

## What it is

A Python pipeline that answers a research question with two LLM agents instead of one. Gemini (default model: `gemini-1.5-pro-latest`) plays the "Explorer" (broad, higher temperature) and Claude (default model: `claude-sonnet-4-5-20250929`) plays the "Judge" (strict, lower temperature). Both draft answers independently from the same evidence, then debate each other claim by claim over multiple rounds. A referee stage extracts only the claims both agents accept — the project's working principle, stated in the code, is `Truth = A ∩ B` — and the result is rendered to an academic-style PDF through LaTeX, with an automated quality-assurance loop before approval.

The pipeline is orchestrated as a LangGraph state machine and driven from a Streamlit web UI (Turkish-language interface).

## Why it exists

A single model's answer inherits that model's hallucinations and blind spots. This project is an experiment in reducing that risk through cross-model consensus: if two independently prompted models from different vendors, given the same sources, both assert a claim with high confidence, that claim is more likely to be true — and anything only one of them asserts is dropped. This does not make the output hallucination-proof — it narrows the report to the intersection of what both models will defend, trading coverage for confidence. The repo's planning documents (`MASTERPLAN.md`, `PLAN.md`, `CONSENSUS_SYSTEM.md`) record the design iterations, including a move from a "devil's advocate" critique protocol to the current collaborative-convergence debate.

## How it works

The workflow (`src/workflow.py`) is a cyclic LangGraph `StateGraph` over a shared Pydantic `DebateState`:

1. **Grounding** (`src/phases/phase_1_grounding.py`) — three modes: `offline` (model knowledge only), `internet`, or `auto` (keyword heuristic decides). Internet mode queries the Tavily search API (advanced depth, top 5 results, some domains excluded) and packs the results into an immutable shared context of numbered, URL-tagged sources. Search failure falls back to offline mode.
2. **Parallel drafting** (`src/phases/phase_2_parallel_drafting.py`) — both agents answer the question independently and concurrently from the same shared context, with no visibility into each other's output. System prompts require every claim to carry a `[Source: URL]` tag. Gemini runs at temperature 0.7, Claude at 0.5.
3. **Iterative debate** (`src/phases/phase_3_4_iterative_debate.py`) — for up to `MAX_ROUNDS` rounds (default 3), each agent receives both previous answers and must return (a) a JSON comparison table scoring every claim as agree / partial / conflict with a 0–1 confidence and a source for each side, and (b) a revised answer. Claims that both agents mark "agree" with confidence above a per-round threshold (0.70, then 0.80, then 0.85) are **locked** and removed from further debate. Convergence requires four metrics — a symmetric intersection-based consensus, each agent's individual coverage, and their average — to all clear the threshold (default 0.95); otherwise the loop continues until max rounds ("forced stop").
4. **Intersection synthesis** (`src/phases/phase_5_intersection.py`) — Claude, acting as a neutral referee at temperature 0.2, extracts only the claims present in both drafts, stated without hedging, and supported by the sources. Anything one-sided, uncertain, or contradicted is excluded ("when in doubt, exclude").
5. **LaTeX generation** (`src/agents/latex_generator.py`) — Claude converts the consensus report into article-class LaTeX with Turkish (babel) support. Citation commands and reference sections are deliberately stripped from the final document.
6. **PDF compilation** (`src/agents/pdf_compiler.py`) — `pdflatex -interaction=nonstopmode`, run twice, with up to 3 retries and a configurable timeout.
7. **Quality assurance and approval** (`src/agents/qa_agents.py`) — Gemini Vision scores rendered page images (layout, typography, tables, appearance) and Claude scores the extracted text (completeness, structure, academic quality); if the average is below the threshold (default 75/100) the LaTeX/PDF stage regenerates, up to 2 times.

Supporting pieces: `src/api_clients.py` wraps both vendors' SDKs with tenacity retry/backoff and enables Google Search grounding on Gemini calls; `src/prompts.py` holds all agent personas and the debate handshake prompt; `src/schemas.py` defines the debate state, rounds, and locked claims.

## Building & running

Prerequisites:

- Python (the Docker image uses `python:3.11-slim`)
- A LaTeX distribution providing `pdflatex` (TeX Live or MiKTeX) — the compiler raises a clear error if missing
- Poppler utilities (used by `pdf2image` for the visual QA step)
- API keys: Anthropic, Google (Gemini), and Tavily (Tavily only needed for internet/auto mode)

Local run:

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY, GOOGLE_API_KEY, TAVILY_API_KEY
streamlit run app.py
```

The UI serves on `http://localhost:8501`. Generated PDFs, LaTeX sources, and logs land in `./output/`.

Docker (installs TeX Live and Poppler for you):

```bash
docker compose up --build
```

Configuration is environment-driven (`.env.example` lists everything): model IDs (`CLAUDE_MODEL`, default `claude-sonnet-4-5-20250929`; `GEMINI_MODEL`, default `gemini-1.5-pro-latest`), `MAX_ROUNDS`, `CONVERGENCE_THRESHOLD`, `QA_THRESHOLD`, LaTeX timeouts/retries, and output paths.

## Status & caveats

A working prototype, honestly rough in places. Known limitations observed in the code and in past runs:

- **Debate JSON parsing is fragile.** The agents are asked to emit strict JSON plus free text; in practice the JSON parse can fail and fall back to regex extraction, which pegs consensus near 50% — so runs often end at max rounds ("forced stop") rather than by natural convergence.
- **The final PDF contains no citations.** Source attribution is enforced in drafts and debate tables, but `strip_citations` removes all citation markers, reference numbers, and bibliographies from the final LaTeX by design.
- **Debate output does not feed the final report.** Intersection synthesis consumes the original Phase-2 drafts; the revised answers and locked-claim list produced by the debate loop currently gate convergence but are not passed to the referee stage.
- **Language:** the UI and most prompts are Turkish; reports compile with Turkish babel support.
- **Search behavior:** Tavily runs only in `internet` mode; `auto` selects internet only when time-sensitive keywords match, and any search failure silently falls back to offline (training-data) mode. Separately, Gemini calls enable Google Search grounding, so evidence gathering is not exclusively Tavily.
- **Dead and stray code:** older phase implementations (`phase_3_cross_examination.py`, `phase_4_convergence.py`) remain in the tree but are no longer wired into the workflow; `src/utils/citation_validator.py` is unused; ad-hoc API test scripts (`test_api.py`, `test_gemini_*.py`, `test_simple.py`, `list_models_new.py`) sit at the repo root.
- **Dependency age:** some pins are dated (e.g. `langgraph==0.0.32`), and the default `gemini-1.5-pro-latest` model ID may need updating.

## License

MIT — see [LICENSE](LICENSE).
