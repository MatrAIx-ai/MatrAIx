# Scale-Up Guide: Converting Full Datasets to YAML Personas

**Current Status**: 336 personas (samples from 4 datasets)  
**Target**: 1M+ personas from full datasets

---

## Overview

The MatrAIx persona curation pipeline can scale from samples to full datasets using the `scale_up_datasets.py` script. This guide walks through scaling each dataset.

### Dataset Availability

| Dataset | Size | Shards | Format | Status |
|---------|------|--------|--------|--------|
| **Nemotron Personas USA** | 1M | 11 shards | Parquet | Ready to scale |
| **Tencent PersonaHub Elite** | 300GB+ | Multiple | Parquet | Ready to scale |
| **Google Synthetic-Persona-Chat** | ~50K | Multiple CSV | CSV | Ready to scale |
| **OASIS Reddit** | 36 users | 1 JSON | JSON | ✓ Complete (sample only) |
| **Apple ML-PRIMEX** | ~100 | 1 CSV | CSV | ✓ Complete (sample only) |

---

## Quick Start

### 1. Install Dependencies

```bash
pip install datasets tqdm pyyaml
```

### 2. Scale Nemotron (1M personas)

**Full dataset (streamed)**:
```bash
cd /home/yuexing/MatrAIx/personas/existing_data_curation
python scripts/scale_up_datasets.py --datasets nemotron
```

**Subset (first 100K)**:
```bash
python scripts/scale_up_datasets.py --datasets nemotron --max 100000
```

**Estimated time & resources**:
- Full 1M: ~24-48 hours (streaming, no disk cache)
- 100K: ~2-4 hours
- 10K: ~15 minutes
- CPU: Minimal (mostly network I/O)
- Disk: ~2-3 GB for YAML output (depending on quantity)

### 3. Scale PersonaHub (Elite, 300GB+)

```bash
python scripts/scale_up_datasets.py --datasets personahub --max 100000
```

### 4. Scale Google Synthetic-Persona-Chat

```bash
python scripts/scale_up_datasets.py --datasets synthetic --max 50000
```

---

## Detailed Process

### Nemotron (1M personas, 11 shards)

**What's happening**:
1. Dataset loads from Hugging Face Hub via streaming
2. Each record (parquet shard) is processed in order
3. Fields are restructured into consistent YAML format
4. Progress bar shows real-time count
5. Logs saved to `scale_up.log`

**Expected output**:
```
================================================================================
DATASET SCALE-UP PROCESSOR
================================================================================
Datasets: nemotron
Max records: unlimited
Output: /home/yuexing/MatrAIx/personas/existing_data_curation/curated_personas
================================================================================

>>> NEMOTRON (1M personas, 11 shards, ~2.7GB)
Loading Nemotron dataset (1M personas, 11 shards)...
Max records: unlimited
Nemotron: 100%|████| 1000000/1000000 [48:12<00:00, 345.2it/s]
✓ Processed 1,000,000 Nemotron personas

================================================================================
TOTAL PROCESSED: 1,000,000 personas
Output directory: /home/yuexing/MatrAIx/personas/existing_data_curation/curated_personas
YAML files created: 1,000,336
================================================================================
```

**Resulting files**:
- `Nemotron_XXXXXXXX.yaml` × 1,000,000
- Each file ~4-6 KB
- Total directory size: ~4-6 GB

---

## YAML Format Consistency

All output files follow this structure:

```yaml
id: <dataset-specific-id>
source: <DatasetName>
source_file: <streaming-source>
record_index: <0-based-index>

# Dataset-specific fields
demographics:  # (Nemotron)
  age: 28
  gender: Female
  occupation: fast_food_or_counter_worker
  location:
    city: Madison
    state: WI

personas:  # (Nemotron)
  professional: "..."
  sports: "..."
  core: "..."

attributes:  # (Nemotron)
  skills: [...]
  hobbies: [...]
  career_goals: "..."

expertise:  # (PersonaHub)
  general_domain_top1pct: "Computer Science"
  specific_domain_top1pct: "Embedded Systems"

raw_fields: [list of original field names]
```

---

## Streaming Strategy

The script uses **streaming mode** for all datasets:

**Advantages**:
- ✅ No large downloads needed
- ✅ Processes records on-the-fly
- ✅ Works even for 300GB+ datasets
- ✅ Memory efficient (constant usage)

