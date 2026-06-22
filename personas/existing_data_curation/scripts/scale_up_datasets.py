#!/usr/bin/env python3
"""
Scale up persona dataset conversion from samples to full datasets.

This script:
1. Downloads full datasets from Hugging Face (streamed to avoid memory issues)
2. Converts to individual YAML files with DatasetName_IDXXXX format
3. Handles large-scale data efficiently (1M+ personas)
4. Shows progress and statistics

Usage:
    python scale_up_datasets.py --datasets all
    python scale_up_datasets.py --datasets nemotron --max 100000
    python scale_up_datasets.py --datasets personahub --batch-size 1000
"""

import json
import yaml
import csv
import os
from pathlib import Path
from typing import Dict, List, Any, Generator, Optional
import logging
import argparse
from tqdm import tqdm
import sys

# Try to import Hugging Face datasets
try:
    from datasets import load_dataset
    HAS_HF = True
except ImportError:
    HAS_HF = False
    print("Warning: datasets library not installed. Install with: pip install datasets")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scale_up.log')
    ]
)
logger = logging.getLogger(__name__)

# Base paths
RAW_DATA_DIR = Path(__file__).parent.parent / "raw"
OUTPUT_DIR = Path(__file__).parent.parent / "curated_personas"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

class DatasetProcessor:
    """Base class for dataset processing."""

    def __init__(self, dataset_name: str, max_records: Optional[int] = None):
        self.dataset_name = dataset_name
        self.max_records = max_records
        self.count = 0

    def process(self) -> int:
        """Process dataset and return count of personas created."""
        raise NotImplementedError

    def write_persona_yaml(self, person_id: str, persona_data: Dict[str, Any]) -> bool:
        """Write a single persona to YAML file."""
        try:
            filename = f"{self.dataset_name}_{person_id}.yaml"
            filepath = OUTPUT_DIR / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(
                    persona_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,
                    width=200  # Longer lines for persona descriptions
                )
            return True
        except Exception as e:
            logger.error(f"Error writing {filename}: {e}")
            return False

class NemotronProcessor(DatasetProcessor):
    """Process NVIDIA Nemotron Personas USA (1M personas, 11 parquet shards)."""

    def __init__(self, max_records: Optional[int] = None):
        super().__init__("Nemotron", max_records)
        self.repo_id = "nvidia/Nemotron-Personas-USA"

    def process(self) -> int:
        """Download and process Nemotron dataset."""
        if not HAS_HF:
            logger.error("Hugging Face datasets library required for Nemotron")
            return 0

        logger.info(f"Loading Nemotron dataset (1M personas, 11 shards)...")
        logger.info(f"Max records: {self.max_records if self.max_records else 'all'}")

        try:
            # Stream the dataset to avoid loading everything into memory
            dataset = load_dataset(self.repo_id, split='train', streaming=True)

            pbar = tqdm(dataset, total=self.max_records, desc="Nemotron")

            for record in pbar:
                if self.max_records and self.count >= self.max_records:
                    break

                try:
                    person_id = record.get('uuid', f'{self.count:08d}')[:8].upper()

                    # Structure the data consistently
                    persona_data = {
                        'id': person_id,
                        'source': 'Nemotron',
                        'source_file': 'nemotron_personas_usa (streaming)',
                        'record_index': self.count,
                        'demographics': {
                            'age': record.get('age'),
                            'gender': record.get('sex'),
                            'marital_status': record.get('marital_status'),
                            'education_level': record.get('education_level'),
                            'occupation': record.get('occupation'),
                            'location': {
                                'city': record.get('city'),
                                'state': record.get('state'),
                                'country': record.get('country'),
                                'zipcode': record.get('zipcode'),
                            }
                        },
                        'personas': {
                            'professional': record.get('professional_persona'),
                            'sports': record.get('sports_persona'),
                            'arts': record.get('arts_persona'),
                            'travel': record.get('travel_persona'),
                            'culinary': record.get('culinary_persona'),
                            'core': record.get('persona'),
                        },
                        'background': {
                            'cultural': record.get('cultural_background'),
                        },
                        'attributes': {
                            'skills': record.get('skills_and_expertise_list'),
                            'hobbies': record.get('hobbies_and_interests_list'),
                            'career_goals': record.get('career_goals_and_ambitions'),
                        },
                    }

                    if self.write_persona_yaml(person_id, persona_data):
                        self.count += 1

                    pbar.update(1)

                except Exception as e:
                    logger.error(f"Error processing Nemotron record {self.count}: {e}")
                    continue

            logger.info(f"✓ Processed {self.count} Nemotron personas")
            return self.count

        except Exception as e:
            logger.error(f"Error loading Nemotron dataset: {e}")
            return 0

