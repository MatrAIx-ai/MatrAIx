# Nemotron Overall Diversity Visualization

This figure visualizes the 300 selected Nemotron personas from `nemotron_test_users_50_per_domain.md`: 50 users per application domain.

![Overall diversity projection](nemotron_overall_diversity_projection.svg)

## Method

This is an **overall-diversity** view, not a demographic- or dimension-specific diversity chart.

- Build one text representation per selected persona using demographics, persona sections, attributes, and background fields.
- Convert persona text to TF-IDF features with unigram and bigram terms.
- Reduce persona text features to two dimensions with truncated SVD.
- Color points by application domain and draw a light coverage ellipse for each domain.

Interpretation: wider spread within a color indicates broader overall profile coverage for that domain. Overlap between colors indicates cross-domain persona similarity, which can be useful for testing whether applications distinguish domain needs rather than only broad demographics.

## Overall Diversity Metrics

| Domain | Users | Mean pairwise cosine distance | Median pairwise cosine distance | Mean projected radius | P90 projected radius |
|---|---:|---:|---:|---:|---:|
| Movie / film | 50 | 0.808 | 0.831 | 0.057 | 0.095 |
| Beauty | 50 | 0.820 | 0.867 | 0.104 | 0.196 |
| Game | 50 | 0.768 | 0.827 | 0.061 | 0.119 |
| Finance | 50 | 0.735 | 0.757 | 0.072 | 0.128 |
| Medical / healthcare | 50 | 0.734 | 0.757 | 0.081 | 0.164 |
| Ecommerce / retail | 50 | 0.754 | 0.786 | 0.053 | 0.099 |

The pairwise cosine-distance metrics are computed in the reduced persona-text feature space. They are better suited for comparing within-domain spread than visual distances alone.

## Practical Takeaway

The selected users are not intended to be balanced by one visible field. They are intended to cover different overall persona profiles within each application domain, while preserving domain relevance. The detailed rationale for each selected user remains in `nemotron_test_users_50_per_domain.md`.