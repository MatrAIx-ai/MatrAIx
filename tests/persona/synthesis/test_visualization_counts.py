from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
GRAPH_PATH = ROOT / "persona" / "synthesis" / "graph" / "full_dag.json"
SCHEMA_PATH = ROOT / "persona" / "schema" / "dimensions.json"
HTML_PATH = ROOT / "persona" / "synthesis" / "visualization" / "full_dag_overview.html"


class _GraphDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._in_graph_data = False
        self._chunks: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attr_map = dict(attrs)
        if tag == "script" and attr_map.get("id") == "graph-data":
            self._in_graph_data = True

    def handle_data(self, data: str) -> None:
        if self._in_graph_data:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_graph_data:
            self._in_graph_data = False

    def payload(self) -> dict[str, Any]:
        if not self._chunks:
            msg = "visualization graph-data script was not found"
            raise AssertionError(msg)
        return json.loads("".join(self._chunks))


def _graph_data_payload() -> dict[str, Any]:
    parser = _GraphDataParser()
    parser.feed(HTML_PATH.read_text(encoding="utf-8"))
    return parser.payload()


def test_visualization_distinguishes_schema_attributes_from_helper_nodes() -> None:
    graph = json.loads(GRAPH_PATH.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    html = HTML_PATH.read_text(encoding="utf-8")
    payload = _graph_data_payload()

    schema_ids = {dimension["id"] for dimension in schema["dimensions"]}
    graph_ids = {node["id"] for node in graph["nodes"]}
    emitted_ids = {
        node["id"] for node in graph["nodes"] if node.get("emit", True) is not False
    }

    assert schema["targetDimensions"] == len(schema_ids) == 1339
    assert len(graph_ids) == 1357
    assert schema_ids <= graph_ids
    assert len(graph_ids - schema_ids) == 18

    assert payload["counts"] == {
        "schema_attributes": 1339,
        "emitted_attributes": 1230,
        "hidden_schema_attributes": 109,
        "latent_helper_nodes": 18,
        "graph_nodes": 1357,
        "hidden_graph_nodes": 127,
    }
    assert len(payload["nodes"]) == 1357
    assert len(payload["edges"]) == 6937
    assert sum(category["attributeCount"] for category in payload["categories"]) == 1339
    assert sum(category["helperCount"] for category in payload["categories"]) == 18

    helper_nodes = {node["id"] for node in payload["nodes"] if not node["isAttribute"]}
    assert helper_nodes == graph_ids - schema_ids
    assert all(node["type"] == "latent/helper" for node in payload["nodes"] if not node["isAttribute"])
    assert {node["id"] for node in payload["nodes"] if node["emit"]} == schema_ids & emitted_ids

    assert "Schema attributes" in html
    assert "Latent/helper nodes" in html
    assert "Graph nodes" in html
