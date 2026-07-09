#!/usr/bin/env python3
"""Production Amazon-reviewer persona extraction — sharded, resumable, 1 GPU.

One array task = one user_bucket (hex 00..ff) = one GPU. For its bucket it:
  1. loads the selection index (data/amazon/selected_users_100k.parquet),
  2. downloads that bucket's raw reviews from the gated HF dataset,
  3. assembles each selected user's reviews into a single profile_text,
  4. runs the Amazon persona prompt over all category dimension-chunks, and
  5. appends one JSON object per user to data/amazon/extraction_v1/shard_<bkt>.jsonl.

Persona = one user. Resumable: skips user_id already written, so a preempted /
re-queued task continues where it left off. Output schema matches the wiki
extractor (fields:[{field_id,value,confidence,evidence,description,assignment_type}]).

A100 80GB note: the 35B MoE is ~70 GB in bf16 and will not leave room for the KV
cache on a single 80 GB card, so this script defaults to --quantization fp8
(weight-only FP8 via Marlin on Ampere → ~35 GB weights, plenty of KV headroom).

Example (single card):
  python run_extraction_amazon.py --shard-id 0 --quantization fp8 \
      --out-dir data/amazon/extraction_v1
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

CACHE = "/n/netscratch/lu_lab/Lab/xiaominli/mycache/hf_home"
os.environ.setdefault("HF_HOME", CACHE)
os.environ.setdefault("HF_HUB_CACHE", f"{CACHE}/hub")
os.environ.setdefault("HF_XET_CACHE", f"{CACHE}/xet")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

import pandas as pd  # noqa: E402

REPO_ROOT = Path("/n/netscratch/lu_lab/Lab/xiaominli/LLMResearch/MatrAIx")
DATA_DIR = REPO_ROOT / "persona/human_extraction/data"
SELECTION = DATA_DIR / "amazon/selected_users_100k.parquet"
DIMENSIONS_JSON = REPO_ROOT / "persona/schema/dimensions.json"
MODEL_ID = "Qwen/Qwen3.6-35B-A3B"
OPENROUTER_MODEL_ID = "qwen/qwen3.6-35b-a3b"
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
ASSIGNMENT_TYPES = {
    "direct",
    "structured_claim",
    "summary_inference",
    "unsupported",
}
NULLISH_VALUES = {
    "",
    "none",
    "null",
    "n/a",
    "na",
    "unknown",
    "unsupported",
    "not applicable",
}

DATASET_REPO = "MatrAIx2026/MatrAIx2026"
UBUK = ("amazon/modal_artifacts/"
        "amazon_reviews_2018_2023_user_buckets_min30_verified70_text2000")

REVIEW_TMPL = ("[{date}] {category} | {parent_asin} | rating={rating:.0f}/5 | "
               "verified={verified}\nTitle: {title}\n{text}")


def hf_token() -> str | None:
    tok = os.environ.get("HF_TOKEN") or os.environ.get("HF_TOKEN_matraix")
    if tok:
        return tok
    bashrc = Path(os.path.expanduser("~/.bashrc"))
    if bashrc.exists():
        for line in bashrc.read_text().splitlines():
            m = re.search(r"HF_TOKEN_matraix=['\"]?([^'\"\s]+)", line)
            if m:
                return m.group(1)
    return None


def assemble_profile(g: pd.DataFrame, max_chars: int) -> str:
    """Concatenate one user's reviews (chronological) into a profile_text."""
    g = g.sort_values("timestamp")
    parts = [REVIEW_TMPL.format(
                date=r.date, category=r.category, parent_asin=r.parent_asin,
                rating=float(r.rating), verified=bool(r.verified_purchase),
                title=(r.title or ""), text=(r.text or ""))
             for r in g.itertuples()]
    header = (f"Amazon reviewer profile — {len(g)} reviews across "
              f"{g.category.nunique()} categories.\n\n")
    return (header + "\n\n".join(parts))[:max_chars]


