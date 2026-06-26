# Amazon Top 10K Rich Persona Reviewers

This file documents a reusable top-10K Amazon reviewer pool for persona inference. It is intended for staged inference runs when running all eligible users at once is too expensive.

## Source

- Hugging Face dataset: `MatrAIx/MatrAIx`
- Source artifact: `amazon/modal_artifacts/amazon_reviews_2018_2023_eligible_users_min30_verified70_text2000`
- Source artifact time window: `2018-2023`
- Source eligibility filter: `review_count >= 30`, `verified_share >= 0.70`, `text_chars >= 2000`
- Eligible rows loaded: `1,744,018`
- Selected rows: `10,000`

## Output Files

- `amazon_top_10000_rich_persona_reviewer_ids_2018_2023.txt`: one user ID per line for retrieval/inference jobs.
- `amazon_top_10000_rich_persona_reviewers_2018_2023.jsonl`: ranked users with scoring metrics and category metadata.
- `amazon_top_10000_rich_persona_reviewers_2018_2023.csv`: same ranked table in CSV form for quick inspection.

## Ranking Score

The ranking score is a weighted sum of percentile ranks across richness signals. Percentile ranks are used because Amazon review activity is heavy-tailed.

| Signal | Weight | Why it matters |
|---|---:|---|
| `text_chars` | 0.35 | More written evidence for values, preferences, routines, and decision style. |
| `text_reviews` | 0.20 | More distinct text-bearing observations. |
| `category_count` | 0.20 | Broader life/product coverage, supporting richer cross-domain personas. |
| `history_days` | 0.15 | Longer temporal history, reducing one-off or short-burst behavior. |
| `review_count` | 0.05 | More total rating/review events, including rating-only behavior. |
| `verified_share` | 0.05 | Higher purchase-verification reliability. |

## Selected Pool Summary

| Metric | Min | P25 | Median | P75 | P90 | P99 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|
| `review_count` | 84.000 | 170.000 | 218.000 | 294.000 | 405.000 | 833.010 | 4072.000 |
| `text_reviews` | 84.000 | 170.000 | 218.000 | 294.000 | 405.000 | 833.010 | 4072.000 |
| `text_chars` | 16505.000 | 37328.750 | 53288.500 | 82207.000 | 128656.300 | 366813.520 | 2604472.000 |
| `category_count` | 16.000 | 20.000 | 21.000 | 23.000 | 24.000 | 27.000 | 31.000 |
| `history_days` | 1730.000 | 1854.000 | 1876.000 | 1891.000 | 1901.000 | 1927.000 | 1982.000 |
| `verified_share` | 0.700 | 0.953 | 0.977 | 0.989 | 0.995 | 1.000 | 1.000 |
| `rich_persona_score` | 0.932 | 0.937 | 0.943 | 0.952 | 0.960 | 0.973 | 0.985 |

## Top 20 Preview

| Rank | User ID | Score | Reviews | Text reviews | Text chars | Categories | History days | Verified share |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | `AEVCYNI3IXMGN7NK6VK454TCPJVQ` | 0.9848 | 593 | 593 | 108109 | 24 | 1890.0 | 1.000 |
| 2 | `AHBMDQZGIGQKZVWUZY2V5HGAEDLA` | 0.9812 | 177 | 177 | 117022 | 21 | 1916.0 | 1.000 |
| 3 | `AGEDEMV6OQEVYWVUJZ7ARFBDDRLA` | 0.9812 | 257 | 257 | 133037 | 24 | 1881.0 | 1.000 |
| 4 | `AGEF6JWOYITDQSWDUJKVHOD5PVBA` | 0.9804 | 284 | 284 | 63574 | 21 | 1899.0 | 1.000 |
| 5 | `AGYWTBGBT5TZTCPI4ARWUBQP7QJQ` | 0.9799 | 440 | 440 | 78473 | 21 | 1888.0 | 1.000 |
| 6 | `AFL6LNJSCK64JALLU5BITXAJB7PA` | 0.9797 | 518 | 518 | 82461 | 26 | 1914.0 | 0.992 |
| 7 | `AEFBQNPW45PS7HT4S2K2CXJ7QD4A` | 0.9793 | 375 | 375 | 63761 | 24 | 1880.0 | 1.000 |
| 8 | `AGEDGOQOBKXG2GD72DWL7IMICSLA` | 0.9792 | 217 | 217 | 58588 | 22 | 1896.0 | 1.000 |
| 9 | `AESJGWCGL52BA3R6ZYEZ34YF5GHQ` | 0.9792 | 363 | 363 | 135288 | 22 | 1922.0 | 0.992 |
| 10 | `AFNV4FEWBULFC76I2CE5IUSNIP5Q` | 0.9791 | 390 | 390 | 73804 | 25 | 1930.0 | 0.990 |
| 11 | `AFOWHOG3GLMBU5IF45DTKDL3UVZQ` | 0.9791 | 230 | 230 | 313161 | 21 | 1885.0 | 1.000 |
| 12 | `AHCU7R3ZFK5U2LYRDXTMFJKZ6PQQ` | 0.9788 | 559 | 559 | 129132 | 26 | 1897.0 | 0.995 |
| 13 | `AEF4A5PLYVU67SYR67JR3227YS4A` | 0.9785 | 2253 | 2253 | 1048395 | 28 | 1905.0 | 0.984 |
| 14 | `AGF3S7SP4POWQFRMEHW3EKQLDQEQ` | 0.9783 | 207 | 207 | 92430 | 23 | 1881.0 | 1.000 |
| 15 | `AHYO5RTFJMKUUH4MAEIJMNK7MKJA` | 0.9782 | 465 | 465 | 65476 | 23 | 1921.0 | 0.996 |
| 16 | `AFE2N6HZLRYEZ2PG2QX6FDYTEULA` | 0.9782 | 960 | 960 | 154104 | 25 | 1914.0 | 0.983 |
| 17 | `AF77X636QF2W6A5CLY3XSBVIIJUA` | 0.9780 | 333 | 333 | 112716 | 22 | 1930.0 | 0.988 |
| 18 | `AFIIU7UHCHTG2CV7WNIXUTB3MU5Q` | 0.9780 | 257 | 257 | 142705 | 22 | 1917.0 | 0.992 |
| 19 | `AHYGFP6Y3PGXZN5FDOGUDOL4K3RA` | 0.9778 | 204 | 204 | 67313 | 24 | 1883.0 | 1.000 |
| 20 | `AF6MH74A4E45AV3OGDIU4RE5B6HQ` | 0.9777 | 547 | 547 | 237340 | 25 | 1901.0 | 0.985 |

## Reproducibility Note

The selected users are ranked from the existing eligible-user summary artifact, not by reading raw review text or calling an LLM. This makes the list cheap to regenerate and suitable as a shared inference queue.