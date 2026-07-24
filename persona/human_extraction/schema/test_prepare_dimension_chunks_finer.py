from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parents[3]
SCRIPT_PATH = (
    REPO_ROOT
    / "persona"
    / "human_extraction"
    / "schema"
    / "prepare_dimension_chunks_finer.py"
)
V3_EXTRACTOR_PATH = (
    REPO_ROOT
    / "persona"
    / "human_extraction"
    / "scripts"
    / "extract_personas_stackoverflow_vllm_v3.py"
)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def chunk_module():
    return load_module("prepare_dimension_chunks_finer_test", SCRIPT_PATH)


@pytest.fixture(scope="module")
def v3_module():
    return load_module("extract_personas_stackoverflow_vllm_v3_test", V3_EXTRACTOR_PATH)


def test_finer_manifest_has_exact_coverage_and_distribution(chunk_module):
    catalog = chunk_module.load_and_validate_catalog(chunk_module.DEFAULT_SOURCE)
    manifest = chunk_module.build_manifest(catalog)
    source_by_id = {dimension["id"]: dimension for dimension in catalog["dimensions"]}
    flattened = [
        dimension_id
        for chunk in manifest["chunks"]
        for dimension_id in chunk["dimension_ids"]
    ]
    sizes = [chunk["size"] for chunk in manifest["chunks"]]

    assert len(flattened) == 1290
    assert Counter(flattened) == Counter(source_by_id.keys())
    assert len(sizes) == 70
    assert min(sizes) == 11
    assert statistics.median(sizes) == 18
    assert max(sizes) == 25
    assert sum(size < 25 for size in sizes) == 65
    assert sum(15 <= size <= 24 for size in sizes) == 59
    assert all(size <= 25 for size in sizes)

    for chunk in manifest["chunks"]:
        assert chunk["size"] == len(chunk["dimension_ids"])
        assert chunk["dimension_ids"] == [
            dimension["id"] for dimension in chunk["dimensions"]
        ]
        assert [dimension["index"] for dimension in chunk["dimensions"]] == sorted(
            dimension["index"] for dimension in chunk["dimensions"]
        )
        assert all(source_by_id[dimension["id"]] == dimension for dimension in chunk["dimensions"])


def test_every_finer_size_exception_is_explicit_and_semantic(chunk_module):
    catalog = chunk_module.load_and_validate_catalog(chunk_module.DEFAULT_SOURCE)
    manifest = chunk_module.build_manifest(catalog)
    expected_exception_ids = {
        "demographics_household_social_context",
        "languages_core_europe",
        "languages_african_middle_eastern_global",
        "expertise_law_finance_economics",
        "expertise_earth_environment_transport",
        "industries_economy_infrastructure",
        "industries_public_creative_services",
        "personality_big_five_openness_conscientiousness",
        "health_management_accessibility",
        "hobbies_crafts_collecting_nature",
        "hobbies_adventure_food_performance",
    }
    actual_exception_ids = {
        item["chunk_id"] for item in manifest["summary"]["size_exceptions"]
    }

    assert actual_exception_ids == expected_exception_ids
    assert len(actual_exception_ids) == 11
    for chunk in manifest["chunks"]:
        outside = not (
            chunk_module.PREFERRED_MIN_SIZE
            <= chunk["size"]
            <= chunk_module.PREFERRED_MAX_SIZE
        )
        assert outside == ("size_exception" in chunk)
        if outside:
            assert len(chunk["size_exception"]) > 40


def test_finer_manifest_metadata_and_rendering_are_current(chunk_module):
    catalog = chunk_module.load_and_validate_catalog(chunk_module.DEFAULT_SOURCE)
    manifest = chunk_module.build_manifest(catalog)
    first = chunk_module.render_manifest(manifest)
    second = chunk_module.render_manifest(chunk_module.build_manifest(catalog))

    assert first == second
    assert chunk_module.MANIFEST_VERSION == "2.0"
    assert chunk_module.TARGET_SIZE == 20
    assert chunk_module.PREFERRED_MIN_SIZE == 15
    assert chunk_module.PREFERRED_MAX_SIZE == 24
    assert chunk_module.DEFAULT_OUTPUT.name == "dimension_chunks_finer.jsonl"
    assert chunk_module.DEFAULT_OUTPUT.read_text(encoding="utf-8") == first
    assert chunk_module.main(["--check"]) == 0

    records = [json.loads(line) for line in first.splitlines()]
    source_hash = chunk_module.canonical_sha256(catalog)
    assert len(records) == 70
    assert all(record["manifest_context"]["manifest_version"] == "2.0" for record in records)
    assert all(record["manifest_context"]["chunk_count"] == 70 for record in records)
    assert all(
        record["manifest_context"]["source_catalog"]["canonical_json_sha256"]
        == source_hash
        for record in records
    )
    assert all(record["dimensions"] for record in records)


def test_v3_loads_every_finer_chunk_and_builds_its_schema(chunk_module, v3_module):
    manifest = v3_module.load_dimension_manifest(chunk_module.DEFAULT_OUTPUT)

    assert manifest.version == "2.0"
    assert len(manifest.chunks) == 70
    assert len({chunk.chunk_id for chunk in manifest.chunks}) == 70
    assert sum(len(chunk.dimensions) for chunk in manifest.chunks) == 1290
    for chunk in manifest.chunks:
        schema = v3_module.build_chunk_json_schema(chunk)
        fields = schema["properties"]["fields"]
        assert fields["maxItems"] == len(chunk.dimensions)
        assert len(fields["items"]["oneOf"]) == len(chunk.dimensions)
