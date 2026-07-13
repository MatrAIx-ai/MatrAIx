"""The renderer must be importable without numpy and render deterministically."""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DIMS_FIXTURE = {
    "dimensions": [
        {
            "id": "age_bracket",
            "label": "Age bracket",
            "category": "Demographic: Core",
            "values": ["18-24", "25-34"],
            "phrase": "aged {value}",
        },
        {
            "id": "hobby",
            "label": "Hobby",
            "category": "Interests: Food",
            "values": ["baking", "none"],
            "defaultValue": "none",
        },
    ]
}


def test_render_module_imports_stdlib_only():
    from persona.synthesis import render as render_module

    source = Path(render_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.partition(".")[0])
    assert imported_roots <= {"__future__", "json", "re", "pathlib", "typing"}


def test_render_core_bucket_and_default_suppression(tmp_path):
    from persona.synthesis.render import load_dims, render

    dims_path = tmp_path / "dims.json"
    dims_path.write_text(json.dumps(DIMS_FIXTURE), encoding="utf-8")
    dims = load_dims(dims_path)

    text = render({"age_bracket": "18-24", "hobby": "baking"}, dims)
    assert text == "A persona aged 18-24.\nInterests: their hobby is baking."

    # Default values and unknown attribute ids are silently omitted.
    text = render({"age_bracket": "18-24", "hobby": "none", "mystery": "x"}, dims)
    assert text == "A persona aged 18-24."


def test_script_reuses_the_module():
    from persona.synthesis.render import render

    path = REPO_ROOT / "persona" / "synthesis" / "scripts" / "render_personas.py"
    spec = importlib.util.spec_from_file_location("render_personas_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    assert module.render is render
