from __future__ import annotations

import json
import io
import os
import re
import sys
import tempfile
from ast import literal_eval
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from recbot.catalog_resources import RecAIResourceSpec, ensure_recai_resource_dir
from recbot.native_contract import build_native_action
from recbot.semantic_ranker import SemanticProfileRankingTool
from recbot.types import RecBotRequest, RecBotTrace, RecBotTurnResult


def _latest_user_message(request: RecBotRequest) -> str:
    return request.latest_user_message


def _build_chat_history(request: RecBotRequest) -> str:
    lines: list[str] = []
    for message in request.messages[:-1]:
        if message.role == "user":
            prefix = "Human"
        elif message.role == "assistant":
            prefix = "Assistent"
        else:
            prefix = "System"
        lines.append(f"{prefix}: {message.content}")
    return "\n".join(lines)


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return int(raw)


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return float(raw)


def _planning_recording_file() -> str:
    return os.environ.get(
        "INTERECAGENT_PLANNING_RECORDING_FILE",
        str(Path(tempfile.gettempdir()) / "matraix_interecagent_plan.jsonl"),
    )


def _resource_mode() -> str:
    return os.environ.get("INTERECAGENT_RESOURCE_MODE", "matraix_catalog")


def _ranker_mode(resource_mode: str) -> str:
    default = "semantic_profile" if resource_mode == "matraix_catalog" else "native"
    return os.environ.get("INTERECAGENT_RANKER_MODE", default)


def _default_catalog_path(domain: str) -> Path:
    if domain != "movie":
        raise RuntimeError(
            "INTERECAGENT_CATALOG_PATH must be set for non-movie catalog-backed domains"
        )
    return APP_ROOT / "samples" / "cmu_movie_summary_tiny.jsonl"


def _catalog_resource_output_dir(domain: str) -> Path:
    configured = os.environ.get("INTERECAGENT_GENERATED_RESOURCE_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (
        REPO_ROOT
        / "data"
        / "cache"
        / "recommendation_chatbot_eval"
        / "recai_resources"
        / domain
    )


def _catalog_resource_spec(domain: str) -> RecAIResourceSpec:
    catalog_path = Path(
        os.environ.get("INTERECAGENT_CATALOG_PATH", str(_default_catalog_path(domain)))
    )
    return ensure_recai_resource_dir(
        catalog_path,
        _catalog_resource_output_dir(domain),
        domain,
    )


