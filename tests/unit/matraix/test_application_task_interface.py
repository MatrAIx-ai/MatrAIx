from __future__ import annotations

import json
import tomllib
from pathlib import Path

from harbor.models.task.config import TaskConfig

from matraix.task_catalog import get_task_catalog_entry


REPO_ROOT = Path(__file__).resolve().parents[3]
TASKS_ROOT = REPO_ROOT / "application" / "tasks"
INTERFACE_ROOT = TASKS_ROOT / "application_interface"
ECOMMERCE_TASK = TASKS_ROOT / "web-ecommerce-platform_product-discovery"


def test_application_interface_manifest_groups_core_protocols() -> None:
    manifest = json.loads((INTERFACE_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["schemaVersion"] == "application-task-interface-v1"
    assert set(manifest["applicationTypes"]) == {"survey", "chatbot", "web"}
    assert manifest["applicationTypes"]["survey"]["status"] == "active"
    assert (
        manifest["applicationTypes"]["survey"]["canonicalTask"]
        == "application/tasks/survey_form"
    )
    assert (
        manifest["applicationTypes"]["chatbot"]["canonicalTask"]
        == "application/tasks/chatbot_chat_api"
    )
    assert (
        manifest["applicationTypes"]["web"]["canonicalTask"]
        == "application/tasks/web-ecommerce-platform_product-discovery"
    )


def test_application_interface_docs_exist_for_each_protocol() -> None:
    for dirname in ("survey", "chatbot", "web"):
        doc = INTERFACE_ROOT / dirname / "README.md"
        assert doc.is_file(), doc
        text = doc.read_text(encoding="utf-8")
        assert "Task instruction" in text
        assert "Interaction protocol" in text
        assert "Evaluation contract" in text


def test_web_ecommerce_platform_task_is_task_specific_hosted_app() -> None:
    cfg = TaskConfig.model_validate_toml(
        (ECOMMERCE_TASK / "task.toml").read_text(encoding="utf-8")
    )
    assert cfg.task is not None
    assert cfg.task.name == "matraix/application-web-ecommerce-platform-product-discovery"

    raw = tomllib.loads((ECOMMERCE_TASK / "task.toml").read_text(encoding="utf-8"))
    assert raw["metadata"]["type"] == "web"
    assert raw["metadata"]["domain"] == "commerce-retail"
    assert "/app/output" in raw["artifacts"]

    compose = (ECOMMERCE_TASK / "environment" / "docker-compose.yaml").read_text(
        encoding="utf-8"
    )
    assert "ecommerce-web" in compose
    assert "condition: service_healthy" in compose

    instruction = (ECOMMERCE_TASK / "instruction.md").read_text(encoding="utf-8")
    assert "http://ecommerce-web:8000/" in instruction
    assert "/app/output/ecommerce_interaction.json" in instruction
    assert "browser" in instruction.lower()


def test_survey_form_task_is_generic_instrument_host() -> None:
    task = TASKS_ROOT / "survey_form"
    cfg = TaskConfig.model_validate_toml(
        (task / "task.toml").read_text(encoding="utf-8")
    )
    assert cfg.task is not None
    assert cfg.task.name == "matraix/application-survey-form"

    raw = tomllib.loads((task / "task.toml").read_text(encoding="utf-8"))
    assert raw["metadata"]["type"] == "survey"
    assert raw["metadata"]["domain"] == "software"
    assert "/app/output" in raw["artifacts"]

    instruction = (task / "instruction.md").read_text(encoding="utf-8")
    assert "/app/output/survey_result.json" in instruction
    assert "answers" in instruction
    assert "trajectory" in instruction

    test_sh = (task / "tests" / "test.sh").read_text(encoding="utf-8")
    assert "python3 /tests/test_state.py" in test_sh

    example_prompt = task / "examples" / "product_attitudes_task_prompt.md"
    assert example_prompt.is_file()
    prompt_text = example_prompt.read_text(encoding="utf-8")
    assert "product_attitudes_v1" in prompt_text
    assert "/app/output/survey_result.json" in prompt_text

    job = (
        REPO_ROOT
        / "configs"
        / "jobs"
        / "example-job-recipe"
        / "appSim-survey-form-local.yaml"
    )
    assert job.is_file()
    job_text = job.read_text(encoding="utf-8")
    assert "application/tasks/survey_form" in job_text
    assert "product_attitudes_task_prompt.md" in job_text


def test_web_ecommerce_platform_verifier_schema_names_persona_feedback() -> None:
    verifier = (ECOMMERCE_TASK / "tests" / "test_state.py").read_text(encoding="utf-8")
    assert "need_satisfaction" in verifier
    assert "ease_of_use" in verifier
    assert "overall_experience_rating" in verifier


def test_web_ecommerce_platform_has_local_visual_assets() -> None:
    site = ECOMMERCE_TASK / "environment" / "ecommerce-web" / "site"
    catalog = json.loads((site / "catalog.json").read_text(encoding="utf-8"))
    index = (site / "index.html").read_text(encoding="utf-8")
    assert '<img class="product-media"' in index
    for product in catalog["products"]:
        image = product.get("image")
        assert isinstance(image, str) and image.startswith("assets/")
        assert (site / image).is_file(), image


def test_canonical_web_task_is_in_task_catalog() -> None:
    entry = get_task_catalog_entry(
        "application/tasks/web-ecommerce-platform_product-discovery"
    )
    assert entry is not None
    assert entry["type"] == "web"
    assert entry["domain"] == "commerce-retail"


def test_canonical_survey_task_is_in_task_catalog() -> None:
    entry = get_task_catalog_entry("application/tasks/survey_form")
    assert entry is not None
    assert entry["type"] == "survey"
    assert entry["domain"] == "software"
