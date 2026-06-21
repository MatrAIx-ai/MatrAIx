#!/usr/bin/env python3
"""
Convert existing persona datasets to individual YAML files.

This script processes multiple persona datasets and converts each person-level row
into a standalone YAML file with naming format: DatasetName_IDXXXX.yaml

Datasets supported:
- Nemotron Personas USA (nemotron_sample_100.jsonl)
- Tencent PersonaHub Elite (personahub_elite_persona_sample_100.jsonl)
- OASIS (oasis_sample_100.json)
- Apple ML-PRIMEX (primex_sample_100.csv)

Output: personas/existing_data_curation/curated_personas/
"""

import json
import yaml
import csv
import os
from pathlib import Path
from typing import Dict, List, Any
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Base paths
RAW_DATA_DIR = Path(__file__).parent.parent / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "curated_personas"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

def process_nemotron():
    """Process NVIDIA Nemotron Personas USA dataset."""
    dataset_name = "Nemotron"
    source_file = RAW_DATA_DIR / "nemotron_personas_usa" / "nemotron_sample_100.jsonl"

    if not source_file.exists():
        logger.warning(f"Nemotron file not found: {source_file}")
        return 0

    count = 0
    with open(source_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())

                # Use UUID as ID, or fallback to line number
                person_id = data.get('uuid', f'{line_num:04d}')[:8].upper()
                filename = f"{dataset_name}_{person_id}.yaml"

                # Structure the data
                persona_data = {
                    'id': person_id,
                    'source': dataset_name,
                    'source_file': 'nemotron_sample_100.jsonl',
                    'demographics': {
                        'age': data.get('age'),
                        'gender': data.get('sex'),
                        'marital_status': data.get('marital_status'),
                        'education_level': data.get('education_level'),
                        'occupation': data.get('occupation'),
                        'location': {
                            'city': data.get('city'),
                            'state': data.get('state'),
                            'country': data.get('country'),
                            'zipcode': data.get('zipcode'),
                        }
                    },
                    'personas': {
                        'professional': data.get('professional_persona'),
                        'sports': data.get('sports_persona'),
                        'arts': data.get('arts_persona'),
                        'travel': data.get('travel_persona'),
                        'culinary': data.get('culinary_persona'),
                        'core': data.get('persona'),
                    },
                    'background': {
                        'cultural': data.get('cultural_background'),
                    },
                    'attributes': {
                        'skills': data.get('skills_and_expertise_list'),
                        'hobbies': data.get('hobbies_and_interests_list'),
                        'career_goals': data.get('career_goals_and_ambitions'),
                    },
                    'raw_fields': list(data.keys()),
                }

                # Write YAML
                with open(OUTPUT_DIR / filename, 'w') as out:
                    yaml.dump(persona_data, out, default_flow_style=False, sort_keys=False, allow_unicode=True)

                logger.info(f"✓ {filename}")
                count += 1

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing line {line_num}: {e}")

    return count

