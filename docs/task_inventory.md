# MatrAIx Task-Type Inventory

High-level inventory of **distinct task types/domains** implemented anywhere in the
repo — main, all branches, and all PRs — for the breadth-of-domains comparison
against single-domain agent benchmarks (WebShop, Mind2Web, etc.). Instance-level
duplication (one template × N products/topics) is collapsed into a single entry
with an instance count.

Snapshot date: 2026-07-18.

## Methodology

**Task format discovered on main (Applications team).** One folder per runnable
scenario under `application/tasks/<interaction-type>_<slug>/`, containing
`task.toml` (with `[metadata] type/domain/tags`), a persona-facing
`instruction.md`, an `input/` bundle (questionnaire, context docs), a verifier
under `tests/`, `reporting.json`, and `persona_strategy.json`. Interaction types
follow the four "environment types" in `docs/applications/PLAN.md`:
Type 1 = **survey**, Type 2 = **chatbot** (agent converses with a system under
test), Type 3 = **web** (live browser surfaces via Playwright / browser-use /
Cocoa / CUA), Type 4 = **os-app / computer-use** (native iOS/macOS/Linux apps).
`example-*` folders are copy-from references, not benchmark tasks.

**Other subteams.** The Environment team ships runtimes, not task folders:
Harbor runtime, shared task-environments (survey form, chat sidecars, shared
web/os images), external-benchmark adapters, and the OASIS multi-agent social
simulation (branch-only). The Persona team's deliverables are persona
*construction* pipelines (extraction, synthesis, schema/taxonomy) rather than
agent scenarios; its only `persona/tasks/` entry is a mirror of the survey
reference task. Persona pipelines are therefore **not** counted as task types
here.

**Coverage.** 238 `origin/*` branches plus ~70 fork-remote branches scanned via
`git diff origin/main...<branch> --stat`; all 189 PRs (open/merged/closed/draft)
enumerated via `gh pr list`; head refs of the 28 task-relevant PRs fetched and
diffed individually. Templated sets (200 product surveys, 405 synthetic surveys,
351 synthetic chatbots, 10 prescreening protocols, 10 Pew templates) were
sampled (2–3 task folders each), confirmed structurally identical, and collapsed
to one entry apiece.

## Summary table