def build_amazon_prompt(profile_text: str, dimensions: list[dict]) -> str:
    """Amazon-reviewer persona-extraction prompt (see extract_personas_amazon.ipynb)."""
    lines = [
        "You are mapping observable Amazon review evidence to schema-constrained "
        "persona fields for one reviewer. Fill attributes that are well supported "
        "by the review history, and leave unsupported or identity-like claims null.",
        "",
        "Important: emitting one field object is bookkeeping, not permission to "
        "fill the attribute. For every dimension, start from value=null and "
        'assignment_type="unsupported". Change value only when the evidence '
        "passes the rules below.",
        "",
        "Return ONLY JSON with this shape (no markdown, no commentary):",
        '{"fields": [{"field_id": "<one id from DIMENSIONS below>", '
        '"value": "<one allowed value, copied verbatim, or null>", '
        '"confidence": 0.0, '
        '"evidence": "<one short exact quote copied from REVIEWER HISTORY, or empty string>", '
        '"description": "<1-2 concrete sentences, or empty string>", '
        '"assignment_type": "direct|structured_claim|summary_inference|unsupported"}]}',
        "",
        "Allowed support:",
        "- direct: use when the reviewer explicitly states the fact about "
        "themselves in review text.",
        "- structured_claim: use for repeated owned/use-context statements or "
        "concrete non-sensitive purchase/review facts supported by at least 2 "
        "distinct reviews, products, or category clusters.",
        "- summary_inference: use for non-sensitive interests, shopping behavior, "
        "preferences, review style, communication style, or expertise when a "
        "repeated pattern is visible across the review history.",
        "- Overall writing style may support communication/cognitive-style "
        "dimensions only when the pattern is visible across at least 5 reviews.",
        "- unsupported: use when evidence is absent, one-off, ambiguous, generic, "
        "gift-related, or mainly about someone other than the reviewer.",
        "",
        "Hard limits:",
        "- For age, gender, health, disability, ethnicity, religion, politics, "
        "income, family/household status, occupation, location, employment, and "
        "parenthood: assign a non-null value only from an explicit self-statement. "
        "Do not use product category alone.",
        "- Do not attribute traits of gift recipients or other product users to "
        "the reviewer. A gift may support shopping behavior, not the reviewer's "
        "own identity, household, or hobbies.",
        "- Generic praise like \"great product\" or product titles alone is not "
        "diagnostic evidence for persona attributes.",
        "- Do not infer personality inventories, values, worldview, MBTI, Big "
        "Five, HEXACO, clinical attributes, or mental-state attributes from "
        "ordinary shopping reviews unless the reviewer explicitly states the "
        "trait or belief.",
        "",
        "Output rules:",
        "- Emit exactly one object per dimension listed below.",
        "- Do not output any field_id that is not listed in DIMENSIONS.",
        "- Do not duplicate field_id. Each listed field_id appears exactly once.",
        "- Do not omit assignment_type. Every object must include one of the four "
        "assignment_type strings above.",
        "- value MUST be exactly one of that dimension's allowed values (copied "
        "verbatim), OR null.",
        '- Never use "Unsupported", "unsupported", "Not applicable", "N/A", '
        '"unknown", or "" as value unless that exact string appears in that '
        "field's allowed values.",
        "- Judge the history as a whole; prefer attributes backed by MULTIPLE "
        "reviews over a single purchase (one-off items may be gifts for others).",
        "- If the reviews do not support a dimension, set value to null, "
        'confidence to 0.0, evidence to "", assignment_type to "unsupported", '
        'and description to "".',
        "- Every non-null value MUST include a short evidence quote copied "
        "verbatim from one of the reviews.",
        "- Evidence must be an exact quote from REVIEWER HISTORY, not your reasoning, "
        "a paraphrase, or a summary. If you cannot copy an exact quote, return "
        "unsupported.",
        "- If you cannot copy an exact quote, return unsupported.",
        "- Do not append support counts, explanations, or labels to evidence. "
        "Evidence must be only text that appears in REVIEWER HISTORY.",
        "- description: 1-2 concrete sentences describing THIS shopper for this "
        "attribute using details from their reviews (categories, products, "
        "statements). Describe the person; do not justify the label.",
        "- Sensitive / high-risk fields require explicit self-statements: age, "
        "gender, income, marital status, children count, religion, politics, "
        "ethnicity, health, disability, mental health, neurotype, MBTI, Big Five, "
        "personality traits, attachment style, and relationship style.",
        "- Do not infer these fields from product category, product size, possible "
        "gift purchases, cooking tools, romance books, writing style, tone, "
        "vocabulary, price level, or household items.",
        "- Return valid JSON only, with no markdown.",
        "- Most dimensions can be unsupported. Do not make the persona complete.",
        "",
        "DIMENSIONS (field_id — label — description — allowed values):",
    ]
    for d in dimensions:
        allowed = " | ".join(str(v) for v in d.get("values", [])) or "(free value)"
        desc = str(d.get("description", "")).strip()
        lines.append(f"- {d['id']} — {d.get('label', d['id'])} — {desc} — [{allowed}]")
    lines += ["", "REVIEWER HISTORY:", profile_text]
    return "\n".join(lines)


