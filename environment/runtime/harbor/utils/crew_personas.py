"""Upload crew persona YAML referenced by ``input/crew_manifest*.yaml``.

PersonaBench convention (see ``application/README.md``): persona profiles live
under repo-root ``persona/datasets/`` and are referenced at job launch — not
copied into task or environment folders. Tasks that run a multi-persona
simulation inside the container (e.g. Starclash) list those paths in
``crew_manifest.yaml``; Harbor uploads them before the oracle/agent phase,
mirroring ``PersonaMixin``'s single-file upload to ``/app/input/persona.yaml``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from harbor.environments.base import BaseEnvironment

_DEFAULT_CREW_MANIFEST = "input/crew_manifest.yaml"
_CONTAINER_WORKDIR = "/app"


def find_crew_manifest(task_dir: Path) -> Path | None:
    """Return ``task_dir/input/crew_manifest.yaml`` when present."""
    manifest = task_dir / _DEFAULT_CREW_MANIFEST
    return manifest if manifest.is_file() else None


def resolve_repo_root(task_dir: Path) -> Path | None:
    """Reuse TaskPaths repository-root discovery."""
    from harbor.models.task.paths import TaskPaths

    return TaskPaths(task_dir)._find_repository_root()


def persona_paths_from_manifest(manifest_path: Path) -> list[str]:
    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return []
    paths = raw.get("persona_paths")
    if not isinstance(paths, list):
        return []
    return [str(item) for item in paths if item]


def container_path_for_persona(rel_path: str, *, workdir: str = _CONTAINER_WORKDIR) -> str:
    clean = rel_path.replace("\\", "/").lstrip("/")
    return f"{workdir.rstrip('/')}/{clean}"


async def upload_crew_personas_for_task(
    environment: BaseEnvironment,
    task_dir: Path,
    *,
    workdir: str = _CONTAINER_WORKDIR,
    crew_manifest: Path | None = None,
    logger: logging.Logger | None = None,
) -> int:
    """Upload persona YAML files listed in a crew manifest into the container.

    Returns the number of files uploaded. No-op when the task has no crew
    manifest or no ``persona_paths`` entries.
    """
    manifest = crew_manifest or find_crew_manifest(task_dir)
    if manifest is None:
        return 0

    rel_paths = persona_paths_from_manifest(manifest)
    if not rel_paths:
        return 0

    repo_root = resolve_repo_root(task_dir) or Path.cwd()
    log = logger or logging.getLogger(__name__)
    uploaded = 0

    for rel_path in rel_paths:
        host_path = (repo_root / rel_path).resolve()
        if not host_path.is_file():
            raise FileNotFoundError(
                f"Crew manifest {manifest} references missing persona file: "
                f"{rel_path} (resolved to {host_path}). Persona profiles must "
                f"exist under repo-root persona/datasets/ — see application/README.md."
            )
        target = container_path_for_persona(rel_path, workdir=workdir)
        log.debug("Uploading crew persona %s -> %s", host_path, target)
        await environment.upload_file(host_path, target)
        uploaded += 1

    return uploaded