def process_personahub():
    """Process Tencent PersonaHub Elite dataset."""
    dataset_name = "PersonaHub"
    source_file = RAW_DATA_DIR / "tencent_personahub" / "personahub_elite_persona_sample_100.jsonl"

    if not source_file.exists():
        logger.warning(f"PersonaHub file not found: {source_file}")
        return 0

    count = 0
    with open(source_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                data = json.loads(line.strip())

                person_id = f'{line_num:04d}'
                filename = f"{dataset_name}_{person_id}.yaml"

                # Structure the data
                persona_data = {
                    'id': person_id,
                    'source': dataset_name,
                    'source_file': 'personahub_elite_persona_sample_100.jsonl',
                    'persona_description': data.get('persona'),
                    'expertise': {
                        'general_domain_top1pct': data.get('general domain (top 1 percent)'),
                        'specific_domain_top1pct': data.get('specific domain (top 1 percent)'),
                        'general_domain_top01pct': data.get('general domain (top 0.1 percent)'),
                        'specific_domain_top01pct': data.get('specific domain (top 0.1 percent)'),
                    },
                    'raw_fields': list(data.keys()),
                }

                # Write YAML
                with open(OUTPUT_DIR / filename, 'w') as out:
                    yaml.dump(persona_data, out, default_flow_style=False, sort_keys=False, allow_unicode=True)

                logger.info(f"✓ {filename}")
                count += 1

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error on line {line_num}: {e}")
            except Exception as e:
                logger.error(f"Error processing line {line_num}: {e}")

    return count

def process_oasis():
    """Process OASIS Reddit user data."""
    dataset_name = "OASIS"
    source_file = RAW_DATA_DIR / "oasis" / "oasis_sample_100.json"

    if not source_file.exists():
        logger.warning(f"OASIS file not found: {source_file}")
        return 0

    count = 0
    try:
        with open(source_file, 'r') as f:
            data = json.load(f)

        # Check if it's a list or dict
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Could be nested, try 'data' or 'users' key
            items = data.get('data', data.get('users', [data]))
        else:
            items = [data]

        for idx, person in enumerate(items, 1):
            try:
                # Extract user ID or use index
                user_id = person.get('user_id', person.get('id', f'{idx:04d}'))
                if isinstance(user_id, (int, float)):
                    person_id = f'{user_id:04d}'
                else:
                    person_id = str(user_id)[:8].upper()

                filename = f"{dataset_name}_{person_id}.yaml"

                # Structure the data
                persona_data = {
                    'id': person_id,
                    'source': dataset_name,
                    'source_file': 'oasis_sample_100.json',
                    'user_data': person,
                    'raw_fields': list(person.keys()) if isinstance(person, dict) else [],
                }

                # Write YAML
                with open(OUTPUT_DIR / filename, 'w') as out:
                    yaml.dump(persona_data, out, default_flow_style=False, sort_keys=False, allow_unicode=True)

                logger.info(f"✓ {filename}")
                count += 1

            except Exception as e:
                logger.error(f"Error processing OASIS record {idx}: {e}")

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in OASIS file: {e}")
    except Exception as e:
        logger.error(f"Error processing OASIS file: {e}")

    return count

def process_primex():
    """Process Apple ML-PRIMEX dataset."""
    dataset_name = "PRIMEX"
    source_file = RAW_DATA_DIR / "apple_ml_primex" / "primex_sample_100.csv"

    if not source_file.exists():
        logger.warning(f"PRIMEX file not found: {source_file}")
        return 0

    count = 0
    try:
        with open(source_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                try:
                    # Use Identity column as ID
                    person_id = row.get('Identity', f'{row_num:04d}')
                    if isinstance(person_id, str):
                        person_id = person_id.replace('_', '').replace('-', '')[:8].upper()

                    filename = f"{dataset_name}_{person_id}.yaml"

                    # Structure the data
                    # Group columns by category
                    hobbies = {}
                    timing = {}
                    beliefs = {}
                    other = {}

                    for key, value in row.items():
                        if 'Hobbies' in key:
                            hobbies[key] = value
                        elif 'Timing' in key:
                            timing[key] = value
                        elif any(belief in key for belief in ['believes', 'world', 'safety', 'boring', 'dangerous']):
                            beliefs[key] = value
                        else:
                            other[key] = value

                    persona_data = {
                        'id': person_id,
                        'source': dataset_name,
                        'source_file': 'primex_sample_100.csv',
                        'demographics': {
                            'age': other.get('Age'),
                            'gender': other.get('Gender'),
                            'education': other.get('Education'),
                            'employment': other.get('Employment'),
                            'political_party': other.get('political party'),
                            'religion': other.get('Religion - Selected Choice'),
                            'location': {
                                'countries': other.get('List of Countries'),
                            }
                        },
                        'hobbies': hobbies if hobbies else None,
                        'beliefs_worldview': beliefs if beliefs else None,
                        'survey_responses': other,
                        'raw_fields': list(row.keys()),
                    }

                    # Remove None values
                    if not hobbies:
                        del persona_data['hobbies']
                    if not beliefs:
                        del persona_data['beliefs_worldview']

                    # Write YAML
                    with open(OUTPUT_DIR / filename, 'w') as out:
                        yaml.dump(persona_data, out, default_flow_style=False, sort_keys=False, allow_unicode=True)

                    logger.info(f"✓ {filename}")
                    count += 1

                except Exception as e:
                    logger.error(f"Error processing PRIMEX row {row_num}: {e}")

    except Exception as e:
        logger.error(f"Error processing PRIMEX file: {e}")

    return count

def main():
    """Process all datasets."""
    logger.info(f"Output directory: {OUTPUT_DIR}\n")

    total = 0

    logger.info("Processing Nemotron Personas USA...")
    total += process_nemotron()
    logger.info("")

    logger.info("Processing Tencent PersonaHub Elite...")
    total += process_personahub()
    logger.info("")

    logger.info("Processing OASIS...")
    total += process_oasis()
    logger.info("")

    logger.info("Processing Apple ML-PRIMEX...")
    total += process_primex()
    logger.info("")

    logger.info(f"✓ Conversion complete! Created {total} YAML files in {OUTPUT_DIR}")

    # List files
    yaml_files = list(OUTPUT_DIR.glob("*.yaml"))
    logger.info(f"\nCreated files ({len(yaml_files)} total):")
    for f in sorted(yaml_files)[:10]:
        logger.info(f"  - {f.name}")
    if len(yaml_files) > 10:
        logger.info(f"  ... and {len(yaml_files) - 10} more")

if __name__ == "__main__":
    main()
