from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_persona_eval_core_and_chatbot_task_are_separated() -> None:
    app_root = REPO_ROOT / "applications" / "persona_eval"
    chatbot_api = (
        REPO_ROOT
        / "application"
        / "tasks"
        / "chatbot_chat_api"
        / "environment"
        / "chatbot_api"
    )

    assert (app_root / "backend").is_dir()
    assert (app_root / "frontend").is_dir()
    assert (app_root / "persona_eval").is_dir()
    assert not (app_root / "recbot").exists()
    assert not (app_root / "harbor_api").exists()
    assert (chatbot_api / "harbor_api").is_dir()
    assert (chatbot_api / "recbot").is_dir()
    assert (chatbot_api / "data" / "catalogs").is_dir()


def test_chatbot_task_compose_builds_from_task_owned_api_context() -> None:
    compose_path = (
        REPO_ROOT
        / "application"
        / "tasks"
        / "chatbot_chat_api"
        / "environment"
        / "docker-compose.yaml"
    )
    compose = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = compose["services"]

    for service_name in ("chatbot-api", "recai-api", "finance-api", "openbb-mcp"):
        assert services[service_name]["build"]["context"] == "./chatbot_api"
