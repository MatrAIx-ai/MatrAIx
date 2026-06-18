# Proposal: Persona-Conditioned Evaluation for Recommendation Chatbots

Suggested repository path: `applications/proposal_recommendation_chatbot_eval.md`

Owner(s): Yifan Simon Liu, Qianfeng Wen
Team: Application
Status: Proposal for discussion
Related issue or discussion: https://github.com/MatrAIx-ai/MatrAIx/issues/20
Environment type: Type 2 Chatbot Environment
Target domain: Recommendation Systems, E-Commerce, Local Services, Movies, Fashion
Commit scope: Documentation-only proposal. No code, no data, no model artifact, no benchmark result.

Dataset/interface notes: see `applications/recommendation_chatbot_eval/`.
Current local testing domain: Movies, using the CMU Movie Summary Corpus shape and a tiny movie fixture.

## 1. General Task Description

### 1.1 Task Definition

This proposal defines a chatbot-based evaluation task for recommendation systems. The task evaluates whether a recommendation chatbot can serve heterogeneous users who issue the same or similar natural-language recommendation request while differing in latent preferences, constraints, and decision criteria.

The main object of evaluation is the target chatbot's interactive recommendation policy. We evaluate how the chatbot asks clarification questions, elicits preferences, updates recommendations, explains tradeoffs, and produces a final recommendation that satisfies a user agent paired with a persona.

### 1.2 Evaluation Setup

Each evaluation episode contains four core elements:

1. an initial recommendation request,
2. a structured persona represented as a list of attributes,
3. a persona-affiliated user agent paired with that persona,
4. a recommendation chatbot with access to a candidate item catalog and item metadata, including popularity signals.

The same initial request is reused across multiple personas. This setup tests whether the chatbot gives homogeneous mainstream recommendations across users, or adapts to different latent user utilities through conversation.

### 1.3 Components and Terminology

**Persona**
A structured profile or attribute list. It may include demographics, situational context, hard constraints, soft preferences, budget, decision style, communication style, and domain-specific preferences.

**Persona-affiliated user agent**
A simulated user created by pairing an agent with a persona. The agent follows the persona during conversation and reveals preferences gradually according to the interaction.

**Recommendation chatbot**
The target system under evaluation. It can ask clarification questions, recommend items, revise recommendations, and explain tradeoffs.

**Evaluation environment**
The controller that initializes the episode, enforces the turn budget, logs the transcript, and records structured telemetry.

### 1.4 Episode Output

Each episode produces:

1. the full multi-turn conversation transcript,
2. the final recommendation or recommendation set,
3. structured user-side feedback from the persona-affiliated user agent,
4. evaluation telemetry, including satisfaction, constraint satisfaction, preference match, popularity exposure, and failure reasons.

## 2. Motivation

Generic recommendation evaluation often collapses user utility into a single average-user judgment. For the same recommendation request, a generic LLM judge may assign similar scores to outputs that sound fluent, plausible, and broadly useful.

Real recommendation users are heterogeneous. The same request can imply different desirable products depending on budget, context, constraints, prior experience, lifestyle, accessibility needs, risk tolerance, and personal taste. A recommendation chatbot that repeatedly gives popular mainstream suggestions may appear strong under generic evaluation while failing specific user groups.

This proposal uses persona-affiliated user agents as interactive simulated users to expose this heterogeneity. The evaluation asks whether the chatbot can elicit and satisfy the latent utility of different users through dialogue.

## 3. Core Research Claim

Generic recommendation evaluation can hide heterogeneous user utility. Persona-conditioned chatbot evaluation turns a single natural-language request into a distributional test over users. This reveals whether the bot adapts to different latent preferences and whether its failures concentrate along known bias dimensions such as popularity bias.

A recommendation chatbot should avoid mapping the same underspecified query to the same mainstream answer across all users. It should treat recommendation as an interaction problem where heterogeneous user utility must be elicited and satisfied through dialogue.

Persona-affiliated user agents provide a structured simulation signal for early-stage diagnosis. Important findings should later be validated with real-user data.

## 4. Evaluation Goal

The goal is to evaluate whether a recommendation chatbot can:

1. handle the same underspecified request across heterogeneous personas,
2. ask useful clarification questions when the request is underspecified,
3. adapt recommendations after persona-specific preferences are revealed,
4. avoid over-relying on popular items when they conflict with user-specific utility.

Central diagnostic question:

```text
Does a popularity-biased recommendation chatbot appear acceptable under generic evaluation while losing utility for specific persona groups?
```

## 5. Scenario Overview

Each scenario consists of a recommendation domain, a candidate item catalog, a set of base user requests, and multiple personas attached to each request.

Possible domains:

- restaurants,
- hotels,
- laptops,
- local services,
- travel destinations,
- consumer products,
- fashion products,
- movies.

