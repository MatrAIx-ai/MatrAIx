from __future__ import annotations

import importlib.util
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PERSONA_PATH_PATTERN = re.compile(r"PERSONA_PATH=([^\s]+)")


def _persona_paths_from_text(text: str) -> list[Path]:
    return [ROOT / match.group(1) for match in PERSONA_PATH_PATTERN.finditer(text)]


def _assert_persona_paths_exist(paths: list[Path]) -> None:
    assert paths, "expected at least one PERSONA_PATH default"
    missing = [path.relative_to(ROOT).as_posix() for path in paths if not path.exists()]
    assert missing == []


def test_oasis_static_docker_persona_defaults_exist() -> None:
    static_files = [
        ROOT / "environment/oasis/docker-compose.yaml",
        ROOT / "environment/oasis/agents/Dockerfile",
    ]

    paths = []
    for path in static_files:
        paths.extend(_persona_paths_from_text(path.read_text()))

    _assert_persona_paths_exist(paths)


def test_oasis_generated_compose_persona_defaults_exist(tmp_path: Path) -> None:
    module_path = ROOT / "environment/oasis/generate_compose.py"
    spec = importlib.util.spec_from_file_location("oasis_generate_compose", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    output_path = tmp_path / "docker-compose.generated.yaml"
    module.generate(num_agents=5, output_path=output_path.as_posix())

    _assert_persona_paths_exist(_persona_paths_from_text(output_path.read_text()))