| # | Task type | Domain | Subteam | Status | Source | Instances |
|---|-----------|--------|---------|--------|--------|-----------|
| 1 | Grounded national-survey replication | Public policy: consumer finance, public health, food security, arts participation, developer demographics | Applications | Merged (main) | PR #205 | ~10 |
| 2 | Product/feature-concept surveys | Consumer products & product-feature feedback (retail, pharmacy AI, fintech, dev tools) | Applications | Merged (main) | main | 5 |
| 3 | Commerce product-perception survey battery | Commerce/retail purchase psychology (pricing, brand, ads, reviews, sustainability…) | Applications | Open PR | PR #250 (current branch; supersedes closed #148) | 200 generated (20 archetypes × 10 products) |
| 4 | Synthetic consumer-behavior survey bank | Everyday finance / healthcare / software habits & attitudes | Applications | Open PR | PR #203 (supersedes closed #202) | 405 generated |
| 5 | Pew public-opinion survey templates | Politics, religion, international relations, AI attitudes | Applications | Closed PR, stub | PR #157 | 10 (stubs) |
| 6 | Grounded SUT chatbot evaluation | Finance research, e-commerce recommendation, medical consultation, retail support, mental health, dev tools, clinic scheduling, budgeting | Applications | 3 merged (main) + 5 in open PR | main (#223), PR #215 (+#280 cleanup) | 8 |
| 7 | Synthetic everyday-advice chatbot bank | ~30 life domains: travel, legal, telecom, insurance, real estate, education, careers, parenting, pets, arts… | Applications | Draft PR | PR #255 (staging/synthetic-tasks) | 351 generated |
| 8 | Clinical-trial pre-screening chatbots | Healthcare: trial eligibility screening | Applications | Draft PR | PR #257 (supersedes #216) | 10 (one protocol each) |
| 9 | Mental-health support chatbots (synthetic) | Healthcare: anxiety/depression support, crisis detection | Applications | Open PRs | PRs #260, #261 | 2 |
| 10 | Meal-planning & nutrition assistant chatbot | Healthcare: dietary coaching | Applications | Open PR | PR #199 | 1 |
| 11 | Account-recovery support chatbot (Rasa) | Customer service / account security | Applications | Draft PR | PR #159 | 1 |
| 12 | Product-choice web browsing (references) | E-commerce comparison shopping | Applications | Merged (main) | main (#163 etc.) | 4 reference tasks × 4 browser stacks |
| 13 | Recipe choice on Allrecipes | Food & lifestyle web browsing | Applications | Open PR | PR #281 | 1 |
| 14 | Course choice on MIT OpenCourseWare | Education / self-directed learning | Applications | Open PR | PR #271 | 1 |
| 15 | Portfolio backtesting on Portfolio Visualizer | Finance: investment allocation & risk | Applications | Open PR | PR #228 | 1 (2 harness variants) |
| 16 | Live-site comprehension (GitHub pricing, Python docs) | Software: pricing plan fit, docs error lookup | Applications | Draft PR | PR #159 | 2 |
| 17 | Heads-up Texas Hold'em poker (web game) | Gaming: strategic play vs dynamic opponent | Applications | Draft PR | PR #200 | 1 |
| 18 | Starclash multi-agent arena game | Gaming / social simulation: persona reasoning styles vs bot table | Applications | Open PR | PR #266 (supersedes closed #197) | 1 |
| 19 | Native OS-app decision tasks | News subscription (iOS), stock sentiment (macOS), automation gallery (macOS) | Applications | Merged (main) | main (#226, #237) | 3 (+3 computer-use references) |
| 20 | OASIS social-media simulation | Social media dynamics: information spread, polarization, herd behavior | Environment | Open PRs (WIP, not merged) | PRs #141, #142 (open); #126, #167 (closed); fork branches incl. Greenland GPU deploy | 1 platform (Twitter/Reddit-like, up to 1M agents) |
| 21 | External-benchmark adapters (SimpleQA, AppWorld) | Factuality QA; app-automation eval | Environment | Merged (main) | main (#145, #146) | 2 adapters |

## Task-type descriptions

### 1. Grounded national-survey replication (main, merged via #205)
Personas answer questionnaires reconstructed from real large-scale survey
instruments: CFPB Financial Well-Being and Making Ends Meet, the Fed's SHED,
FDIC household banking, Census Household Pulse, NCI HINTS, CPS Food Security and
Tobacco Use supplements, NEA SPPA (arts participation), and the Stack Overflow
Developer Survey. The persona reads the instrument and returns structured
answers; rule-based verifiers score schema validity and answer aggregation
enables comparison against published human marginals. ~10 instruments spanning
finance, health, food security, culture, and software.

### 2. Product/feature-concept surveys (main)
Single-product opinion surveys about real, current products/features: Nike Air
Max DN, CVS prescription-AI app feature, Robinhood Cortex digests, Claude Code
VS Code checkpoints, plus a general product-attitudes instrument. Same survey
runtime as #1 but synthetic instruments authored per product.

### 3. Commerce product-perception survey battery (PR #250, open — this branch)
One survey template family applied combinatorially: 20 question archetypes
(purchase intent, price sensitivity, brand perception, ad response, review
trust, discount response, gift suitability, impulse-vs-planned, delivery
patience, warranty importance, sustainability, value-for-money, repurchase,
return likelihood, satisfaction, feature priority, channel preference,
competitor comparison, perceived quality, recommendation) × 10 real Amazon
products each = **200 generated task folders, counted as one task type**. Each
task has a unique persona-facing instruction, but structure and verifier are
templated. Probes consumer-psychology dimensions of retail decisions.

### 4. Synthetic consumer-behavior survey bank (PR #203, open)
405 generated survey tasks (a closed predecessor, #202, had 300) covering
everyday behaviors and attitudes tagged finance / healthcare / software —
e.g. wedding budgeting, wire-transfer usage, yoga practice, weight management,
workflow-automation tools, web-browser choice. Structurally one template;
counted as one type.

### 5. Pew public-opinion survey templates (PR #157, closed — stub)
10 survey folders modeled on Pew Research instruments (2024 election, US image
abroad, views of China/Israel, religion in Latin America, national identity,
news & social media, Americans & AI). **Half-built**: each folder has only a
README and instruction.md — no task.toml, verifier, or input bundle — and the
PR was closed. Included because it is the only politics/religion survey work in
the repo.

### 6. Grounded SUT chatbot evaluation (main + PR #215)
Personas hold multi-turn conversations with real open-source products wired in
as Dockerized sidecars ("system under test"), then report structured feedback.
On main: `chat_openbb` (OpenBB financial-research copilot), `chat_recai`
(conversational e-commerce recommender), `chat_multi-agent-medical-assistant`
(medical information assistant). PR #215 (open) adds five more grounded SUTs:
retail order support, mental-health support, developer helper, clinic
appointment scheduling, and a budget coach (the budget coach is being removed
again in open PR #280). Verifiers check conversation artifacts and structured
exposure contracts.

### 7. Synthetic everyday-advice chatbot bank (PR #255, draft)
351 generated chatbot tasks against a shared simulated-chatbot sidecar
(`shared-chat-sim`), spanning ~30 topical categories: travel, legal, healthcare,
telecom, real estate, insurance, finance, education, customer service, careers,
personal development, events, automotive, technology, sustainability, sports,
relationships, pets, parenting, home, government services, gardening, food,
entertainment, arts, music, writing, beauty, photography, volunteering. One
template; counted as one type.

### 8. Clinical-trial pre-screening chatbots ("Scenario 10"; PR #257 draft, supersedes #216)
10 tasks, one clinical protocol each (type-2 diabetes, hypertension, migraine,
sleep apnea, knee osteoarthritis, smoking cessation, insomnia, cardiac rehab,
atrial fibrillation, asthma). The persona is screened for trial eligibility in
dialog; verifiers test boundary conditions (e.g. A1c cutoffs, insulin-pump
exclusions) against the persona's health profile.

### 9. Mental-health support chatbots, synthetic (PRs #260, #261, open)
Anxiety-support and depression-support chatbot tasks with explicit
crisis-detection tags — structurally close to the #255 bank but authored
individually with safety-focused verifiers.

### 10. Meal-planning & nutrition assistant chatbot (PR #199, open)
Personalized meal planning / dietary-adherence coaching conversation; tests
whether recommendations adapt to the persona's constraints.

### 11. Account-recovery support chatbot (PR #159, draft)
A Rasa-based account-recovery flow as SUT, part of a broader "real chatbot and
website task bank" draft that also contributes type #16.

### 12. Product-choice web browsing references (main)
Reference web tasks where a persona browses a small storefront and makes a
choice (laptop choice, bookshop choice, subscription plan choice, insurance
quote choice), implemented across four browser harnesses (Playwright DOM,
browser-use, Cocoa, CUA screen agents). These are `example-*` scaffolding, but
they are the only merged web-domain tasks on main.

### 13–16. Live-website decision tasks (PRs #281, #271, #228, #159 — open/draft)
Individually authored web tasks on real public sites: choosing a recipe on
Allrecipes under time/novelty pressure (food & lifestyle); choosing a course on
MIT OpenCourseWare (education); configuring and interpreting a portfolio
backtest on Portfolio Visualizer (finance; Playwright + CUA variants); GitHub
pricing plan-fit and Python-docs error-lookup comprehension (software). Each
probes persona-sensitive comparison on a live surface.

### 17. Heads-up Texas Hold'em poker (PR #200, draft)
Web game with a task-specific host: the persona plays heads-up poker against a
dynamic opponent; evaluates persona-consistent risk/strategy behavior.

### 18. Starclash multi-agent arena game (PR #266, open)
A custom social arena game (rock-paper-scissors-like) where the sampled persona
plays as a real player at a table filled with Bayesian bots; tags emphasize
persona reasoning styles and reasoning-trajectory capture.

### 19. Native OS-app decision tasks (main)
Computer-use tasks in real OS applications: deciding on an Apple News+
subscription (iOS), reading sentiment from the macOS Stocks app for Micron, and
picking automations from the macOS Shortcuts gallery. Plus three `example-*`
computer-use references (Linux note-to-CSV, macOS calendar handoff, iOS photo
access review). Runs on macOS/iOS/Linux screen-agent harnesses.

### 20. OASIS social-media simulation (Environment team; branch/PR only)
Integration of CAMEL-AI's OASIS: LLM agents act as users of Twitter-like and
Reddit-like platforms to study information spreading, polarization, herd
behavior, and recommender effects, scaling to ~1M agents via sparse activation
and distributed vLLM. Includes an orchestrator + per-agent containers, live
dashboard feed, 3D viewer, and a "Greenland" 8×A100 pod deployment (fork
branches). Open ports #141/#142; earlier PRs #126/#167 closed. **Not merged to
main** — a working prototype, not a shipped benchmark task.

### 21. External-benchmark adapter surfaces (main)
SimpleQA (4,326 factuality questions converted to Harbor task dirs, LLM-judge
graded) and an AppWorld BenchFlow eval surface in the Playground backend. These
evaluate agent capability rather than persona fidelity; included for
completeness, arguably out of scope for the domain-breadth claim.

## Gaps / uncertainties

- **Scenario numbering is not canonical.** PR #257 calls prescreening
  "Scenario 10" and early PR #14 claims "4 application Scenarios", but no
  authoritative Scenario 1–N list exists in the repo; the stable taxonomy is
  the Type 1–4 interaction types in `docs/applications/PLAN.md`.
- **Overlap between synthetic banks.** #9 (anxiety/depression chatbots) and the
  healthcare slice of #7 (351-task bank) are near-neighbors; if collapsed, the
  distinct-type count drops by one. Similarly #2 vs #3 are both product
  surveys (individually authored vs templated).
- **Microverse** (`fork/environment/microverse`) is docs/process-only — no
  environment implementation; excluded.
- **Persona-team branches** (Amazon Reviews 2023, Wikipedia, Stack Overflow,
  PRISM, ConvAI2 extraction; GSS crosswalk; schema taxonomy; DAG Studio /
  Synthesis Studio) are persona-construction pipelines, not agent task types;
  deliberately excluded from the table.
- **Stale old-layout branches** (`ui/matraix-redesign`,
  `app/persona-eval-paper-experiments`, `codex/chatbot-general-survey-prompts`,
  `codex/pb18x-*` ports) predate the `application/tasks/` migration; their task
  content (recommender chat, e-commerce product discovery, support-chatbot
  examples) is already represented by merged successors and was not counted
  separately.
- Closed PR #202 (300 surveys), #216 (prescreening v1), #148 (200 product
  surveys v1), and #197 (Starclash v1) are superseded by open successors and
  were merged into the corresponding entries, not double-counted.
- Fork remotes were scanned for names, and key ones diffed (oasis, microverse,
  persona_subtask_2.x); a handful of fork-only patch branches
  (`*-patch-1` etc.) are one-file doc edits and were not individually diffed.
