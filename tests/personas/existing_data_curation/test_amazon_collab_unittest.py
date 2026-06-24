import gzip
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from personas.existing_data_curation.scripts.validate_amazon_results import (
    validate_amazon_archive,
)
from personas.existing_data_curation.wiki_collab.amazon_collab import (
    build_amazon_profile_database,
)
from personas.existing_data_curation.wiki_collab.core import Assignment, load_protocol_manifest
from personas.existing_data_curation.worker_kit.run_amazon_range import (
    parse_args as parse_amazon_runner_args,
    run_amazon_range,
)


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def _sample_user_row() -> dict:
    return {
        "user_id": "u1",
        "temporal_split": {"method": "per_user_temporal", "train_fraction": 0.8},
        "reviews": [
            {
                "review_id": "r1",
                "parent_asin": "B001",
                "category": "Books",
                "title": "Detailed notes",
                "text": "I annotate every chapter and compare translations.",
                "rating": 5,
                "timestamp": 1700000000000,
            }
        ],
        "validation_reviews": [
            {
                "review_id": "v1",
                "parent_asin": "B002",
                "category": "Books",
                "title": "Held out",
                "text": "This should not be used for persona construction.",
                "rating": 4,
                "timestamp": 1710000000000,
            }
        ],
    }


class AmazonCollabTests(unittest.TestCase):
    def test_mock_amazon_range_builds_valid_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            histories = tmp_path / "user_histories.jsonl"
            db = tmp_path / "amazon_profiles.sqlite"
            manifest_path = tmp_path / "dataset_manifest.json"
            schema = tmp_path / "schema.json"
            mapping = tmp_path / "mapping.json"
            out_dir = tmp_path / "runs"
            _write_jsonl(histories, [_sample_user_row()])
            _write_json(
                schema,
                {
                    "dimensions": [
                        {
                            "id": "test_interest",
                            "label": "Test Interest",
                            "category": "Interests",
                            "description": "A test interest dimension.",
                            "values": ["High", "Low"],
                        }
                    ]
                },
            )
            _write_json(
                mapping,
                {
                    "evidence_categories": [
                        {
                            "id": "interests",
                            "label": "Interests",
                            "schema_categories": ["Interests"],
                        }
                    ]
                },
            )
            dataset_manifest = build_amazon_profile_database(
                user_histories=histories,
                out_db=db,
                manifest_path=manifest_path,
                dataset_id="amazon-test-v1",
            )
            protocol_dir = Path(
                "personas/existing_data_curation/protocols/amazon_review_persona_inference_v1"
            )
            protocol = load_protocol_manifest(protocol_dir)
            assignment = Assignment(
                assignment_id="A0001",
                worker_id="alice",
                dataset_id="amazon-test-v1",
                dataset_sha256=dataset_manifest["db_sha256"],
                protocol_id=protocol.protocol_id,
                protocol_sha256=protocol.protocol_sha256,
                range_start=0,
                range_end=1,
            )
            args = parse_amazon_runner_args(
                [
                    "--db",
                    str(db),
                    "--protocol",
                    str(protocol_dir),
                    "--range",
                    "0:1",
                    "--worker-id",
                    "alice",
                    "--out-dir",
                    str(out_dir),
                    "--dataset-id",
                    "amazon-test-v1",
                    "--dataset-sha256",
                    dataset_manifest["db_sha256"],
                    "--backend",
                    "mock",
                    "--schema-path",
                    str(schema),
                    "--evidence-mapping-path",
                    str(mapping),
                    "--dimension-ids",
                    "test_interest",
                ]
            )
            archive = run_amazon_range(
                db_path=db,
                protocol_dir=protocol_dir,
                range_start=0,
                range_end=1,
                worker_id="alice",
                out_dir=out_dir,
                dataset_id="amazon-test-v1",
                dataset_sha256=dataset_manifest["db_sha256"],
                args=args,
            )
            report = validate_amazon_archive(
                archive_path=archive,
                db_path=db,
                assignment=assignment,
                expected_prompt_sha256=protocol.prompt_sha256,
                schema_path=schema,
            )
            with tarfile.open(archive, "r:gz") as tar:
                tar.extract("results.jsonl.gz", path=tmp_path)
            with gzip.open(tmp_path / "results.jsonl.gz", "rt", encoding="utf-8") as fh:
                rows = [json.loads(line) for line in fh]
        self.assertTrue(report.accepted, report.errors)
        self.assertEqual(report.valid_rows, 1)
        self.assertEqual(rows[0]["source_type"], "amazon_reviews_2023")
        self.assertEqual(rows[0]["inferred_attributes"], [])


if __name__ == "__main__":
    unittest.main()