**How it works**:
1. Hugging Face Hub sends records in batches
2. Each batch is converted to YAML
3. File is written immediately (disk streaming)
4. Memory is freed for next batch
5. Process can be paused/resumed (if checkpoint added)

---

## Parallel Processing (Optional Future Enhancement)

To speed up conversion 4-10x, use parallel processing:

```python
# Future enhancement: process multiple shards in parallel
import multiprocessing

with multiprocessing.Pool(4) as pool:
    results = pool.map(process_shard, shard_list)
```

**Trade-off**: Uses 4 CPU cores, still low memory (streaming writes).

---

## Integration with Dimensions Schema

After scaling up, integrate with `personas/dimensions+new.json`:

### Step 1: Extract Key Dimensions

```python
# Extract from Nemotron YAML files
import yaml
from pathlib import Path

dimensions_per_dataset = {}

for yaml_file in Path('curated_personas').glob('Nemotron_*.yaml'):
    with open(yaml_file) as f:
        persona = yaml.safe_load(f)
    
    # Extract demographics as dimensions
    demographics = persona.get('demographics', {})
    for key, value in demographics.items():
        if value:
            dimensions_per_dataset.setdefault(key, []).append(value)
```

### Step 2: Map to Existing Dimensions

```python
# Map Nemotron demographics to schema
mapping = {
    'occupation': 'demo_occupation',
    'age': 'demo_age_decade',
    'gender': 'demo_gender',
    # ... more mappings
}
```

### Step 3: Validate & Merge

```python
# Validate all values fit schema constraints
# Merge with dimensions+new.json
# Update schema if needed
```

---

## Monitoring & Resumption

### Log File

```bash
tail -f scale_up.log
```

Shows:
- Processing speed (records/second)
- HTTP requests to Hugging Face
- Errors (if any)
- Final stats

### Adding Checkpointing (Future)

To enable resumption mid-process:

```python
# Save checkpoint every N records
if self.count % 10000 == 0:
    with open('checkpoint.json', 'w') as f:
        json.dump({
            'dataset': self.dataset_name,
            'last_count': self.count,
            'timestamp': time.time()
        }, f)
```

---

## Running on Schedule

### Option 1: Daily Background Download

```bash
# crontab -e
0 2 * * * cd /path && python scripts/scale_up_datasets.py --datasets all >> scale_up.log 2>&1
```

### Option 2: Docker Container

```dockerfile
FROM python:3.11
RUN pip install datasets tqdm pyyaml
WORKDIR /app
COPY scale_up_datasets.py .
CMD ["python", "scale_up_datasets.py", "--datasets", "all"]
```

### Option 3: Cloud Job (Google Cloud Run, AWS Lambda)

For 1M-persona conversion (~48 hours):
- Estimated cost: $50-200 (depending on resource tier)
- Recommend: CPU-only instance, 2-4 GB RAM

---

## Troubleshooting

### Out of Memory
- Reduce batch size (default: streaming, no batching)
- Add checkpoint/resume feature
- Use a larger machine

### Network Timeouts
- Increase timeout in script
- Use a VPN/proxy closer to Hugging Face servers
- Schedule during off-peak hours

### Disk Full
- Monitor disk usage: `df -h`
- Process in chunks and archive old files
- Consider cloud object storage (S3, GCS)

### Duplicate Files
- Script uses dataset-specific IDs (no collision)
- Safe to re-run (will overwrite with same content)

---

## Architecture for 1M+ Personas

**Current approach** (working):
```
Raw Dataset (HF Hub)
    ↓ (streaming)
scale_up_datasets.py
    ↓
Individual YAML files (Nemotron_XXXXXXXX.yaml × 1M)
    ↓
Integrate with dimensions schema
    ↓
MatrAIx persona database
```

**Recommended next steps**:
1. Run Nemotron full (1M personas) — takes ~2 days
2. Run PersonaHub (100K+ personas)
3. Deduplicate across datasets
4. Map to unified schema
5. Release as benchmark dataset

---

## Reference

- Script: `scripts/scale_up_datasets.py`
- Output: `curated_personas/` (336 now, 1M+ target)
- Datasets: Hugging Face Hub (nvidia/Nemotron-Personas-USA, proj-persona/PersonaHub, etc.)
- Format: YAML (DatasetName_IDXXXX.yaml)

---

**Last updated**: 2026-06-21  
**Status**: Ready to scale
