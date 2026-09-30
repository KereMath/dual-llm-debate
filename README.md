# dual-llm-debate

[![CI](https://github.com/KereMath/dual-llm-debate/actions/workflows/ci.yml/badge.svg)](https://github.com/KereMath/dual-llm-debate/actions/workflows/ci.yml)

Two LLMs from different vendors research the same question independently, debate each other's claims round by round, and a neutral referee distills their agreed claims into a LaTeX-compiled PDF report.

## What it is

A Python pipeline that answers a research question with two LLM agents instead of one. Gemini (default `gemini-flash-latest`, a rolling alias that survives Google's model retirements, with a configurable fallback model for 503/quota spikes) plays the "Explorer" — broad, higher temperature (0.7) — and Claude (default model `claude-sonnet-4-5-20250929`) plays the "Judge" — strict, lower temperature (0.5). Both draft answers independently from the same evidence, then compare and revise claim by claim over several rounds. A referee stage (Claude at temperature 0.2) extracts a consensus report, which is rendered to an academic-style PDF through LaTeX and passed through an automated quality-assurance step. The project's working slogan, repeated across the code and the UI, is `Truth = A ∩ B`.

The pipeline is orchestrated as a LangGraph 1.x state machine (`src/workflow.py`) over a shared Pydantic `DebateState` (`src/schemas.py`). Execution is streamed node by node (`workflow.stream`), which drives live progress in the Streamlit web UI (`app.py`): phase tracker, live log tail, per-round convergence chart, the locked-claims table with confidence and sources, and an explicit QA verdict panel. Every finished run is persisted locally by the pipeline itself (`src/run_store.py`, JSON under `output/runs/`), so results survive page refreshes and restarts — the sidebar lists past researches chat-app style (click one to reopen it; a fresh page starts clean with just the question box).

## Why it exists

A single model's answer inherits that model's blind spots. This project is an experiment in reducing that risk through cross-model consensus: if two independently prompted models from different vendors, given the same sources, both assert a claim, that claim is kept and anything only one asserts is meant to be dropped. This trades coverage for confidence rather than making the output hallucination-proof. The debate protocol evolved during development from an adversarial "devil's advocate / cross-examination" design to the current collaborative-convergence one; the old implementation has been removed, and the `*PLAN*.md` / `IMPLEMENTATION_SUMMARY.md` files are kept as historical design snapshots.

## How it works

The workflow builds a LangGraph `StateGraph` with these nodes: `grounding → parallel_drafting → iterative_debate → intersection_synthesis → latex_generation → pdf_compilation → quality_assurance → approval_decision`, plus a conditional `pdf_revision` edge that loops back to `latex_generation`.

1. **Grounding** (`src/phases/phase_1_grounding.py`) — three modes: `offline` (model knowledge only), `internet`, or `auto`. In auto mode a keyword check (`TIME_SENSITIVE_KEYWORDS` in `src/config.py`, e.g. "news", "price", "2025", "güncel") picks internet vs offline. Internet mode queries the Tavily search API (advanced depth, up to 5 results, with `pinterest.com` and `quora.com` excluded) and packs the results into a shared context of numbered, URL-tagged sources. Any search error — including a missing Tavily key — is caught and falls back to offline mode.
2. **Parallel drafting** (`src/phases/phase_2_parallel_drafting.py`) — both agents answer the same question from the same shared context concurrently (`asyncio.gather`), with no visibility into each other's output. Their system prompts (`src/prompts.py`) require every claim to carry a `[Source: ...]` tag. Gemini runs at 0.7, Claude at 0.5. If either draft fails after retries, the run aborts explicitly — the pipeline never debates against an error placeholder.
3. **Iterative debate** (`src/phases/phase_3_4_iterative_debate.py`) — before round 1, a single deterministic call (Claude, temperature 0, schema-enforced) distills both drafts into a **canonical claim inventory**: one merged, numbered list of atomic claims that both agents must evaluate under exactly those `claim_id`s (rows with invented ids are discarded and logged, unevaluated ids are logged). This makes claim identity shared by construction instead of hoping two independently-numbered tables line up; after every non-final round a second extraction pass appends genuinely new claims surfaced in the revised answers (with fresh ids), so a claim that first emerges mid-debate can still be locked rather than reaching the report only through the referee. Then, for up to `MAX_ROUNDS` rounds (default 3), each agent is shown both agents' previous answers and must return a verdict on each inventory claim — **agree** means "I endorse this claim as stated", **partial** means "I endorse only a narrower/qualified version" (written in its `resolution`), **conflict** means "I dispute it" — each with a 0–1 confidence and a source per side, plus its revised answer. The comparison is **schema-enforced structured output** (Claude via forced tool-use, Gemini via `response_schema` — `DebateComparisonOutput` in `src/schemas.py`), so there is no free-text JSON to parse on the happy path; only if a structured call fails does the round fall back to the legacy two-part text protocol and its salvage parser. Claims that both agents mark "agree" — each with its *own* confidence at or above a per-round threshold (0.70 in round 1, 0.80 in round 2, 0.85 thereafter) — are locked under the inventory's canonical statement text, with each agent's final wording stored alongside it; if either wording narrows the canonical claim, the synthesizer is shown that nuance rather than just the broad statement. If inventory extraction itself fails, the debate falls back to per-agent numbering, where a coarse resolution-text similarity check catches only *blatantly* unrelated ID collisions — a safety net, not a guarantee, which is exactly why the inventory is the primary mechanism. From the next round on the agents are instructed to respect locked claims and focus on the disputed points. Four metrics are computed each round — a symmetric, intersection-based consensus plus each agent's individual coverage and their average — and the debate converges only when all four reach the convergence threshold (default 0.95). Otherwise the loop runs to max rounds and sets a `forced_stop` flag.
4. **Intersection synthesis** (`src/phases/phase_5_intersection.py`) — Claude, acting as a neutral referee at temperature 0.2, is fed the debate's output: the locked-claim list (with sources and confidence), each agent's final revised answer from the last debate round, and the still-disputed points. Locked claims are treated as the pre-verified backbone of the report and must all be included; additional claims are admitted only if both revised answers assert them with source support; disputed points are excluded outright ("when in doubt, exclude"). The pre-debate Phase-2 drafts are used only if no debate round was recorded.
5. **LaTeX generation** (`src/agents/latex_generator.py`) — Claude converts the consensus report into an article-class LaTeX document with Turkish `babel` support. A `strip_citations()` pass then removes all `\cite`/`\citep`/`\citet` commands, inline `[n]` reference numbers, `natbib`, and any bibliography/References section.
6. **PDF compilation** (`src/agents/pdf_compiler.py`) — writes the LaTeX into a temp directory and runs `pdflatex -interaction=nonstopmode` twice; the whole compile is retried up to `MAX_LATEX_RETRIES` times (default 3) with a per-run timeout (`LATEX_TIMEOUT`, default 30s). Only the resulting PDF is copied into `./output/pdfs`.
7. **Quality assurance and approval** (`src/agents/qa_agents.py`) — Gemini Vision scores the *first* rendered page image (layout, typography, tables/figures, professional appearance) and Claude scores the extracted PDF text (question completeness, fidelity to the consensus report — missing citations are *not* penalized, since they are stripped by design — structure, academic standards). If the average of the two scores is below `QA_THRESHOLD` (default 75) the pipeline regenerates the LaTeX/PDF, up to `MAX_PDF_REGENERATIONS` times (default 2). QA failures are explicit: if a QA model errors or returns unparseable JSON, the run is marked `qa_failed` with zero scores, the PDF is *not* approved, and no regeneration is attempted (regeneration can't fix a QA infrastructure error) — there is no silent auto-approval. The PDF file still exists on disk either way; approval is a recorded verdict, not a gate on the file.

Supporting modules: `src/api_clients.py` wraps the Anthropic and `google-genai` SDKs with `tenacity` retry/backoff and a configurable Gemini fallback model — deliberately with **no** Google Search grounding on the Gemini calls, since both agents must argue from the same shared context (web evidence enters only through the shared Tavily phase); `src/prompts.py` holds every agent persona and the debate handshake prompt; `src/schemas.py` defines `DebateState` and the `DebateRound` / `ComparisonClaim` / `LockedClaim` records.

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

The suite covers the debate's consensus math and claim locking, debate-response parsing (including the malformed-JSON fallbacks), the synthesis stage's inputs (locked claims + revised answers, not the pre-debate drafts), the explicit QA-failure path, and workflow graph compilation. The same suite runs in CI on every push (`.github/workflows/ci.yml`, Python 3.11 and 3.12).

Docker (installs TeX Live packages and Poppler for you):

```bash
docker compose up --build
```

Configuration is environment-driven; `.env.example` lists every setting: model IDs (`CLAUDE_MODEL`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODEL`), `MAX_ROUNDS`, `CONVERGENCE_THRESHOLD`, `QA_THRESHOLD`, `DEFAULT_RESEARCH_MODE`, `REPORT_LANGUAGE`, `LATEX_TIMEOUT`, `MAX_LATEX_RETRIES`, `MAX_PDF_REGENERATIONS`, and the output directories. Temperatures and token limits are hard-coded in `src/config.py`, not exposed as env vars.

## Status & caveats

A personal, experimental prototype. Remaining limitations visible in the code:

- **Text-mode parsing survives only as a fallback.** The debate comparison is schema-enforced (tool-use / `response_schema`); when a structured call errors outright, the round falls back to the legacy free-text protocol, whose parser recovers what it can (salvaging intact claim objects from truncated JSON) and pegs consensus at 0.5 when nothing is recoverable. A fully unparseable fallback round therefore cannot converge, and such runs end at max rounds ("forced stop"). Both paths are covered by tests.
- **The final PDF has no citations, by design.** Sources are required in the drafts and debate tables, but `strip_citations()` removes all citation markers, reference numbers, and bibliographies from the final LaTeX.
- **Language.** The web UI is English; agent prompts are a mix of English scaffolding and Turkish instructions, and reports compile with Turkish `babel` support. The final report's language is configurable (`REPORT_LANGUAGE` env var or the "Report language" selector in the UI): `auto` (default) follows the question's language, `tr`/`en` force Turkish/English regardless of the question.
- **Claude wears many hats.** One of the two debaters (Claude) is also the claim-inventory extractor, the neutral referee, the LaTeX generator and the content-QA scorer. "Neutral" therefore means *prompted for neutrality*, not structurally neutral — a single-vendor bias the referee-panel roadmap item is meant to address.
- **Design docs are historical.** `PLAN.md`, `MASTERPLAN.md`, `IMPLEMENTATION_SUMMARY.md` and `CONSENSUS_SYSTEM.md` are mid-development snapshots (marked as such) and describe some designs that were later changed or dropped; the README and the code are authoritative.
- **Gemini free tier.** Flash models run on the free tier but with small per-model daily quotas (~20 requests/day; one full pipeline run makes 5-9 Gemini calls). Pro models require a paid plan (their free-tier quota is zero). When the primary model hits a 503 spike or its daily quota, the client retries with backoff and then switches to `GEMINI_FALLBACK_MODEL` once before failing explicitly.

Previously documented gaps that have since been fixed (see git history): the synthesis stage now consumes the debate's locked claims and final revised answers instead of the pre-debate drafts; QA errors now fail the run explicitly instead of auto-approving with a default score of 85; a failed draft aborts the run instead of silently debating an error placeholder; agents must emit a `resolution` sentence per claim, so locked claims carry real statement text instead of empty strings; Gemini's private Google-Search grounding was removed to keep both agents on the same shared evidence; the dead adversarial-protocol code (cross-examination/convergence phases, devil's-advocate prompts, unused citation validator, root-level ad-hoc scripts) has been removed; a locking bug that read Claude's *estimate of Gemini's* confidence instead of Claude's own is fixed; claim identity is now shared by construction via the pre-debate canonical claim inventory (a resolution-similarity guard remains only for the no-inventory fallback); a failed referee synthesis now sets `synthesis_failed` and such a run can never end approved; and a pytest suite (run in CI) now covers the consensus math, claim locking, parsing fallbacks, drafting/synthesis behavior, QA failure paths, and the Streamlit app boot.

## Roadmap

Deliberately not started — each is a contained next step, listed in order of value:

- **LangGraph checkpointing** (`SqliteSaver` + a `thread_id` per run): resume interrupted runs instead of losing paid API calls, plus human-in-the-loop approval of locked claims before synthesis.
- **Graph-native debate rounds**: lift the internal `while` loop of `run_debate_loop` into a `debate_round` node with a conditional edge, so each round is a graph step — per-round checkpoints, per-round streaming in the UI, and nodes that return partial state updates (deltas) instead of full dumps.
- **Per-disputed-claim evidence retrieval + peer-review exchange**: when a claim stays disputed across rounds, a targeted retrieval step searches for that specific claim, and both agents write a structured review of each other's position (evidence quality, reasoning gaps) followed by a rebuttal before the locking decision — full peer review scoped to disputed claims only, so cost stays bounded and convergence isn't flooded with new claims every round. (Note: both agents already cross-judge every round via the comparison table; Explorer/Judge are personas, not a one-way reviewer role.)
- **Source-verification before locking**: check that a claim's cited source actually entails the claim (the honest successor of the removed `citation_validator`).
- **Referee panel**: replace the single Claude referee with a small panel of judges voting per claim — and move claim-inventory extraction to the panel too, since today one debater's vendor also runs the debate's neutral machinery.
- **Anti-sycophancy round**: one adversarial "try to break this consensus" pass before final locking, guarding against the two models converging by politeness rather than evidence.

## License

MIT — Copyright (c) 2026 Kerem Gür. See [LICENSE](LICENSE).