For each base request, the environment creates a group of persona variants. These variants share the same initial query and differ in latent preferences and constraints.

Example:

```text
Base request:
Can you recommend a good restaurant for dinner this weekend?

Persona A:
A parent looking for a quiet family-friendly restaurant with parking.

Persona B:
A budget-sensitive user who wants a local non-touristy place.

Persona C:
A vegetarian user who cares about menu flexibility.

Persona D:
A user looking for a high-end popular restaurant for a special occasion.
```

A strong chatbot should ask clarification questions, infer decision criteria from the conversation, and adapt its final recommendation across these users.

## 6. Interaction Protocol

For each evaluation episode, the environment runs a multi-turn conversation:

1. The persona-affiliated user agent sends the initial recommendation request.
2. The recommendation chatbot asks clarification questions or provides recommendations.
3. The user agent responds according to its persona, hidden constraints, and satisfaction state.
4. The chatbot updates its recommendation, asks follow-up questions, or explains tradeoffs.
5. The conversation ends when the user agent accepts, rejects, stops the conversation, or the turn budget is reached.
6. The environment records final recommendation quality, satisfaction, clarification behavior, and bias-sensitive metrics.

The user agent should behave like a realistic user. It should reveal relevant information when asked, correct bad assumptions when necessary, and express satisfaction or dissatisfaction based on its persona-conditioned decision rule.

## 7. Persona and User-Agent Design

Each persona contains:

- demographic or situational context,
- domain-specific preferences,
- hard constraints,
- soft preferences,
- budget or resource constraints,
- tolerance for popular or mainstream options,
- willingness to answer clarification questions,
- decision rule for accepting or rejecting recommendations,
- hidden satisfaction function,
- response style.

The persona profile should distinguish visible and hidden fields.

Visible fields are used for logging or optional profile-aware settings. Hidden fields define the user's latent utility and should be revealed through interaction. If the chatbot lacks direct access to hidden fields, the evaluation should reward useful elicitation and adaptation rather than direct guessing.

## 8. Recommendation Chatbots to Compare

### 8.1 Preference-Sensitive Chatbot

The preference-sensitive chatbot attempts to satisfy the user's stated and elicited preferences. When the query is underspecified, it asks clarification questions before committing to a narrow recommendation. It balances item relevance, hard constraints, soft preferences, diversity, and user-specific utility.

### 8.2 Popularity-Biased Chatbot

The popularity-biased chatbot overweights popularity, ratings, trending status, brand familiarity, or mainstream appeal. It may still sound fluent and helpful, yet it systematically promotes popular items even when they are weaker matches for the persona's latent preferences.

The popularity-biased chatbot should remain superficially plausible, so the evaluation tests bias localization rather than generic chatbot breakdown.

## 9. Bias Intervention

The core intervention is a controlled popularity prior added to the recommendation policy.

The preference-sensitive chatbot ranks or selects items based on query relevance, stated constraints, elicited preferences, and item fit.

The popularity-biased chatbot receives an additional preference for high-popularity items. This popularity prior can be parameterized by strength.

Key hypothesis:

```text
The popularity-biased chatbot may perform well for mainstream personas, while losing utility for personas whose preferences are poorly aligned with popular items.
```

The expected failure is segment-specific. The biased bot should specifically fail through popularity-mediated mechanisms, such as recommending popular near-miss items, ignoring long-tail options, or overusing popularity as justification.

## 10. Evaluation Metrics

### 10.1 Interaction Quality

- Clarification Rate
- Relevant Clarification Rate
- Premature Recommendation Rate
- Adaptation after User Feedback
- Turn Efficiency
- Failure to Follow User Correction

### 10.2 Persona Utility

- Final Satisfaction Score
- Acceptance Rate
- Constraint Satisfaction Rate
- Hard Constraint Violation Rate
- Soft Preference Match Rate
- Persona-Specific Utility@k

### 10.3 Popularity-Bias Diagnostics

- Mean Popularity@k
- Long-Tail Exposure@k
- Popular Near-Miss Rate
- Popularity-Utility Correlation
- Segment Utility Gap
- Recommendation Homogenization across Personas

### 10.4 Judge Comparison

- Generic LLM Judge Score
- Persona-Affiliated User Satisfaction Score
- Judge-User Disagreement Rate
- Cases where the generic judge rates both bots similarly while persona-conditioned feedback reveals a large utility gap

## 11. Expected Failure Modes

Expected failures of a popularity-biased chatbot include:

- recommending popular but persona-mismatched items,
- failing to ask clarification questions before recommending mainstream options,
- ignoring constraints revealed later in the conversation,
- over-explaining popularity signals such as ratings, trending status, or brand familiarity,
- converging to similar recommendations across different personas,
- achieving high generic judge scores while receiving low satisfaction from specific persona groups.

