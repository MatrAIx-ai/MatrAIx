from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from harbor.models.task.paths import TaskPaths
import tomllib


ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_SURVEY = ROOT / "application/tasks/example-survey_product-feedback"
RECOMMENDER_CHAT = ROOT / "application/tasks/recommender-agent_chat_api"
TASK_SPEC_ROOT = ROOT / "application/task-spec"
REAL_TASK_BANK = ROOT / "application/tasks/real_chatbot_website_task_bank.md"
RASA_ACCOUNT = ROOT / "application/tasks/rasa-account-recovery_support-chatbot"
GITHUB_PRICING = ROOT / "application/tasks/web-github-pricing_plan-fit"
PYTHON_DOCS = ROOT / "application/tasks/web-python-docs_error-lookup"


def test_example_survey_task_metadata_is_clean() -> None:
    task_text = (EXAMPLE_SURVEY / "task.toml").read_text(encoding="utf-8")
    task = tomllib.loads(task_text)

    assert task["task"]["name"] == "personabench/application-survey-product-feedback"
    assert task["metadata"]["type"] == "survey"
    assert "matraix/" not in task_text.lower()

    readme = (EXAMPLE_SURVEY / "README.md").read_text(encoding="utf-8")
    assert "bench-dev-2000" not in readme


def test_example_survey_verifier_accepts_minimal_valid_result(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "survey_result.json").write_text(
        json.dumps(
            {
                "instrument": {"id": "smoke", "title": "Smoke survey"},
                "answers": [
                    {
                        "questionId": "q1",
                        "value": 4,
                        "rationale": "Fits the assigned persona.",
                        "confidence": 0.8,
                    }
                ],
                "trajectory": [
                    {
                        "timestamp": "2026-06-24T00:00:00Z",
                        "actor": "user",
                        "action": "answer_question",
                        "context": {"questionId": "q1"},
                        "outcome": {"questionId": "q1", "value": 4},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    verifier_path = EXAMPLE_SURVEY / "tests/test_state.py"
    spec = importlib.util.spec_from_file_location("example_survey_test_state", verifier_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.OUTPUT_DIR = output_dir
    module.RESULT_PATH = output_dir / "survey_result.json"
    assert module.main() == 0


def test_recommender_chat_task_metadata_is_clean() -> None:
    task_text = (RECOMMENDER_CHAT / "task.toml").read_text(encoding="utf-8")
    task = tomllib.loads(task_text)

    assert task["task"]["name"] == "personabench/application-recommender-agent-chat-api"
    assert task["metadata"]["type"] == "chatbot"
    assert task["metadata"]["domain"] == "commerce-retail"
    assert "matraix/" not in task_text.lower()

    readme = (RECOMMENDER_CHAT / "README.md").read_text(encoding="utf-8")
    assert "applications/recommendation_chatbot_eval" not in readme
    assert "--persona-ids 0042" in readme
    assert "recommender-agent-chat-api-auto-n1.yaml" in readme


def test_recommender_chat_verifier_accepts_minimal_valid_result(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    session_id = "session-123"
    messages = [
        {"role": "user", "content": "I want a thoughtful movie for a quiet night."},
        {"role": "assistant", "content": "Do you prefer drama, comedy, or sci-fi?"},
        {"role": "user", "content": "Drama, but not too bleak."},
        {"role": "assistant", "content": "I can look for warm dramas with strong characters."},
        {"role": "user", "content": "A recent film would be best."},
        {"role": "assistant", "content": "Past Lives is a good fit."},
    ]
    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "sessionId": session_id,
                "domain": "movie",
                "messages": messages,
                "turns": [],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "user_feedback.json").write_text(
        json.dumps(
            {
                "needConstraintSatisfaction": "yes",
                "personalPreferenceSatisfaction": "partially",
                "overallExperienceRating": 8,
                "reason": "The recommendation fit the quiet drama request.",
                "askedUsefulClarificationQuestions": True,
            }
        ),
        encoding="utf-8",
    )

    verifier_path = RECOMMENDER_CHAT / "tests/test_state.py"
    spec = importlib.util.spec_from_file_location(
        "recommender_chat_test_state", verifier_path
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.OUTPUT_DIR = output_dir
    module.TRANSCRIPT_PATH = output_dir / "transcript.json"
    module.FEEDBACK_PATH = output_dir / "user_feedback.json"
    assert module.main() == 0


def test_recommender_chat_sidecar_contract() -> None:
    server_path = (
        TaskPaths.from_task_dir(RECOMMENDER_CHAT).environment_dir
        / "recommender-api"
        / "server.py"
    )
    spec = importlib.util.spec_from_file_location("recommender_api_server", server_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    session = module.create_session("movie")
    first_turn = module.post_message(
        session["sessionId"], "I want a warm, character-driven movie."
    )
    second_turn = module.post_message(
        session["sessionId"], "Please avoid bleak endings."
    )
    third_turn = module.post_message(session["sessionId"], "Something recent is ideal.")

    assert first_turn["reply"]
    assert second_turn["reply"]
    assert third_turn["recommendedItems"]

    conversation = module.get_conversation(session["sessionId"])
    recommendations = module.get_recommendations(session["sessionId"])

    assert len(conversation["messages"]) == 6
    assert recommendations["total"] >= 1
    assert recommendations["recommendedItems"][0]["itemId"].startswith("movie-")


def test_rasa_account_recovery_task_metadata_is_clean() -> None:
    task_text = (RASA_ACCOUNT / "task.toml").read_text(encoding="utf-8")
    task = tomllib.loads(task_text)

    assert task["task"]["name"] == (
        "personabench/application-rasa-account-recovery-support-chatbot"
    )
    assert task["metadata"]["type"] == "chat"
    assert task["metadata"]["domain"] == "commerce-retail"
    assert task["environment"]["definition"] == (
        "application/rasa-account-recovery_support-chatbot"
    )
    assert TaskPaths.from_task_dir(RASA_ACCOUNT).environment_dir.is_dir()
    assert "matraix/" not in task_text.lower()

    readme = (RASA_ACCOUNT / "README.md").read_text(encoding="utf-8")
    assert "https://github.com/RasaHQ/rasa" in readme
    assert "http://rasa-account-recovery:5005/webhooks/rest/webhook" in readme


def test_rasa_account_recovery_verifier_accepts_minimal_valid_result(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    conversation_id = "persona-0042"
    (output_dir / "transcript.json").write_text(
        json.dumps(
            {
                "conversation_id": conversation_id,
                "sidecar": "rasa-account-recovery",
                "endpoint": (
                    "http://rasa-account-recovery:5005/webhooks/rest/webhook"
                ),
                "messages": [
                    {
                        "role": "user",
                        "content": "Hello, I need to recover my account.",
                    },
                    {
                        "role": "assistant",
                        "content": "I can help with account recovery.",
                    },
                    {
                        "role": "user",
                        "content": "The account reset email is not arriving.",
                    },
                    {
                        "role": "assistant",
                        "content": "Try one new recovery link and check spam.",
                    },
                    {
                        "role": "user",
                        "content": "I want to avoid sharing sensitive data.",
                    },
                    {
                        "role": "assistant",
                        "content": "Use only the account email alias here.",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    (output_dir / "account_recovery_result.json").write_text(
        json.dumps(
            {
                "conversation_id": conversation_id,
                "source_reference": {
                    "repository": "https://github.com/RasaHQ/rasa",
                    "runtime": "rasa/rasa:3.6.21-full",
                    "endpoint": (
                        "http://rasa-account-recovery:5005/webhooks/rest/webhook"
                    ),
                },
                "application_result": {
                    "outcome_class": "recovery_options_explained",
                    "recovery_path": "email verification and support escalation",
                    "asked_for_sensitive_data": False,
                    "requested_personal_data": ["account email alias"],
                },
                "persona_self_report": {
                    "trust_rating": 7,
                    "frustration_rating": 4,
                    "privacy_comfort": "medium",
                    "reason": "The bot explained recovery without asking for PII.",
                },
                "metric_summary": {
                    "numeric": {
                        "turns_to_resolution": 3,
                        "trust_rating": 7,
                        "frustration_rating": 4,
                    },
                    "categorical": {
                        "outcome_class": "recovery_options_explained",
                        "privacy_comfort": "medium",
                    },
                    "textual": {
                        "main_friction": "Reset email delay remained unresolved.",
                        "persona_rationale": "The privacy boundary was clear.",
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    verifier_path = RASA_ACCOUNT / "tests/test_state.py"
    spec = importlib.util.spec_from_file_location(
        "rasa_account_recovery_test_state",
        verifier_path,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.OUTPUT_DIR = output_dir
    module.TRANSCRIPT_PATH = output_dir / "transcript.json"
    module.RESULT_PATH = output_dir / "account_recovery_result.json"
    assert module.main() == 0


def test_rasa_account_recovery_sidecar_uses_real_rasa_runtime() -> None:
    environment_dir = TaskPaths.from_task_dir(RASA_ACCOUNT).environment_dir
    bot_dir = environment_dir / "rasa-bot"

    dockerfile = (bot_dir / "Dockerfile").read_text(encoding="utf-8")
    assert "FROM rasa/rasa:3.6.21-full" in dockerfile
    assert "https://github.com/RasaHQ/rasa" in dockerfile
    assert "rasa train --fixed-model-name account_recovery" in dockerfile

    compose = (environment_dir / "docker-compose.yaml").read_text(encoding="utf-8")
    assert "rasa-account-recovery" in compose
    assert "5005" in compose

    credentials = (bot_dir / "credentials.yml").read_text(encoding="utf-8")
    domain = (bot_dir / "domain.yml").read_text(encoding="utf-8")
    rules = (bot_dir / "data/rules.yml").read_text(encoding="utf-8")
    nlu = (bot_dir / "data/nlu.yml").read_text(encoding="utf-8")

    assert "rest:" in credentials
    assert "utter_recovery_options" in domain
    assert "utter_privacy_boundary" in domain
    assert "intent: account_recovery" in rules
    assert "intent: identity_concern" in rules
    assert "I need to recover my account" in nlu


def test_real_chatbot_website_task_bank_covers_required_fields() -> None:
    text = REAL_TASK_BANK.read_text(encoding="utf-8")

    required_fields = [
        "Scenario name:",
        "Task type:",
        "Domain / vertical:",
        "Product or system under test:",
        "Source site or API:",
        "Task description:",
        "Instruction for each persona:",
        "Environment needs:",
        "Persona attributes that should affect behavior:",
        "Output telemetry:",
        "Aggregate metrics:",
        "Why personas should differ:",
    ]
    for field in required_fields:
        assert field in text

    assert text.count("### ") >= 10
    for source in (
        "https://github.com/pricing",
        "https://docs.python.org/",
        "https://openlibrary.org/developers/api",
        "https://github.com/chatwoot/chatwoot",
        "https://github.com/OpenBB-finance/OpenBB",
        "https://github.com/RasaHQ/rasa",
    ):
        assert source in text

    assert "application/tasks/web-github-pricing_plan-fit" in text
    assert "application/tasks/web-python-docs_error-lookup" in text
    assert "application/tasks/rasa-account-recovery_support-chatbot" in text


def test_github_pricing_task_metadata_is_clean() -> None:
    task_text = (GITHUB_PRICING / "task.toml").read_text(encoding="utf-8")
    task = tomllib.loads(task_text)

    assert task["task"]["name"] == "personabench/application-web-github-pricing-plan-fit"
    assert task["metadata"]["type"] == "web"
    assert task["metadata"]["domain"] == "software"
    assert task["agent"]["network_mode"] == "public"
    assert task["environment"]["definition"] == "application/web-github-pricing_plan-fit"
    assert TaskPaths.from_task_dir(GITHUB_PRICING).environment_dir.is_dir()
    assert "matraix/" not in task_text.lower()
    assert "https://github.com/pricing" in (
        GITHUB_PRICING / "instruction.md"
    ).read_text(encoding="utf-8")


def test_github_pricing_verifier_accepts_minimal_valid_result(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "pricing_plan_evaluation.json").write_text(
        json.dumps(
            {
                "source_url": "https://github.com/pricing",
                "selected_plan": "Team",
                "fit_rating": 8,
                "trust_rating": 7,
                "budget_fit": "acceptable",
                "conversion_intent": "consider",
                "reason": (
                    "The selected plan fits the persona's small team "
                    "collaboration needs."
                ),
                "friction_points": ["Add-on pricing needs a second pass."],
            }
        ),
        encoding="utf-8",
    )

    verifier_path = GITHUB_PRICING / "tests/test_state.py"
    spec = importlib.util.spec_from_file_location("github_pricing_test_state", verifier_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.OUTPUT = output_dir / "pricing_plan_evaluation.json"
    assert module.main() == 0


def test_python_docs_task_metadata_is_clean() -> None:
    task_text = (PYTHON_DOCS / "task.toml").read_text(encoding="utf-8")
    task = tomllib.loads(task_text)

    assert task["task"]["name"] == "personabench/application-web-python-docs-error-lookup"
    assert task["metadata"]["type"] == "web"
    assert task["metadata"]["domain"] == "software"
    assert task["agent"]["network_mode"] == "public"
    assert task["environment"]["definition"] == "application/web-python-docs_error-lookup"
    assert TaskPaths.from_task_dir(PYTHON_DOCS).environment_dir.is_dir()
    assert "matraix/" not in task_text.lower()
    assert "https://docs.python.org/" in (PYTHON_DOCS / "instruction.md").read_text(
        encoding="utf-8"
    )


def test_python_docs_verifier_accepts_minimal_valid_result(tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    (output_dir / "python_docs_lookup.json").write_text(
        json.dumps(
            {
                "source_url": "https://docs.python.org/3/library/pathlib.html",
                "topic": "pathlib.Path.read_text",
                "answer_summary": (
                    "Path.read_text reads a file into a string, and the encoding "
                    "argument should be set when text encoding matters."
                ),
                "documentation_confidence": 8,
                "ease_of_lookup": 7,
                "would_reuse_docs": True,
                "friction_points": ["The page is dense for beginners."],
            }
        ),
        encoding="utf-8",
    )

    verifier_path = PYTHON_DOCS / "tests/test_state.py"
    spec = importlib.util.spec_from_file_location("python_docs_test_state", verifier_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    module.OUTPUT = output_dir / "python_docs_lookup.json"
    assert module.main() == 0


def test_application_task_spec_manifest_uses_clean_task_paths() -> None:
    manifest = json.loads((TASK_SPEC_ROOT / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["schemaVersion"] == "application-task-spec-v1"
    assert set(manifest["applicationTypes"]) == {
        "survey",
        "chatbot",
        "web",
        "os-app",
    }
    assert manifest["applicationTypes"]["survey"]["canonicalTask"] == (
        "application/tasks/example-survey_product-feedback"
    )
    assert manifest["applicationTypes"]["chatbot"]["canonicalTask"] == (
        "application/tasks/recommender-agent_chat_api"
    )
    assert manifest["applicationTypes"]["web"]["canonicalTask"] == (
        "application/tasks/example-web-playwright_quote-choice"
    )
    assert manifest["applicationTypes"]["os-app"]["canonicalTask"] == (
        "application/tasks/example-computer-use-ios_photo-access-review"
    )


def test_application_task_spec_docs_cover_each_protocol() -> None:
    for dirname in ("survey", "chatbot", "web"):
        doc = TASK_SPEC_ROOT / dirname / "README.md"
        assert doc.is_file(), doc
        text = doc.read_text(encoding="utf-8")
        assert "Task instruction" in text
        assert "Interaction protocol" in text
        assert "Evaluation contract" in text
        assert "applications/tasks/" not in text

    os_app_doc = TASK_SPEC_ROOT / "os-app" / "README.md"
    assert os_app_doc.is_file()
    os_app_text = os_app_doc.read_text(encoding="utf-8")
    assert "evaluation and reporting contract" in os_app_text.lower()
