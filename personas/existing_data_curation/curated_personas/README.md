# Curated Personas from Existing Datasets

**Status**: ✅ Complete (336 personas converted)

This directory contains individual YAML files for personas extracted from four major external datasets, organized with the naming format: `DatasetName_IDXXXX.yaml`

---

## Overview

| Dataset | Count | Source | Format | Naming |
|---------|-------|--------|--------|--------|
| **Nemotron** | 100 | NVIDIA Nemotron Personas USA | JSONL | `Nemotron_XXXXXXXX.yaml` (UUID-based) |
| **PersonaHub** | 100 | Tencent PersonaHub Elite | JSONL | `PersonaHub_XXXX.yaml` (sequence) |
| **OASIS** | 36 | OASIS Reddit User Data | JSON | `OASIS_XXXX.yaml` (sequence) |
| **PRIMEX** | 100 | Apple ML-PRIMEX | CSV | `PRIMEX_XXXXXXXX.yaml` (identity-based) |
| **TOTAL** | **336** | | | |

---

## Dataset Descriptions

### Nemotron Personas USA (100 personas)

**Source**: `raw/nemotron_personas_usa/nemotron_sample_100.jsonl`

Rich, multi-faceted personas with domain-specific attributes:

- **Demographics**: Age, gender, marital status, education, occupation, location
- **Personas**: Professional, sports, arts, travel, culinary, core persona descriptions
- **Background**: Cultural background and heritage
- **Attributes**: Skills, hobbies, career goals

**File structure example**:
```yaml
id: E7C05746
source: Nemotron
demographics:
  age: 28
  gender: Female
  occupation: fast_food_or_counter_worker
  location:
    city: Madison
    state: WI
personas:
  professional: "Mary Alberti is a front‑line food service specialist..."
  sports: "Mary Alberti fuels their fitness routine..."
  arts: "Mary Alberti finds creative inspiration..."
attributes:
  skills: [POS system operation, Cash handling, ...]
  hobbies: [Bullet journaling, Home cooking, ...]
```

---

### Tencent PersonaHub Elite (100 personas)

**Source**: `raw/tencent_personahub/personahub_elite_persona_sample_100.jsonl`

Expertise-focused personas extracted from domain knowledge:

- **Persona Description**: Free-form persona text
- **Expertise**: General and specific domains at 1% and 0.1% levels
  - Examples: Computer Science → Embedded Systems, Zoology → Animal Behavior

**File structure example**:
```yaml
id: '0001'
source: PersonaHub
persona_description: "A software developer who is looking for a way to simplify..."
expertise:
  general_domain_top1pct: Computer Science
  specific_domain_top1pct: Embedded Systems
  general_domain_top01pct: null
  specific_domain_top01pct: null
```

---

### OASIS Reddit User Data (36 personas)

**Source**: `raw/oasis/oasis_sample_100.json`

Reddit user profiles with varying field coverage:

- **User Data**: All fields from Reddit user objects
- **Fields vary by user** (common: username, karma, subreddit subscriptions, etc.)

**File structure example**:
```yaml
id: '0001'
source: OASIS
source_file: oasis_sample_100.json
user_data:
  username: "example_user"
  karma: 15000
  # ... other Reddit fields ...
```

---

### Apple ML-PRIMEX (100 personas)

**Source**: `raw/apple_ml_primex/primex_sample_100.csv`

Survey responses from diverse population on worldviews, beliefs, and values:

- **Demographics**: Age, gender, education, employment, political affiliation, religion
- **Hobbies**: Cultural events, exercise, gardening, video games, reading, cooking, etc.
- **Beliefs & Worldview**: Primal World Beliefs questionnaire responses
- **Survey Responses**: Opinions on technology, environment, equality, future scenarios

**File structure example**:
```yaml
id: R5SOPK4O
source: PRIMEX
source_file: primex_sample_100.csv
demographics:
  age: 30 to 39
  gender: Female
  education: Undergraduate degree
  employment: Working full-time
  political_party: Democrat
hobbies:
  Hobbies - Cultural events: Yes
  Hobbies - Exercising: Yes
  Hobbies - Reading: Yes
beliefs_worldview:
  # Primal World Beliefs responses...
survey_responses:
  # All other survey fields...
```

---

## File Organization

```
curated_personas/
├── README.md
├── Nemotron_01B0D4D4.yaml      # 100 Nemotron personas
├── Nemotron_078955AD.yaml
├── ... (100 total)
├── PersonaHub_0001.yaml         # 100 PersonaHub personas
├── PersonaHub_0002.yaml
├── ... (100 total)
├── OASIS_0001.yaml              # 36 OASIS personas
├── OASIS_0002.yaml
├── ... (36 total)
├── PRIMEX_R5SOPK4O.yaml         # 100 PRIMEX personas
├── PRIMEX_R3IX2VSO.yaml
├── ... (100 total)
```