These failures help distinguish popularity-mediated recommendation bias from generic chatbot quality problems.

## 12. Minimal Deliverables for the First Version

The first version should include:

- this proposal document,
- a chatbot interaction protocol,
- a persona schema for recommendation conversations,
- a small set of same-query persona groups,
- a small synthetic item-catalog schema,
- definitions of preference-sensitive and popularity-biased chatbot policies,
- metric definitions,
- one example conversation trace.

The first version should avoid large-scale benchmark results, real user data, proprietary catalog data, and production chatbot integrations.

## 13. Concise Implementation Plan

### P0. Proposal

- Add this chatbot-first proposal under `applications/`.
- Open or link a GitHub issue for discussion.

### P1. Scenario Schema

- Define the episode format, persona fields, item catalog fields, transcript format, and stopping rule.
- Choose one initial domain for the first worked example.

### P2. Interaction and Baselines

- Define the user-agent response policy for gradual preference revelation.
- Define preference-sensitive and popularity-biased chatbot baselines.

### P3. Metrics and Example Trace

- Add metric definitions and one example conversation trace.
- Compare generic judge scores with persona-conditioned satisfaction in the example.

## 14. Non-Goals for the First Commit

This first proposal does not aim to:

- release a full recommendation benchmark,
- claim persona-affiliated agents are substitutes for real users,
- use private or proprietary user data,
- evaluate production recommendation systems,
- optimize recommendation algorithms,
- study all recommender bias types,
- provide large-scale empirical results.

The first goal is to define the scenario, protocol, and diagnostic metrics clearly enough for later implementation.

## 15. Related Work

### [Evaluating Large Language Models as Generative User Simulators for Conversational Recommendation](https://arxiv.org/abs/2403.09738)

- Defines a protocol for evaluating LLM-based user simulators in conversational recommendation.
- Tests item mention, binary preference, open-ended preference, recommendation request, and feedback behavior.
- Directly supports this proposal's focus on simulated user behavior, while motivating careful treatment of simulator failure modes such as popularity bias and weak preference alignment.

### [SimUSER: Simulating User Behavior with Large Language Models for Recommender System Evaluation](https://aclanthology.org/2025.acl-industry.5/)

- Proposes an LLM-based user simulation framework for recommender evaluation.
- Uses persona, memory, perception, and reasoning modules to simulate interaction with recommender systems.
- Supports the idea that persona-conditioned simulated users can provide useful pre-deployment evaluation signals for recommender systems.

### [Stop Playing the Guessing Game! Evaluating Conversational Recommender Systems via Target-free User Simulation](https://aclanthology.org/2025.findings-emnlp.1067/)

- Introduces PEPPER, a target-free user simulation protocol for conversational recommender systems.
- Emphasizes preference elicitation and multi-turn interaction instead of single target-item matching.
- Supports this proposal's chatbot-first setup and its focus on gradual preference discovery.

### [Rethinking the Evaluation for Conversational Recommendation in the Era of Large Language Models](https://arxiv.org/abs/2305.13112)

- Introduces iEvaLM, an interactive evaluation approach with LLM-based user simulators.
- Shows that traditional offline metrics can underestimate conversational recommendation ability.
- Provides a close precedent for evaluating CRS systems through simulated interaction.

### [Can LLM be a Personalized Judge?](https://aclanthology.org/2024.findings-emnlp.592/)

- Studies whether LLMs can judge user preferences from persona descriptions.
- Finds that direct persona-based LLM judging can be unreliable and sensitive to sparse persona descriptions.
- Motivates this proposal's cautious framing of persona-conditioned feedback as simulation telemetry rather than real-user ground truth.

### [The Unfairness of Popularity Bias in Recommendation](https://arxiv.org/abs/1907.13286)

- Studies popularity bias from the user perspective.
- Shows that popularity-biased recommendations can affect users differently depending on their interest in popular items.
- Supports this proposal's segment-level diagnostic design for popularity-mediated utility loss.

### [A Survey on Popularity Bias in Recommender Systems](https://arxiv.org/abs/2308.01118)

- Reviews causes, metrics, and mitigation methods for popularity bias in recommender systems.
- Summarizes computational approaches for detecting and reducing popularity bias.
- Provides background for the proposed popularity-bias diagnostics, such as long-tail exposure and popularity-utility correlation.

### [RecAgent: User Behavior Simulation with Large Language Model based Agents](https://arxiv.org/abs/2306.02552)

- Uses LLM-based agents and a sandbox environment to simulate user behavior in recommender systems.
- Studies emergent recommender phenomena such as information cocoons and conformity behavior.
- Supports the broader application of LLM-based user agents for recommender-system evaluation and analysis.

### [LLM-Powered User Simulator for Recommender System](https://arxiv.org/abs/2412.16984)