def _force_hard_filter_selectable_sql(sql: str) -> str:
    selectable_sql = re.sub(
        r"^\s*SELECT\s+.+?\s+FROM\s+",
        "SELECT * FROM ",
        sql,
        count=1,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return re.sub(
        r"\btags\s+((?:NOT\s+)?LIKE)\s+",
        r"display_text \1 ",
        selectable_sql,
        flags=re.IGNORECASE,
    )


class _HardFilterSelectAdapter:
    def __init__(self, tool: Any) -> None:
        self._tool = tool
        self.name = tool.name
        self.desc = (
            tool.desc
            + "\nThe SELECT clause is normalized by MatrAIx so candidate ids remain available to the native filter tool."
        )

    def run(self, inputs: str) -> str:
        return self._tool.run(_force_hard_filter_selectable_sql(inputs))


class _SeedExcludingSimilarityAdapter:
    def __init__(self, tool: Any, item_corpus: Any, candidate_buffer: Any) -> None:
        self._tool = tool
        self._item_corpus = item_corpus
        self._candidate_buffer = candidate_buffer
        self.name = tool.name
        self.desc = tool.desc

    def run(self, inputs: str) -> str:
        output = self._tool.run(inputs)
        seed_ids = self._seed_ids(inputs)
        if not seed_ids:
            return output
        candidates = self._candidate_buffer.get()
        filtered = [candidate for candidate in candidates if candidate not in set(seed_ids)]
        if filtered == candidates:
            return output
        self._candidate_buffer.push(self.name, filtered)
        suffix = f" Removed seed items {seed_ids} from similarity candidates."
        if getattr(self._candidate_buffer, "tracker", None):
            self._candidate_buffer.tracker[-1]["output"] = (
                str(self._candidate_buffer.tracker[-1].get("output", "")) + suffix
            )
        return output + suffix

    def _seed_ids(self, inputs: str) -> list[int]:
        try:
            titles = literal_eval(inputs)
        except Exception:
            try:
                titles = json.loads(inputs)
            except Exception:
                return []
        if isinstance(titles, str):
            titles = [titles]
        if not isinstance(titles, list) or not titles:
            return []
        try:
            matched_titles = self._item_corpus.fuzzy_match(titles, "title")
            info = self._item_corpus.convert_title_2_info(matched_titles, col_names="id")
            ids = info["id"]
        except Exception:
            return []
        if isinstance(ids, int):
            return [ids]
        return [int(item_id) for item_id in ids]


def _prepare_imports(interecagent_root: str, domain: str, require_resources: bool = False) -> None:
    root = Path(interecagent_root).expanduser().resolve()
    if not root.exists():
        raise RuntimeError(f"INTERECAGENT_ROOT does not exist: {root}")
    if not (root / "llm4crs").exists():
        raise RuntimeError(f"INTERECAGENT_ROOT must point to the InteRecAgent directory: {root}")
    resources_dir = root / "resources" / domain
    if require_resources and not resources_dir.exists():
        raise RuntimeError(
            f"RecAI resources for domain '{domain}' are missing at {resources_dir}. "
            "Download and unpack the ready-to-run InteRecAgent resources before running the smoke test."
        )
    os.environ["DOMAIN"] = domain
    root_path = str(root)
    sys.path[:] = [path for path in sys.path if path != root_path]
    sys.path.insert(0, root_path)


def _build_interecagent(domain: str):
    from llm4crs.agent_plan_first_openai import CRSAgentPlanFirstOpenAI
    from llm4crs.buffer import CandidateBuffer
    from llm4crs.corups import BaseGallery
    from llm4crs.mapper import MapTool
    from llm4crs.prompt import (
        CANDIDATE_STORE_TOOL_DESC,
        HARD_FILTER_TOOL_DESC,
        LOOK_UP_TOOL_DESC,
        MAP_TOOL_DESC,
        RANKING_TOOL_DESC,
        SOFT_FILTER_TOOL_DESC,
        TOOL_NAMES,
    )
    from llm4crs.query import QueryTool
    from llm4crs.retrieval import SQLSearchTool, SimilarItemTool
    from llm4crs.utils import FuncToolWrapper

    resource_mode = _resource_mode()
    if resource_mode == "recai_resources":
        from llm4crs.environ_variables import (
            CATEGORICAL_COLS,
            GAME_INFO_FILE,
            ITEM_SIM_FILE,
            MODEL_CKPT_FILE,
            TABLE_COL_DESC_FILE,
            USE_COLS,
        )
    elif resource_mode == "matraix_catalog":
        spec = _catalog_resource_spec(domain)
        GAME_INFO_FILE = str(spec.item_info_file)
        TABLE_COL_DESC_FILE = str(spec.table_col_desc_file)
        ITEM_SIM_FILE = str(spec.item_sim_file)
        MODEL_CKPT_FILE = os.environ.get(
            "INTERECAGENT_MODEL_CKPT_FILE",
            str(spec.model_ckpt_file),
        )
        USE_COLS = spec.use_cols
        CATEGORICAL_COLS = spec.categorical_cols
    else:
        raise RuntimeError(
            "INTERECAGENT_RESOURCE_MODE must be 'matraix_catalog' or 'recai_resources'"
        )

    domain_map = {"item": domain, "Item": domain.capitalize(), "ITEM": domain.upper()}
    tool_names = {key: value.format(**domain_map) for key, value in TOOL_NAMES.items()}
    max_candidate_num = _env_int("INTERECAGENT_MAX_CANDIDATE_NUM", 1000)

    item_corpus = BaseGallery(
        GAME_INFO_FILE,
        TABLE_COL_DESC_FILE,
        f"{domain}_information",
        columns=USE_COLS,
        fuzzy_cols=["title"] + CATEGORICAL_COLS,
        categorical_cols=CATEGORICAL_COLS,
    )
    candidate_buffer = CandidateBuffer(
        item_corpus,
        num_limit=max_candidate_num,
    )
    tools = {
        "BufferStoreTool": FuncToolWrapper(
            func=candidate_buffer.init_candidates,
            name=tool_names["BufferStoreTool"],
            desc=CANDIDATE_STORE_TOOL_DESC.format(**domain_map),
        ),
        "LookUpTool": QueryTool(
            name=tool_names["LookUpTool"],
            desc=LOOK_UP_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
        ),
        "HardFilterTool": _HardFilterSelectAdapter(
            SQLSearchTool(
                name=tool_names["HardFilterTool"],
                desc=HARD_FILTER_TOOL_DESC.format(**domain_map),
                item_corups=item_corpus,
                buffer=candidate_buffer,
                max_candidates_num=max_candidate_num,
            )
        ),
        "SoftFilterTool": _SeedExcludingSimilarityAdapter(
            SimilarItemTool(
                name=tool_names["SoftFilterTool"],
                desc=SOFT_FILTER_TOOL_DESC.format(**domain_map),
                item_sim_path=ITEM_SIM_FILE,
                item_corups=item_corpus,
                buffer=candidate_buffer,
                top_ratio=_env_float("INTERECAGENT_SIMILAR_RATIO", 0.05),
            ),
            item_corpus,
            candidate_buffer,
        ),
        "MapTool": MapTool(
            name=tool_names["MapTool"],
            desc=MAP_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
        ),
    }
    map_tool = tools.pop("MapTool")
    ranker_mode = _ranker_mode(resource_mode)
    if ranker_mode == "native":
        from llm4crs.ranking import RecModelTool

        tools["RankingTool"] = RecModelTool(
            name=tool_names["RankingTool"],
            desc=RANKING_TOOL_DESC.format(**domain_map),
            model_fpath=MODEL_CKPT_FILE,
            item_corups=item_corpus,
            buffer=candidate_buffer,
            rec_num=_env_int("INTERECAGENT_RANK_NUM", 100),
        )
    elif ranker_mode == "semantic_profile":
        tools["RankingTool"] = SemanticProfileRankingTool(
            name=tool_names["RankingTool"],
            desc=RANKING_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
            rec_num=_env_int("INTERECAGENT_RANK_NUM", 100),
        )
    else:
        raise RuntimeError(
            "INTERECAGENT_RANKER_MODE must be 'semantic_profile' or 'native'"
        )
    tools["MapTool"] = map_tool
    agent = CRSAgentPlanFirstOpenAI(
        domain,
        tools,
        candidate_buffer,
        item_corpus,
        os.environ.get("INTERECAGENT_ENGINE", "gpt-4o-mini"),
        os.environ.get("INTERECAGENT_BOT_TYPE", "chat"),
        max_tokens=_env_int("INTERECAGENT_MAX_OUTPUT_TOKENS", 1024),
        enable_shorten=bool(_env_int("INTERECAGENT_ENABLE_SHORTEN", 0)),
        demo_mode=os.environ.get("INTERECAGENT_DEMO_MODE", "zero"),
        demo_dir_or_file=os.environ.get("INTERECAGENT_DEMO_DIR_OR_FILE"),
        num_demos=_env_int("INTERECAGENT_NUM_DEMOS", 3),
        critic=None,
        reflection_limits=_env_int("INTERECAGENT_REFLECTION_LIMITS", 3),
        planning_recording_file=_planning_recording_file(),
        verbose=bool(_env_int("INTERECAGENT_VERBOSE", 0)),
        reply_style=os.environ.get("INTERECAGENT_REPLY_STYLE", "detailed"),
        enable_summarize=_env_int("INTERECAGENT_ENABLE_SUMMARIZE", 1),
    )
    agent.init_agent()
    agent.set_mode(os.environ.get("INTERECAGENT_MODE", "accuracy"))
    return agent


def _last_recorded_plan(agent: Any) -> str | None:
    record_cache = getattr(agent, "_plan_record_cache", {})
    trajectory = record_cache.get("traj", []) if isinstance(record_cache, dict) else []
    for entry in reversed(trajectory):
        if isinstance(entry, dict) and entry.get("role") == "plan":
            return entry.get("content")
    return None


def _recommended_item_ids(agent: Any) -> list[str]:
    candidate_buffer = getattr(agent, "candidate_buffer", None)
    tracker = getattr(candidate_buffer, "tracker", [])
    item_corpus = getattr(agent, "item_corups", None)
    if not isinstance(tracker, list) or item_corpus is None:
        return []
    for entry in reversed(tracker):
        if not isinstance(entry, dict):
            continue
        tool_name = str(entry.get("tool", ""))
        if "map" not in tool_name.lower():
            continue
        output = str(entry.get("output", ""))
        marker = "Here are recommendations:"
        if marker in output:
            output = output.split(marker, 1)[1]
        titles = [title.strip() for title in output.split(";") if title.strip()]
        if not titles:
            continue
        try:
            info = item_corpus.convert_title_2_info(titles, col_names="external_id")
            external_ids = info["external_id"]
            if isinstance(external_ids, str):
                return [external_ids]
            return [str(item_id) for item_id in external_ids]
        except Exception:
            return []
    return []


def _raw_tool_outputs(agent: Any) -> Any:
    candidate_buffer = getattr(agent, "candidate_buffer", None)
    tracker = getattr(candidate_buffer, "tracker", None)
    if tracker:
        return tracker
    return getattr(candidate_buffer, "track_info", None)


def _repair_empty_tool_plan_response(response: str, native_action: Any) -> str:
    if (
        response.startswith("Something went wrong, please retry.")
        and isinstance(getattr(native_action, "raw_tool_plan", None), list)
        and len(native_action.raw_tool_plan) == 0
    ):
        return (
            "What kind of movie are you in the mood for? "
            "You can tell me a genre, tone, or a movie you recently liked."
        )
    return response


def run_turn(request: RecBotRequest) -> RecBotTurnResult:
    interecagent_root = os.environ.get("INTERECAGENT_ROOT")
    if not interecagent_root:
        raise RuntimeError("INTERECAGENT_ROOT must be set")

    domain = os.environ.get("INTERECAGENT_DOMAIN", request.metadata.get("domain", "movie"))
    resource_mode = _resource_mode()
    _prepare_imports(
        interecagent_root,
        domain,
        require_resources=resource_mode == "recai_resources",
    )
    agent = _build_interecagent(domain)

    user_message = _latest_user_message(request)
    os.environ["MATRAIX_CURRENT_USER_REQUEST"] = user_message
    response = agent.run({"input": user_message}, chat_history=_build_chat_history(request))
    raw_plan = _last_recorded_plan(agent)
    native_raw = raw_plan if raw_plan else f"Final Answer: {response}"
    native_action = build_native_action(native_raw)
    response = _repair_empty_tool_plan_response(response, native_action)
    raw_tool_plan = native_action.raw_tool_plan if isinstance(native_action.raw_tool_plan, list) else []
    trace = RecBotTrace(
        raw_tool_plan=raw_tool_plan,
        raw_tool_outputs=_raw_tool_outputs(agent),
        recommended_item_ids=_recommended_item_ids(agent),
    )
    return RecBotTurnResult(
        backend="interecagent",
        conversation_id=request.conversation_id,
        turn_id=request.turn_id,
        user_message=user_message,
        assistant_message=response,
        native_action=native_action,
        trace=trace,
    )


def main() -> int:
    try:
        stdout = sys.stdout
        payload = json.load(sys.stdin)
        request = RecBotRequest.from_dict(payload)
        backend_stdout = io.StringIO()
        with redirect_stdout(backend_stdout):
            result = run_turn(request)
        backend_output = backend_stdout.getvalue()
        if backend_output:
            print(backend_output, file=sys.stderr, end="")
        json.dump(result.to_dict(), stdout)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