---

## Naming Convention

All files follow the pattern: `DatasetName_IDXXXX.yaml`

| Dataset | ID Format | Example |
|---------|-----------|---------|
| Nemotron | First 8 chars of UUID | `Nemotron_E7C05746.yaml` |
| PersonaHub | Zero-padded sequence (0001-0100) | `PersonaHub_0050.yaml` |
| OASIS | Zero-padded sequence (0001-0036) | `OASIS_0012.yaml` |
| PRIMEX | Identity field (cleaned) | `PRIMEX_R5SOPK4O.yaml` |

---

## How to Use

### Load a Single Persona

```python
import yaml

with open('curated_personas/Nemotron_E7C05746.yaml', 'r') as f:
    persona = yaml.safe_load(f)

print(f"Name: {persona['demographics']['location']['city']}")
print(f"Occupation: {persona['demographics']['occupation']}")
print(f"Professional persona: {persona['personas']['professional']}")
```

### Load All Personas from a Dataset

```python
import yaml
from pathlib import Path

persona_dir = Path('curated_personas')

# Load all Nemotron personas
nemotron_personas = {}
for file in persona_dir.glob('Nemotron_*.yaml'):
    with open(file, 'r') as f:
        persona = yaml.safe_load(f)
        nemotron_personas[persona['id']] = persona

print(f"Loaded {len(nemotron_personas)} Nemotron personas")
```

### Filter Personas by Attribute

```python
# Find all 28-year-old females
young_females = [
    (f.stem, persona)
    for f in persona_dir.glob('Nemotron_*.yaml')
    if (persona := yaml.safe_load(open(f))).get('demographics', {}).get('age') == 28
    and persona.get('demographics', {}).get('gender') == 'Female'
]
```

---

## Data Quality & Coverage

### Nemotron
- ✅ Complete demographics for all 100 personas
- ✅ Rich narrative personas across 6 dimensions
- ✅ Skills and hobbies lists provided

### PersonaHub
- ✅ All 100 personas have descriptions and domain expertise
- ⚠️  Limited to expertise domain (not broader demographics)

### OASIS
- ✅ 36 valid personas extracted
- ⚠️  Field coverage varies by user (some sparse, some rich)
- ⚠️  No demographics; Reddit fields only

### PRIMEX
- ✅ All 100 personas have complete survey responses
- ✅ Rich worldview and belief data
- ⚠️  Sampling bias from online survey methodology

---

## Next Steps

### Integration with MatrAIx Schema

To integrate these personas with `personas/dimensions+new.json`:

1. **Extract key dimensions** from each dataset
2. **Map to existing dimensions** in the schema
3. **Handle missing fields** with defaults or inference
4. **Validate consistency** across datasets

### Scaling

To extend beyond 336 personas:

1. **Fetch full datasets** (currently using samples):
   - Nemotron: 11 shards available
   - PersonaHub Elite: 300GB+ available
   - OASIS: Full Reddit dataset available
   - PRIMEX: Full survey respondents

2. **Add additional datasets** from README.md sources:
   - Google Synthetic-Persona-Chat
   - Facebook PersonaChat
   - HorizonBench
   - WildChat-1M

3. **Develop deduplication** across datasets

---

## Technical Details

### Conversion Script

**Script**: `scripts/convert_to_yaml.py`

The conversion script:
- Reads from raw sample files
- Structures data logically (demographics, personas, attributes, beliefs)
- Handles format-specific quirks (JSONL, JSON, CSV)
- Generates YAML with human-readable formatting
- Preserves all original fields in `raw_fields` list

### YAML Structure

All files follow a consistent structure for easy parsing:

```yaml
id: <dataset-specific-id>
source: <DatasetName>
source_file: <original-filename>

# Dataset-specific fields follow
# (demographics, personas, expertise, beliefs, etc.)

raw_fields: [list of original field names]
```

---

## Statistics

- **Total personas**: 336
- **Total YAML files**: 336
- **Total directory size**: ~3.1 MB
- **Average file size**: ~9.2 KB
- **Conversion time**: <1 second

---

## References

- Original datasets: See `README.md` in parent directory
- Conversion script: `scripts/convert_to_yaml.py`
- Dimensions schema: `../../dimensions+new.json`
- Raw data: `../raw/`

---

**Last updated**: 2026-06-21  
**Format version**: 1.0  
**Conversion tool**: Python 3.x + PyYAML