def parse_fields(text: str) -> list[dict]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return []
    try:
        obj = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return []
    if not isinstance(obj, dict):
        return []
    fields = obj.get("fields")
    return fields if isinstance(fields, list) else []


def _unsupported(dim: dict) -> dict:
    return {
        "field_id": str(dim["id"]),
        "value": None,
        "confidence": 0.0,
        "evidence": "",
        "description": "",
        "assignment_type": "unsupported",
    }


def _confidence(value) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, confidence))


def _normalized_key(value: str) -> str:
    return " ".join(value.replace("-", "–").split()).casefold()


def _coerce_value(value, dim: dict) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if text.casefold() in NULLISH_VALUES:
        return None
    allowed = [str(item) for item in dim.get("values", [])]
    if not allowed:
        return text
    if text in allowed:
        return text
    allowed_by_key = {_normalized_key(item): item for item in allowed}
    return allowed_by_key.get(_normalized_key(text))


def _quote_is_in_profile(evidence: str, profile_text: str) -> bool:
    if not evidence:
        return False
    if evidence in profile_text:
        return True
    return " ".join(evidence.split()) in " ".join(profile_text.split())


def sanitize_fields(
    fields: list[dict],
    dimensions: list[dict],
    profile_text: str = "",
) -> list[dict]:
    """Clamp Amazon model output to one schema-conformant field per dimension."""
    dim_by_id = {str(dim["id"]): dim for dim in dimensions}
    best_by_id: dict[str, dict] = {}

    for raw in fields:
        if not isinstance(raw, dict):
            continue
        field_id = str(raw.get("field_id") or "").strip()
        dim = dim_by_id.get(field_id)
        if dim is None:
            continue

        assignment_type = str(raw.get("assignment_type") or "").strip()
        value = _coerce_value(raw.get("value"), dim)
        confidence = _confidence(raw.get("confidence"))
        evidence = str(raw.get("evidence") or "").strip()
        description = str(raw.get("description") or "").strip()
        supported = (
            value is not None
            and assignment_type in ASSIGNMENT_TYPES
            and assignment_type != "unsupported"
            and _quote_is_in_profile(evidence, profile_text)
        )

        if supported:
            clean = {
                "field_id": field_id,
                "value": value,
                "confidence": confidence,
                "evidence": evidence,
                "description": description,
                "assignment_type": assignment_type,
            }
        else:
            clean = _unsupported(dim)

        prior = best_by_id.get(field_id)
        if prior is None:
            best_by_id[field_id] = clean
            continue
        prior_supported = prior.get("value") is not None
        clean_supported = clean.get("value") is not None
        if clean_supported and not prior_supported:
            best_by_id[field_id] = clean
        elif clean_supported == prior_supported and _confidence(
            clean.get("confidence")
        ) > _confidence(prior.get("confidence")):
            best_by_id[field_id] = clean

    return [best_by_id.get(str(dim["id"])) or _unsupported(dim) for dim in dimensions]


def cat_chunks(by_category: dict, per_chunk: int):
    out = []
    for cat_dims in by_category.values():
        for i in range(0, len(cat_dims), per_chunk):
            out.append(cat_dims[i : i + per_chunk])
    return out


def load_bucket_reviews(bucket: str, token: str | None) -> pd.DataFrame:
    """All reviews in one user_bucket (across every category file)."""
    from huggingface_hub import HfApi, hf_hub_download
    api = HfApi(token=token)
    files = [f for f in api.list_repo_files(DATASET_REPO, repo_type="dataset")
             if f.startswith(f"{UBUK}/bucket={bucket}/") and f.endswith(".parquet")]
    dfs = [pd.read_parquet(hf_hub_download(DATASET_REPO, f, repo_type="dataset",
                                           token=token)) for f in files]
    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


