# Real Chatbot And Website Task Bank

Status: draft P1 Application task bank.
Last reviewed: 2026-07-04.

This task bank turns the current Application ask into source-grounded scenarios
that can be handed to Environment without guessing at the target product,
persona-sensitive axes, outputs, or metrics. The near-term goal is a small set
of real chatbot and website tasks, with deterministic wrappers where live
services require login, change frequently, or should not be stress-tested
directly.

## Guardrails

- Use public, official, or self-hostable targets. Do not commit credentials,
  private chat logs, scraped proprietary data, or generated run outputs.
- Keep live website tasks read-only: no purchases, signups, account changes, or
  real support tickets.
- Prefer local task sidecars for chatbot evaluation unless the target exposes a
  stable public API or the team owns credentials for a test tenant.
- Store raw trajectories and final artifacts separately. Reports should consume
  artifacts, not replay external services.
- Normalize metrics as numeric, categorical, and textual fields so the later
  reporting layer can summarize both single-persona and batch-persona runs.

## Shared Output Contract

Each runnable task should produce:

- `trajectory`: ordered actions, messages, pages, or API calls.
- `application_result`: task-specific final decision or answer.
- `persona_self_report`: persona-grounded satisfaction, trust, confusion, and
  friction notes.
- `metric_summary`: numeric, categorical, and textual metrics.
- `source_reference`: target URL, API, repository, or hosted app version.

## Candidate Tasks

### 1. Chatwoot support account recovery

Scenario name: Chatwoot support account recovery.
Task type: chatbot.
Domain / vertical: customer support / commerce-retail.
Product or system under test: Chatwoot self-hosted support inbox and chat
widget.
Source site or API: https://github.com/chatwoot/chatwoot and
https://www.chatwoot.com/.
Task description: a user who lost access to an account asks for help, shares
only necessary information, and decides whether the support experience is
trustworthy.
Instruction for each persona: recover access while protecting personal data;
ask clarification questions if policy or identity checks are unclear.
Environment needs: self-hosted Chatwoot test tenant, seeded customer record,
support policy, and chat widget or API adapter.
Persona attributes that should affect behavior: privacy sensitivity, digital
literacy, frustration tolerance, prior fraud experience, age, disability or
assistive-technology needs.
Output telemetry: turn transcript, requested personal data, escalations,
resolution status, refusal or retry events, persona self-report.
Aggregate metrics: resolution rate, turns to resolution, unnecessary PII
requests, escalation rate, trust score, frustration score.
Why personas should differ: privacy-sensitive users should resist broad data
requests, low-literacy users should need simpler instructions, and frustrated
users should escalate earlier.

### 2. Multi-Agent Medical Assistant symptom triage

Scenario name: Medical assistant symptom triage.
Task type: chatbot.
Domain / vertical: healthcare / patient support.
Product or system under test: Multi-Agent Medical Assistant.
Source site or API:
https://github.com/souvikmajumder26/Multi-Agent-Medical-Assistant.
Task description: a patient describes non-emergency symptoms and asks what to do
next; the system should provide cautious, non-diagnostic guidance and
appropriate escalation language.
Instruction for each persona: explain symptoms, ask for plain-language next
steps, and state any access constraints such as cost, transport, or anxiety.
Environment needs: self-hosted test instance, safety policy, no real patient
data, and a fixed symptom vignette per run.
Persona attributes that should affect behavior: health literacy, anxiety,
insurance or cost pressure, disability, language preference, caregiver status.
Output telemetry: transcript, safety disclaimers, escalation advice, unsupported
diagnosis attempts, persona confidence and anxiety ratings.
Aggregate metrics: safe escalation rate, diagnosis-overclaim rate,
comprehension score, care-seeking intent, unresolved concern count.
Why personas should differ: high-anxiety personas should ask more follow-ups,
low-health-literacy personas should need simpler wording, and cost-constrained
personas should press for lower-cost options.

### 3. OpenBB market digest assistant

