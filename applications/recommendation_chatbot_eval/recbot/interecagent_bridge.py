from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any


APP_ROOT = Path(__file__).resolve().parents[1]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from recbot.native_contract import build_native_action
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


def _prepare_imports(interecagent_root: str, domain: str) -> None:
    root = Path(interecagent_root).expanduser().resolve()
    if not root.exists():
        raise RuntimeError(f"INTERECAGENT_ROOT does not exist: {root}")
    if not (root / "llm4crs").exists():
        raise RuntimeError(f"INTERECAGENT_ROOT must point to the InteRecAgent directory: {root}")
    resources_dir = root / "resources" / domain
    if not resources_dir.exists():
        raise RuntimeError(
            f"RecAI resources for domain '{domain}' are missing at {resources_dir}. "
            "Download and unpack the ready-to-run InteRecAgent resources before running the smoke test."
        )
    os.environ["DOMAIN"] = domain
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


def _build_interecagent(domain: str):
    from llm4crs.agent_plan_first_openai import CRSAgentPlanFirstOpenAI
    from llm4crs.buffer import CandidateBuffer
    from llm4crs.corups import BaseGallery
    from llm4crs.environ_variables import (
        CATEGORICAL_COLS,
        GAME_INFO_FILE,
        ITEM_SIM_FILE,
        MODEL_CKPT_FILE,
        TABLE_COL_DESC_FILE,
        USE_COLS,
    )
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
    from llm4crs.ranking import RecModelTool
    from llm4crs.retrieval import SQLSearchTool, SimilarItemTool
    from llm4crs.utils import FuncToolWrapper

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
        "HardFilterTool": SQLSearchTool(
            name=tool_names["HardFilterTool"],
            desc=HARD_FILTER_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
            max_candidates_num=max_candidate_num,
        ),
        "SoftFilterTool": SimilarItemTool(
            name=tool_names["SoftFilterTool"],
            desc=SOFT_FILTER_TOOL_DESC.format(**domain_map),
            item_sim_path=ITEM_SIM_FILE,
            item_corups=item_corpus,
            buffer=candidate_buffer,
            top_ratio=_env_float("INTERECAGENT_SIMILAR_RATIO", 0.05),
        ),
        "RankingTool": RecModelTool(
            name=tool_names["RankingTool"],
            desc=RANKING_TOOL_DESC.format(**domain_map),
            model_fpath=MODEL_CKPT_FILE,
            item_corups=item_corpus,
            buffer=candidate_buffer,
            rec_num=_env_int("INTERECAGENT_RANK_NUM", 100),
        ),
        "MapTool": MapTool(
            name=tool_names["MapTool"],
            desc=MAP_TOOL_DESC.format(**domain_map),
            item_corups=item_corpus,
            buffer=candidate_buffer,
        ),
    }
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


def run_turn(request: RecBotRequest) -> RecBotTurnResult:
    interecagent_root = os.environ.get("INTERECAGENT_ROOT")
    if not interecagent_root:
        raise RuntimeError("INTERECAGENT_ROOT must be set")

    domain = os.environ.get("INTERECAGENT_DOMAIN", request.metadata.get("domain", "movie"))
    _prepare_imports(interecagent_root, domain)
    agent = _build_interecagent(domain)

    user_message = _latest_user_message(request)
    response = agent.run({"input": user_message}, chat_history=_build_chat_history(request))
    raw_plan = _last_recorded_plan(agent)
    native_raw = raw_plan if raw_plan else f"Final Answer: {response}"
    native_action = build_native_action(native_raw)
    trace = RecBotTrace(
        raw_tool_plan=native_action.raw_tool_plan,
        raw_tool_outputs=getattr(getattr(agent, "candidate_buffer", None), "track_info", None),
        recommended_item_ids=[],
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
        payload = json.load(sys.stdin)
        request = RecBotRequest.from_dict(payload)
        result = run_turn(request)
        json.dump(result.to_dict(), sys.stdout)
        return 0
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
