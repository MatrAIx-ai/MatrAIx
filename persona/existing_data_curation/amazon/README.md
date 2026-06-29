# Amazon Existing-Data Workflows

This folder contains Amazon Reviews 2023 downstream workflows imported from
PersonaBench PR #1 and adapted for MatrAIx.

- `extraction/infer_amazon_review_dimensions.py` builds compact review-memory
  profiles and maps them onto `persona/dimensions.json`.
- `extraction/render_amazon_inference_report.py` renders pilot inference JSONL
  files for inspection.
- `evaluation/evaluate_amazon_persona_rating_holdout.py` prepares blind
  temporal-holdout rating targets and scores baselines or persona predictions.
- `evaluation/predict_amazon_persona_holdout_ratings.py` predicts held-out
  ratings from constructed personas.
- `subscription_json_backend.py` routes LLM calls through local subscription
  CLIs (`codex` or `claude`) instead of HTTP API keys.

The expected input history format is the normalized one-user-per-row JSONL
written by `../scripts/export_hf_amazon_user_histories.py`.