Scenario name: OpenBB market digest comprehension.
Task type: chatbot.
Domain / vertical: finance / investing research.
Product or system under test: OpenBB-powered financial assistant or MCP/API
surface.
Source site or API: https://github.com/OpenBB-finance/OpenBB and
https://openbb.co/.
Task description: a user asks for a market or company digest and then decides
whether the explanation is actionable, appropriately caveated, and matched to
their expertise.
Instruction for each persona: ask for a digest, probe one unclear claim, and
report what decision the digest would or would not support.
Environment needs: OpenBB test adapter, fixed public-market query, no investment
advice claims, and citation capture.
Persona attributes that should affect behavior: financial literacy, risk
tolerance, investment horizon, numeracy, trust in AI, regulatory sensitivity.
Output telemetry: transcript, cited data sources, clarification turns,
confidence, risk-understanding self-report.
Aggregate metrics: citation coverage, caveat quality, comprehension score,
over-trust rate, risk-alignment score.
Why personas should differ: novice investors should need simpler explanations,
high-risk users may accept thinner caveats, and expert users should challenge
data provenance.

### 4. Open Library book recommender chat

Scenario name: Open Library recommendation assistant.
Task type: chatbot.
Domain / vertical: commerce-retail / media recommendation.
Product or system under test: local recommender-chat wrapper over Open Library
search.
Source site or API: https://openlibrary.org/developers/api and
https://openlibrary.org/dev/docs/api/search.
Task description: a user asks for a book recommendation under constraints such
as budget, age appropriateness, genre, format, or accessibility.
Instruction for each persona: state preferences naturally, answer at least two
clarifying questions, and judge the final recommendation.
Environment needs: small chat API sidecar that calls Open Library Search API and
caches responses for deterministic tests.
Persona attributes that should affect behavior: reading habits, budget,
language, accessibility needs, genre preference, novelty seeking.
Output telemetry: transcript, query terms, recommended work IDs, clarification
quality, final acceptance or rejection.
Aggregate metrics: preference coverage, grounded recommendation rate,
clarifying-question usefulness, recommendation acceptance.
Why personas should differ: genre-loyal personas should reject exploratory
recommendations more often, budget-constrained users should ask about
availability, and accessibility-focused users should value format metadata.

### 5. GitHub pricing plan fit

Scenario name: GitHub pricing plan fit.
Task type: web.
Domain / vertical: software / pricing and signup.
Product or system under test: GitHub pricing page.
Source site or API: https://github.com/pricing.
Task description: a user compares plans for an individual or small team and
decides whether a plan fits their needs and budget.
Instruction for each persona: browse the pricing page, select the plan you
would seriously consider, and explain any confusion or trust concerns.
Environment needs: browser or Playwright environment with public network;
read-only access, no signup.
Persona attributes that should affect behavior: team size, budget sensitivity,
security requirements, open-source familiarity, technical confidence.
Output telemetry: visited pages, selected plan, fit and trust ratings, pricing
confusion notes, conversion intent.
Aggregate metrics: plan-selection distribution, conversion intent, confusion
rate, trust rating, price-sensitivity deltas.
Why personas should differ: individual developers should favor lower tiers,
security-sensitive organizations should look for enterprise features, and
novices should show more pricing comprehension friction.
Runnable first-pass example: `application/tasks/web-github-pricing_plan-fit`.

### 6. Stripe pricing and checkout comprehension

Scenario name: Stripe pricing and checkout comprehension.
Task type: web.
Domain / vertical: finance / payments.
Product or system under test: Stripe pricing page and pricing-table docs.
Source site or API: https://stripe.com/pricing and
https://docs.stripe.com/payments/checkout/pricing-table.
Task description: a user evaluates whether Stripe pricing and hosted checkout
components are understandable enough for a small online business.
Instruction for each persona: find the relevant pricing model, identify any
unclear fees or setup steps, and state whether you would proceed.
Environment needs: browser or Playwright environment with public network;
read-only access, no account creation.
Persona attributes that should affect behavior: business size, technical skill,
fee sensitivity, international sales, trust in financial platforms.
Output telemetry: pages visited, extracted fee assumptions, confusion notes,
implementation confidence, conversion intent.
Aggregate metrics: fee-comprehension score, confusion rate, implementation
confidence, selected next action.
Why personas should differ: nontechnical small-business users should struggle
more with implementation details, while fee-sensitive personas should focus on
edge-case charges.

