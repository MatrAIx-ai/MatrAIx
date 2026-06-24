# Dimensions Additions Summary (2026-06-20)

## Overview

Added **34 new persona dimensions** from three recently integrated external datasets to `dimensions+new.json`:

- **PersonaChat** (Facebook): 1 dimension
- **HorizonBench** (Long-Horizon Personalization): 30 dimensions
- **WildChat** (AllenAI): 3 dimensions

**Total dimensions updated:** 1,282 → **1,316**

---

## Dataset Details

### 1. Facebook PersonaChat (arXiv:1801.07243)

**Source:** `facebook/persona-chat` (HuggingFace)  
**License:** CC-BY-4.0  
**Dimensions Added:** 1

| ID | Label | Column Name | Description |
|---|---|---|---|
| `personachat_persona` | PersonaChat_PersonaDescription | `persona` | Free-text persona profile sentences describing interests, habits, and traits |

**Key Facts:**
- 1,155 crowd-sourced personas with 4–5 profile sentences each
- 10,907 dialogues with 162K+ utterances
- Foundational early work in persona-grounded dialogue
- Manifest: `personas/existing_data_curation/manifests/personachat_facebook.json`

---

### 2. HorizonBench mental_state_graphs (arXiv:2604.17283, April 2026)

**Source:** `stellalisy/HorizonBench` (HuggingFace, config: `mental_state_graphs`)  
**License:** CC-BY-4.0  
**Dimensions Added:** 30

**All 30 Preference Evolution Domains:**

| # | Label | Column Name |
|---|---|---|
| 1 | HorizonBench_Advice_Delivery_Preferences | `advice_delivery_preferences` |
| 2 | HorizonBench_Analytical_Approach | `analytical_approach` |
| 3 | HorizonBench_Apology_Style_Preferences | `apology_style_preferences` |
| 4 | HorizonBench_Communication_Intimacy | `communication_intimacy` |
| 5 | HorizonBench_Communication_Medium_Preferences | `communication_medium_preferences` |
| 6 | HorizonBench_Conflict_Resolution_Style_Preferences | `conflict_resolution_style_preferences` |
| 7 | HorizonBench_Content_Length_Preferences | `content_length_preferences` |
| 8 | HorizonBench_Creative_Collaboration | `creative_collaboration` |
| 9 | HorizonBench_Emotional_Support_Style | `emotional_support_style` |
| 10 | HorizonBench_Empirical_Evidence_Integration_Preferences | `empirical_evidence_integration_preferences` |
| 11 | HorizonBench_Entertainment_Preferences | `entertainment_preferences` |
| 12 | HorizonBench_Ethical_Review_Preferences | `ethical_review_preferences` |
| 13 | HorizonBench_Event_Planning_Detail_Preferences | `event_planning_detail_preferences` |
| 14 | HorizonBench_Facilitation_Style_Preferences | `facilitation_style_preferences` |
| 15 | HorizonBench_Follow_Up_Strategy_Preferences | `follow_up_strategy_preferences` |
| 16 | HorizonBench_Interfaith_Engagement_Preferences | `interfaith_engagement_preferences` |
| 17 | HorizonBench_Intergenerational_Engagement_Preferences | `intergenerational_engagement_preferences` |
| 18 | HorizonBench_Language_Preferences | `language_preferences` |
| 19 | HorizonBench_Motivation_Strategy_Preferences | `motivation_strategy_preferences` |
| 20 | HorizonBench_Philosophical_Engagement | `philosophical_engagement` |
| 21 | HorizonBench_Productivity_Style | `productivity_style` |
| 22 | HorizonBench_Public_Speaking_Coaching_Preferences | `public_speaking_coaching_preferences` |
| 23 | HorizonBench_Self_Esteem_Rebuilding_Preferences | `self_esteem_rebuilding_preferences` |
| 24 | HorizonBench_Social_Engagement_Style_Preferences | `social_engagement_style_preferences` |
| 25 | HorizonBench_Stakeholder_Consultation_Preferences | `stakeholder_consultation_preferences` |
| 26 | HorizonBench_Support_Technique_Preferences | `support_technique_preferences` |
| 27 | HorizonBench_Technology_Assistance_Style_Preferences | `technology_assistance_style_preferences` |
| 28 | HorizonBench_Therapy_Discussion_Preferences | `therapy_discussion_preferences` |
| 29 | HorizonBench_Tone_Guideline_Preferences | `tone_guideline_preferences` |
| 30 | HorizonBench_Writing_Style_Preferences | `writing_style_preferences` |