class PersonaHubProcessor(DatasetProcessor):
    """Process Tencent PersonaHub Elite (2 personas claimed, but actually much larger)."""

    def __init__(self, max_records: Optional[int] = None):
        super().__init__("PersonaHub", max_records)
        self.repo_id = "proj-persona/PersonaHub"

    def process(self) -> int:
        """Download and process PersonaHub dataset."""
        if not HAS_HF:
            logger.error("Hugging Face datasets library required for PersonaHub")
            return 0

        logger.info(f"Loading PersonaHub dataset...")
        logger.info(f"Max records: {self.max_records if self.max_records else 'all'}")

        try:
            # Try elite_persona config first
            dataset = load_dataset(self.repo_id, 'elite_persona', split='train', streaming=True)

            pbar = tqdm(dataset, total=self.max_records, desc="PersonaHub")

            for record in pbar:
                if self.max_records and self.count >= self.max_records:
                    break

                try:
                    person_id = f'{self.count:08d}'

                    persona_data = {
                        'id': person_id,
                        'source': 'PersonaHub',
                        'source_file': 'personahub_elite_persona (streaming)',
                        'record_index': self.count,
                        'persona_description': record.get('persona'),
                        'expertise': {
                            'general_domain_top1pct': record.get('general domain (top 1 percent)'),
                            'specific_domain_top1pct': record.get('specific domain (top 1 percent)'),
                            'general_domain_top01pct': record.get('general domain (top 0.1 percent)'),
                            'specific_domain_top01pct': record.get('specific domain (top 0.1 percent)'),
                        },
                        'raw_fields': list(record.keys()),
                    }

                    if self.write_persona_yaml(person_id, persona_data):
                        self.count += 1

                    pbar.update(1)

                except Exception as e:
                    logger.error(f"Error processing PersonaHub record {self.count}: {e}")
                    continue

            logger.info(f"✓ Processed {self.count} PersonaHub personas")
            return self.count

        except Exception as e:
            logger.error(f"Error loading PersonaHub dataset: {e}")
            return 0

class SyntheticPersonaChatProcessor(DatasetProcessor):
    """Process Google Synthetic-Persona-Chat dataset."""

    def __init__(self, max_records: Optional[int] = None):
        super().__init__("SyntheticPersonaChat", max_records)
        self.repo_id = "google/Synthetic-Persona-Chat"

    def process(self) -> int:
        """Download and process Synthetic-Persona-Chat dataset."""
        if not HAS_HF:
            logger.error("Hugging Face datasets library required")
            return 0

        logger.info(f"Loading Synthetic-Persona-Chat dataset...")

        try:
            # This dataset has multiple CSV files
            dataset = load_dataset(self.repo_id, split='train', streaming=True)

            pbar = tqdm(dataset, total=self.max_records, desc="SyntheticPersonaChat")

            for record in pbar:
                if self.max_records and self.count >= self.max_records:
                    break

                try:
                    person_id = f'{self.count:08d}'

                    persona_data = {
                        'id': person_id,
                        'source': 'SyntheticPersonaChat',
                        'source_file': 'google_synthetic_persona_chat (streaming)',
                        'record_index': self.count,
                        'data': record,
                        'raw_fields': list(record.keys()),
                    }

                    if self.write_persona_yaml(person_id, persona_data):
                        self.count += 1

                    pbar.update(1)

                except Exception as e:
                    logger.error(f"Error processing record {self.count}: {e}")
                    continue

            logger.info(f"✓ Processed {self.count} SyntheticPersonaChat personas")
            return self.count

        except Exception as e:
            logger.error(f"Error loading dataset: {e}")
            return 0

def main():
    parser = argparse.ArgumentParser(
        description='Scale up persona dataset conversion from samples to full datasets'
    )
    parser.add_argument(
        '--datasets',
        choices=['all', 'nemotron', 'personahub', 'synthetic', 'wildchat'],
        default='nemotron',
        help='Which datasets to process'
    )
    parser.add_argument(
        '--max',
        type=int,
        default=None,
        help='Maximum records to process (default: all)'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Batch size for processing'
    )

    args = parser.parse_args()

    logger.info("=" * 80)
    logger.info("DATASET SCALE-UP PROCESSOR")
    logger.info("=" * 80)
    logger.info(f"Datasets: {args.datasets}")
    logger.info(f"Max records: {args.max if args.max else 'unlimited'}")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info("=" * 80)

    total_processed = 0

    # Process datasets
    if args.datasets in ['all', 'nemotron']:
        logger.info("\n>>> NEMOTRON (1M personas, 11 shards, ~2.7GB)")
        processor = NemotronProcessor(max_records=args.max)
        total_processed += processor.process()

    if args.datasets in ['all', 'personahub']:
        logger.info("\n>>> PERSONAHUB ELITE (large dataset)")
        processor = PersonaHubProcessor(max_records=args.max or 100000)
        total_processed += processor.process()

    if args.datasets in ['all', 'synthetic']:
        logger.info("\n>>> SYNTHETIC-PERSONA-CHAT (Google)")
        processor = SyntheticPersonaChatProcessor(max_records=args.max or 50000)
        total_processed += processor.process()

    logger.info("\n" + "=" * 80)
    logger.info(f"TOTAL PROCESSED: {total_processed:,} personas")
    logger.info(f"Output directory: {OUTPUT_DIR}")
    logger.info(f"YAML files created: {len(list(OUTPUT_DIR.glob('*.yaml')))}")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