- Builds an LLM-powered simulator for user engagement with items.
- Emphasizes explicit preference logic, item characteristics, and sentiment modeling.
- Supports structured persona-conditioned feedback tied to item attributes and satisfaction signals.

### [Can Large Language Models Replace Human Subjects? A Large-Scale Replication of Scenario-Based Experiments](https://arxiv.org/abs/2409.00128)

- Replicates scenario-based human experiments using LLMs.
- Provides evidence that LLM-based simulations can support early-stage hypothesis testing while still requiring calibration.
- Supports the use of persona-affiliated agents as a simulation signal for evaluation design.

## 16. Candidate Benchmarks and Resources for Low-Adaptation Reuse

### [AgentRecBench: Benchmarking LLM Agent-based Personalized Recommender Systems](https://arxiv.org/abs/2505.19623)

- Provides an interactive textual recommendation simulator with rich user and item metadata.
- Covers classic recommendation, evolving-interest recommendation, and cold-start recommendation.
- Low-adaptation use: reuse item metadata and interaction scenarios, then add same-query persona groups and popularity-bias interventions.

### [WebShop: Towards Scalable Real-World Web Interaction with Grounded Language Agents](https://arxiv.org/abs/2207.01206)

- Provides a simulated e-commerce environment with real-world product data and natural-language product instructions.
- Evaluates agents that search, navigate, customize, and purchase products.
- Low-adaptation use: convert product instructions into chatbot recommendation requests and use catalog metadata for item grounding.

### [Towards Deep Conversational Recommendations, ReDial](https://arxiv.org/abs/1812.07617)

- Provides a large dataset of human-human movie recommendation dialogues.
- Useful for dialogue patterns, recommendation requests, user feedback, and movie-domain examples.
- Low-adaptation use: start from existing movie dialogues and add structured personas around user preferences.

### [Towards Topic-Guided Conversational Recommender System, TG-ReDial](https://aclanthology.org/2020.coling-main.365/)

- Provides topic-guided conversational recommendation data.
- Includes topic transitions that support richer multi-turn recommendation behavior.
- Low-adaptation use: use topic threads as conversation scaffolds and attach persona attributes to user-side preferences.

### [OpenDialKG: Explainable Conversational Reasoning with Attention-based Walks over Knowledge Graphs](https://aclanthology.org/P19-1081/)

- Provides human-human dialogues linked to knowledge-graph entities and paths.
- Useful for explainable conversational recommendation and entity-grounded item reasoning.
- Low-adaptation use: use entity and KG paths as item evidence for chatbot explanations and tradeoffs.

### [DuRecDial 2.0: A Bilingual Parallel Corpus for Conversational Recommendation](https://aclanthology.org/2021.emnlp-main.356/)

- Provides bilingual English-Chinese recommendation dialogues with profile, goal, knowledge, context, and response fields.
- Useful if the scenario should support multilingual or cross-lingual recommendation evaluation.
- Low-adaptation use: reuse profile and goal fields to seed personas and recommendation requests.

### [LLM-REDIAL: A Large-Scale Dataset for Conversational Recommender Systems Created from User Behaviors with LLMs](https://aclanthology.org/2024.findings-acl.529/)

- Provides a large multi-domain CRS dataset generated from user behavior data with LLMs.
- Useful for multi-domain dialogue templates and user-history-conditioned recommendation scenarios.
- Low-adaptation use: use its dialogue templates and historical interaction fields as seeds for synthetic persona and conversation generation.

### [CRSLab: An Open-Source Toolkit for Building Conversational Recommender System](https://aclanthology.org/2021.acl-demo.22/)

- Provides a unified toolkit for CRS datasets and models.
- Includes commonly used human-annotated CRS datasets and baseline models.
- Low-adaptation use: use CRSLab to run baseline CRS systems while focusing this proposal on persona-conditioned evaluation and telemetry.

## 17. Open Questions

- Should the chatbot receive an explicit user profile, or should all preferences be elicited through conversation?
- What turn budget should be used for the first version?
- Which recommendation domain should be used first?
- How should hard constraints and soft preferences be weighted?
- How should persona-conditioned satisfaction be calibrated across personas?
- Should the generic LLM judge evaluate the full transcript, the final recommendation, or both?
- How should we prevent user agents from over-disclosing hidden preferences too early?
- How should popularity be represented in the synthetic item catalog?
- How should we distinguish popularity bias from reasonable reliance on ratings or social proof?

## 18. Policy and Release Safety

This proposal is documentation-only. It does not include real user data, private conversations, proprietary catalogs, secrets, credentials, PHI, or PII.

Any future examples should use synthetic personas, synthetic item catalogs, and clearly documented generation procedures.

Persona-affiliated user-agent results should be treated as simulation-based diagnostic signals rather than real-user ground truth.
