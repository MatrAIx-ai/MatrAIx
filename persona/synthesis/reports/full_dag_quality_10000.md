# Persona Full DAG Quality Report

## Run

- Graph: `persona/synthesis/graph/full_dag.json`
- Samples: 10,000
- Seed: 42
- Generated at: 2026-06-30T05:42:18+00:00
- Python: 3.13.14
- Platform: macOS-15.6-arm64-arm-64bit-Mach-O

## Timing

| Step | Time |
| --- | ---: |
| Load and compile sampler | 0.3969s |
| Static validation | 0.2710s |
| Sample integer-coded DAG rows | 1.5679s |
| Marginal audit | 0.0075s |
| Consistency audit | 1.3448s |
| End-to-end report runtime | 3.5881s |

Sampling throughput: 6378.0 samples/sec.
End-to-end throughput: 2787.0 samples/sec.

## Static Graph Validation

- Validation passed: `true`
- Nodes: 1,357
- Emitted nodes: 1,230
- Directed proposal edges: 6,937
- Full CPT overlays: 53
- Full CPT rows: 13,491
- Conditional masks: 95
- Missing refs: 0
- Duplicate node ids: 0
- Duplicate directed pairs: 0
- Cycle-free: `true`
- Topological dependency violations: 0

## Consistency Audit

- Personas with hard issues: 0 (0.00%)
- Personas with hard or strong issues: 3 (0.03%)
- Personas with any flagged issue: 29 (0.29%)
- Severity issue counts: `{"soft": 26, "strong": 3}`
- Group issue counts: `{"finance": 29}`

Top consistency rules:

| Rule | Severity | Group | Count | Share |
| --- | --- | --- | ---: | ---: |
| `unbanked_mobile_wallet_or_crypto_payment` | soft | finance | 26 | 0.26% |
| `minor_active_investment` | strong | finance | 3 | 0.03% |

## Focus-Node Marginal Drift

TVD is total variation distance between the sample marginal and the node prior.

| Node | TVD vs prior | Top sampled values |
| --- | ---: | --- |
| `life_stage` | 0.1742 | Mid-life: sample 24.97%, prior 14.29%; Early career: sample 17.95%, prior 14.29%; Student: sample 16.43%, prior 14.29%; Parent of young kids: sample 15.21%, prior 14.29% |
| `seniority` | 0.1458 | Student / intern: sample 24.30%, prior 17.00%; Entry: sample 19.65%, prior 14.50%; Mid: sample 17.51%, prior 25.50%; Senior: sample 11.84%, prior 15.00% |
| `role_function` | 0.1271 | Operations: sample 31.85%, prior 28.75%; Engineering: sample 10.62%, prior 11.25%; Sales / GTM: sample 9.40%, prior 10.00%; Research: sample 7.81%, prior 2.50% |
| `years_experience` | 0.1105 | 0-2: sample 29.44%, prior 25.50%; 11-20: sample 21.90%, prior 22.00%; 20+: sample 19.61%, prior 12.50%; 6-10: sample 16.75%, prior 21.00% |
| `english_proficiency` | 0.1031 | None: sample 37.95%, prior 29.00%; Basic (A1-A2): sample 18.35%, prior 18.00%; Intermediate (B1-B2): sample 15.57%, prior 17.00%; Fluent (C1-C2): sample 15.51%, prior 14.50% |
| `tech_savviness` | 0.0642 | Comfortable: sample 30.56%, prior 33.50%; Cautious adopter: sample 25.48%, prior 25.00%; Reluctant: sample 18.75%, prior 15.50%; Digital native: sample 15.02%, prior 18.50% |
| `highest_education` | 0.0631 | Secondary: sample 45.99%, prior 42.00%; Primary: sample 21.32%, prior 19.00%; Bachelor's: sample 11.17%, prior 14.50%; No formal: sample 9.83%, prior 10.50% |
| `domain` | 0.0127 | Agriculture: sample 24.55%, prior 24.00%; Manufacturing: sample 11.99%, prior 12.00%; Business & Management: sample 10.13%, prior 10.00%; Hospitality: sample 7.21%, prior 7.00% |
| `demo_religion_affiliation` | 0.0116 | Christian: sample 28.81%, prior 28.80%; Muslim: sample 24.98%, prior 25.60%; Hindu: sample 15.16%, prior 14.90%; None: sample 9.58%, prior 9.30% |
| `primary_language` | 0.0116 | English: sample 21.14%, prior 21.50%; Mandarin: sample 20.69%, prior 20.50%; Hindi: sample 10.70%, prior 10.50%; Spanish: sample 10.31%, prior 10.00% |
| `demo_employment_status` | 0.0100 | Full-time: sample 33.85%, prior 33.50%; Student: sample 13.80%, prior 13.50%; Retired: sample 10.74%, prior 11.00%; Self-employed: sample 10.66%, prior 10.50% |
| `demo_ethnicity_broad` | 0.0098 | South Asian: sample 25.36%, prior 25.00%; East Asian: sample 20.71%, prior 20.50%; Black / African: sample 14.18%, prior 14.50%; White / European: sample 10.55%, prior 10.50% |
| `demo_children_count` | 0.0095 | None: sample 41.78%, prior 42.00%; 2 children: sample 17.83%, prior 17.50%; 3+ children: sample 16.52%, prior 16.00%; 1 child: sample 12.77%, prior 13.50% |
| `urbanicity` | 0.0078 | Rural: sample 34.53%, prior 34.50%; Dense urban: sample 24.69%, prior 24.50%; Suburban: sample 20.25%, prior 21.00%; Small town: sample 19.06%, prior 18.50% |
| `age_bracket` | 0.0076 | 25-34: sample 19.78%, prior 19.70%; 35-44: sample 17.29%, prior 17.10%; 45-54: sample 14.47%, prior 14.50%; 18-24: sample 14.09%, prior 13.60% |
| `region` | 0.0070 | South Asia: sample 25.37%, prior 25.23%; East Asia: sample 19.74%, prior 19.41%; Sub-Saharan Africa: sample 16.69%, prior 16.85%; Southeast Asia: sample 8.69%, prior 8.78% |
| `socioeconomic_band` | 0.0050 | Lower-middle: sample 33.39%, prior 33.00%; Low income: sample 33.14%, prior 33.50%; Middle: sample 21.61%, prior 21.50%; Upper-middle: sample 9.50%, prior 9.50% |
| `gender_identity` | 0.0028 | Man: sample 50.02%, prior 49.80%; Woman: sample 49.27%, prior 49.50%; Non-binary: sample 0.33%, prior 0.30%; Self-described: sample 0.23%, prior 0.20% |

## Interpretation

- The static graph checks are structural checks over the committed JSON.
- The sampling audit is stochastic and should be compared with the seed and sample count.
- Marginal drift from priors is expected for non-root nodes because pairwise edges, full CPTs, and masks intentionally condition later fields on earlier fields.
- Hard consistency issues should be treated as blockers. Strong and soft issues are triage signals for graph refinement.