### 7. Python docs error lookup

Scenario name: Python docs error lookup.
Task type: web.
Domain / vertical: software / documentation and education.
Product or system under test: official Python documentation.
Source site or API: https://docs.python.org/.
Task description: a user searches the docs to answer a concrete Python usage
question and reports whether the docs were understandable.
Instruction for each persona: use the docs to answer the task, cite the page
used, and explain whether the page helped or created friction.
Environment needs: browser or Playwright environment with public network.
Persona attributes that should affect behavior: programming experience,
English proficiency, confidence, time pressure, learning style.
Output telemetry: visited docs pages, answer summary, confidence, friction
points, reuse intent.
Aggregate metrics: answer correctness, docs navigation friction, confidence,
reuse intent, support-needed rate.
Why personas should differ: experts should navigate by API names, beginners
should need examples, and low-confidence users should report lower reuse intent.
Runnable first-pass example: `application/tasks/web-python-docs_error-lookup`.

### 8. Books to Scrape product discovery

Scenario name: Books to Scrape product discovery.
Task type: web.
Domain / vertical: commerce-retail / product discovery.
Product or system under test: Books to Scrape public sandbox bookstore.
Source site or API: https://books.toscrape.com/.
Task description: a user browses a book catalog, picks a book they would
consider, and explains the choice.
Instruction for each persona: browse the catalog, choose one visible book, and
report whether you would consider buying it.
Environment needs: existing public-network Playwright task.
Persona attributes that should affect behavior: genre preference, price
sensitivity, reading frequency, novelty seeking, budget.
Output telemetry: selected title and price, interest flag, reason, visited
pages.
Aggregate metrics: selected-category distribution, price sensitivity, purchase
intent, reason themes.
Why personas should differ: frequent readers should explore more options,
price-sensitive users should prefer lower-priced items, and genre-specific
personas should reject off-preference titles.
Runnable reference: `application/tasks/example-web-playwright_books-interest`.

## Runnable First-Pass Examples

The first runnable examples should stay small and read-only so they can pass
free CI and local smoke runs without credentials.

### Example A: GitHub pricing plan fit

Task directory: `application/tasks/web-github-pricing_plan-fit`.
Environment definition:
`environment/task-environments/application/web-github-pricing_plan-fit`.
Start from: `application/tasks/example-web-playwright_books-interest`.
Expected artifact: `/app/output/pricing_plan_evaluation.json`.
Primary metrics:

- `fit_rating` numeric 1-10.
- `trust_rating` numeric 1-10.
- `selected_plan` categorical.
- `conversion_intent` categorical.
- `reason` and `friction_points` textual.

### Example B: Python docs error lookup

Task directory: `application/tasks/web-python-docs_error-lookup`.
Environment definition:
`environment/task-environments/application/web-python-docs_error-lookup`.
Start from: `application/tasks/example-web-playwright_books-interest`.
Expected artifact: `/app/output/python_docs_lookup.json`.
Primary metrics:

- `documentation_confidence` numeric 1-10.
- `ease_of_lookup` numeric 1-10.
- `would_reuse_docs` categorical boolean.
- `answer_summary` and `friction_points` textual.

## Reporting Notes

- Diversity metrics should summarize persona coverage across demographics,
  capability, values, trust, and domain-specific constraints.
- Distribution matching should be added only when a legal human baseline exists;
  otherwise report directional simulated-cohort behavior.
- USI, tau-bench, and Tao-bench-style evaluation should inform the split between
  objective task success, behavioral alignment, and persona self-report.
- PRIMEX/eHRAF-style cultural context should be treated as optional persona
  axes for tasks where worldview or cultural background plausibly changes
  behavior.
- Concordia-style embodied, social, and digital spaces are background framing
  for later multi-agent scopes, not a blocker for these P1 tasks.
- Nemotron/Spectrum-style persona generation should be compared against the
  team's DAG and taxonomy approach when selecting cohorts for batch runs.