**Key Facts:**
- 360 user timelines with structured mental state graphs
- 6-month evolution horizon with preference tracking
- 1.6M conversation turns across 3 frontier LLMs (Claude-Sonnet-4.5, o3, Gemini-3-flash)
- Additional demographics in user_profile: ethnicity, occupation, location
- Manifest: `personas/existing_data_curation/manifests/horizonbench_mental_state_graphs.json`

---

### 3. AllenAI WildChat-1M (arXiv:2405.01470)

**Source:** `allenai/WildChat-1M` (HuggingFace)  
**License:** ODC-BY (Open Data Commons Attribution)  
**Dimensions Added:** 3

| ID | Label | Column Name | Description |
|---|---|---|---|
| `wildchat_state` | WildChat_State | `state` | U.S. state where user accessed WildChat (IP geolocation) |
| `wildchat_country` | WildChat_Country | `country` | Country where user accessed WildChat (IP geolocation) |
| `wildchat_hashed_ip` | WildChat_HashedIP | `hashed_ip` | Privacy-preserving hashed IP address |

**Key Facts:**
- 838K non-toxic conversations from 204K+ unique contributors
- **Privacy-first design:** Intentionally excludes traditional demographics (age, gender, education, occupation)
- Only geographic and technical dimensions available
- Manifest: `personas/existing_data_curation/manifests/wildchat_allenai.json`

---

## Source Traceability

Each dimension includes comprehensive `source_origin` metadata for deduplication:

```json
"source_origin": {
  "source_id": "horizonbench_mental_state_graphs",
  "source_name": "HorizonBench (mental_state_graphs)",
  "source_type": "huggingface_dataset",
  "huggingface_repo": "stellalisy/HorizonBench",
  "huggingface_url": "https://huggingface.co/datasets/stellalisy/HorizonBench",
  "paper_url": "https://arxiv.org/abs/2604.17283",
  "manifest_file": "personas/existing_data_curation/manifests/horizonbench_mental_state_graphs.json",
  "fetch_script": "personas/existing_data_curation/scripts/fetch_sources.py",
  "config": "mental_state_graphs",
  "column_name": "advice_delivery_preferences",
  "license": "cc-by-4.0",
  "added_date": "2026-06-20"
}
```

This enables:
1. **Deduplication:** Find dimensions across sources sharing similar names/concepts
2. **Validation:** Trace back to original data source and fetch script
3. **Attribution:** Link to papers, licenses, and dataset repositories
4. **Audit Trail:** Track when each dimension was added

---

## File Changes

| File | Change | Details |
|---|---|---|
| `dimensions+new.json` | Updated | 1,282 → 1,316 dimensions, targetDimensions field updated |
| `personas/existing_data_curation/manifests/personachat_facebook.json` | Created | Manifest for PersonaChat |
| `personas/existing_data_curation/manifests/horizonbench_mental_state_graphs.json` | Created | Manifest for HorizonBench |
| `personas/existing_data_curation/manifests/wildchat_allenai.json` | Created | Manifest for WildChat |
| `personas/existing_data_curation/README.md` | Updated | Added 3 new sources to Sources table (10 total) |
| `personas/existing_data_curation/scripts/fetch_sources.py` | Updated | Added fetch functions for all 3 datasets |

---

## Fetching Data

To download samples or full datasets:

```bash
cd personas/existing_data_curation

# Sample mode (first 1000 rows per source)
python scripts/fetch_sources.py --source all --mode sample

# Specific datasets
python scripts/fetch_sources.py --source personachat --mode sample --sample-rows 500
python scripts/fetch_sources.py --source horizonbench --mode full
python scripts/fetch_sources.py --source wildchat --mode full
```

Downloaded data lands in `raw/` (git-ignored).

---

## Next Steps

1. **Deduplication Analysis:** Use source_origin metadata to identify duplicate/overlapping dimensions across 10 sources (114+ total dimensions)
2. **Dimension Consolidation:** Merge redundant dimensions, select canonical names
3. **Value Enumeration:** Extract actual values from each dimension (currently all marked "Unknown")
4. **Integration Testing:** Validate dimensions work with persona generation pipeline

---

## Verification

**JSON Validity:** ✅ All JSON syntax valid  
**targetDimensions:** ✅ Updated to 1,316  
**Source Traceability:** ✅ All dimensions linked to papers, manifests, scripts  
**Licenses:** ✅ CC-BY-4.0 (PersonaChat, HorizonBench) and ODC-BY (WildChat)