def openrouter_chat(
    conversations: list[list[dict]],
    *,
    model: str,
    api_key: str,
    base_url: str,
    max_tokens: int,
    temperature: float = 0.0,
    retries: int = 6,
) -> list[str]:
    """Run prompts through OpenRouter's OpenAI-compatible chat endpoint."""
    texts: list[str] = []
    for conv in conversations:
        payload = {
            "model": model,
            "messages": conv,
            "temperature": temperature,
            "top_p": 1.0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            base_url,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "MatrAIx Amazon persona extraction",
            },
            method="POST",
        )
        for attempt in range(retries):
            try:
                with urllib.request.urlopen(req, timeout=300) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                texts.append(data["choices"][0]["message"]["content"])
                break
            except urllib.error.HTTPError as err:
                err_body = err.read().decode("utf-8", errors="replace")
                retryable = err.code in {408, 429, 500, 502, 503, 504}
                if retryable and attempt < retries - 1:
                    time.sleep(min(60, 2 ** attempt))
                    continue
                raise RuntimeError(
                    f"OpenRouter API error {err.code}: {err_body[:1000]}"
                ) from err
            except (urllib.error.URLError, KeyError, IndexError, TypeError) as err:
                if attempt < retries - 1:
                    time.sleep(min(60, 2 ** attempt))
                    continue
                raise RuntimeError(f"OpenRouter request failed: {err}") from err
    return texts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard-id", type=int, required=True,
                    help="0..255 -> user_bucket hex 00..ff")
    ap.add_argument("--out-dir", default=str(DATA_DIR / "amazon/extraction_v1"))
    ap.add_argument("--batch-profiles", type=int, default=32,
                    help="profiles per vLLM submit / checkpoint granularity")
    ap.add_argument("--max-dims-per-chunk", type=int, default=50)
    ap.add_argument("--max-tokens", type=int, default=8192)
    ap.add_argument("--max-model-len", type=int, default=32768)
    ap.add_argument("--max-profile-chars", type=int, default=48000)
    ap.add_argument("--gpu-mem", type=float, default=0.90)
    ap.add_argument("--max-num-seqs", type=int, default=64)
    ap.add_argument("--tensor-parallel", type=int, default=1,
                    help="GPUs per task (2 => bf16 fits across 2x A100 80GB, no quant)")
    ap.add_argument("--quantization", default="fp8",
                    help="fp8 (fits single A100 80GB) | none (bf16, needs 2x A100)")
    ap.add_argument("--limit", type=int, default=0, help="debug: cap users this shard")
    ap.add_argument("--backend", choices=("vllm", "openrouter"), default="vllm")
    ap.add_argument("--openrouter-model", default=OPENROUTER_MODEL_ID)
    ap.add_argument("--openrouter-api-key-env", default="OPENROUTER_API_KEY")
    ap.add_argument("--openrouter-base-url", default=OPENROUTER_CHAT_URL)
    args = ap.parse_args()

    bucket = f"{args.shard_id:02x}"
    token = hf_token()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"shard_{bucket}.jsonl"

    # --- schema / chunks ---
    schema_doc = json.load(open(DIMENSIONS_JSON))
    by_category: dict[str, list] = {}
    for d in schema_doc["dimensions"]:
        by_category.setdefault(d.get("category", "Uncategorized"), []).append(d)
    chunk_list = cat_chunks(by_category, args.max_dims_per_chunk)

    # --- selection for this bucket ---
    sel = pd.read_parquet(SELECTION)
    sel_b = sel[sel.user_bucket == bucket]
    want = set(sel_b.user_id)
    review_count = dict(zip(sel_b.user_id, sel_b.review_count))
    if args.limit:
        want = set(list(want)[: args.limit])

    # --- resume: skip already-written user_id ---
    done: set[str] = set()
    if out_path.exists():
        with open(out_path) as fh:
            for line in fh:
                try:
                    done.add(json.loads(line)["user_id"])
                except Exception:
                    pass
    todo_ids = [u for u in want if u not in done]

    print(f"[shard {args.shard_id} bucket={bucket}] selected={len(sel_b):,} "
          f"want={len(want):,} done={len(done):,} todo={len(todo_ids):,} "
          f"chunks/user={len(chunk_list)}", flush=True)
    if not todo_ids:
        print("[shard] nothing to do — complete.", flush=True)
        return

    # --- load this bucket's reviews and assemble profiles ---
    t0 = time.time()
    rev = load_bucket_reviews(bucket, token)
    rev = rev[rev.user_id.isin(set(todo_ids))]
    profiles = {uid: assemble_profile(g, args.max_profile_chars)
                for uid, g in rev.groupby("user_id", sort=False)}
    todo = [u for u in todo_ids if u in profiles]
    print(f"[shard] loaded {len(rev):,} reviews, assembled {len(profiles):,} "
          f"profiles in {time.time()-t0:.0f}s", flush=True)

    # --- load model/client once ---
    t0 = time.time()
    if args.backend == "vllm":
        from vllm import LLM, SamplingParams  # noqa: PLC0415

        llm_kwargs = dict(
            model=MODEL_ID,
            dtype="bfloat16",
            tensor_parallel_size=args.tensor_parallel,
            gpu_memory_utilization=args.gpu_mem,
            max_model_len=args.max_model_len,
            max_num_seqs=args.max_num_seqs,
            enable_prefix_caching=True,
            trust_remote_code=True,
            download_dir=f"{CACHE}/hub",
        )
        if args.quantization and args.quantization.lower() != "none":
            llm_kwargs["quantization"] = args.quantization
        llm = LLM(**llm_kwargs)
        sampling = SamplingParams(temperature=0.0, top_p=1.0, max_tokens=args.max_tokens)
        print(f"[shard] model loaded in {time.time()-t0:.0f}s "
              f"(tp={args.tensor_parallel}, quant={args.quantization})", flush=True)

        def chat(convs: list[list[dict]]) -> list[str]:
            try:
                outs = llm.chat(convs, sampling,
                                chat_template_kwargs={"enable_thinking": False},
                                use_tqdm=False)
            except TypeError:
                outs = llm.chat(convs, sampling, use_tqdm=False)
            return [o.outputs[0].text for o in outs]
    else:
        api_key = os.environ.get(args.openrouter_api_key_env, "")
        if not api_key:
            raise RuntimeError(
                f"{args.openrouter_api_key_env} is required for --backend openrouter"
            )
        print(f"[shard] using OpenRouter model={args.openrouter_model}", flush=True)

        def chat(convs: list[list[dict]]) -> list[str]:
            return openrouter_chat(
                convs,
                model=args.openrouter_model,
                api_key=api_key,
                base_url=args.openrouter_base_url,
                max_tokens=args.max_tokens,
            )

    # --- stream in batches; checkpoint after each ---
    n_done = 0
    t_gen = time.time()
    with open(out_path, "a") as out_fh:
        for bstart in range(0, len(todo), args.batch_profiles):
            batch = todo[bstart : bstart + args.batch_profiles]
            convs, idx = [], []
            for uid in batch:
                prof = profiles[uid]
                for chunk in chunk_list:
                    convs.append([{"role": "user", "content": build_amazon_prompt(prof, chunk)}])
                    idx.append((uid, chunk))
            outs = chat(convs)
            merged: dict[str, list] = {uid: [] for uid in batch}
            for (uid, chunk), text in zip(idx, outs):
                merged[uid].extend(
                    sanitize_fields(parse_fields(text), chunk, profiles[uid])
                )
            for uid in batch:
                out_fh.write(json.dumps(
                    {"user_id": uid, "user_bucket": bucket,
                     "review_count": int(review_count.get(uid, 0)),
                     "fields": merged[uid]}, ensure_ascii=False) + "\n")
            out_fh.flush()
            os.fsync(out_fh.fileno())
            n_done += len(batch)
            rate = n_done / max(1e-9, time.time() - t_gen)
            eta = (len(todo) - n_done) / max(1e-9, rate)
            print(f"[shard {args.shard_id}] {n_done}/{len(todo)} "
                  f"({100*n_done/len(todo):.1f}%)  {rate:.2f} user/s  "
                  f"ETA {eta/3600:.1f}h", flush=True)

    print(f"[shard {args.shard_id}] DONE {n_done} users in "
          f"{(time.time()-t_gen)/3600:.2f}h -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
