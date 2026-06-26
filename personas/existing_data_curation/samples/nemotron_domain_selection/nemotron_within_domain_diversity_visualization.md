# Nemotron Within-Domain Diversity Visualization

This figure visualizes diversity **inside each application domain**. Each panel uses only the 50 selected users for that domain, so the figure answers: within this domain, are the selected personas spread across different overall profile types?

![Within-domain diversity projection](nemotron_within_domain_diversity_projection.svg)

## Method

- Build one text representation per selected persona from demographics, persona sections, attributes, and background fields.
- For each domain separately, convert the 50 persona texts into TF-IDF unigram/bigram features.
- Reduce each domain-specific feature matrix to two dimensions with truncated SVD.
- Draw one panel per domain with a light coverage ellipse.
- Size points by distance from that domain panel centroid, so larger points are more distinct within that domain.

Panel coordinates are not comparable across domains because each panel is fit separately. This is intentional: the goal is within-domain diversity, not cross-domain separation.

## Within-Domain Diversity Metrics

| Domain | Users | Mean pairwise cosine distance | Median pairwise cosine distance | Mean projected radius | P90 projected radius |
|---|---:|---:|---:|---:|---:|
| Movie / film | 50 | 0.830 | 0.850 | 0.156 | 0.255 |
| Beauty | 50 | 0.832 | 0.868 | 0.163 | 0.444 |
| Game | 50 | 0.821 | 0.859 | 0.186 | 0.366 |
| Finance | 50 | 0.817 | 0.839 | 0.150 | 0.302 |
| Medical / healthcare | 50 | 0.815 | 0.844 | 0.147 | 0.274 |
| Ecommerce / retail | 50 | 0.817 | 0.836 | 0.166 | 0.258 |

## Interpretation

The mean pairwise cosine distance is computed before projection in the reduced persona-text feature space. Higher values indicate that the selected users in that domain are more textually/profile diverse overall. The projection is a visual aid for spotting concentration or multiple profile regions within each domain.