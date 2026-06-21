# environments.oasis — OASIS multi-agent social simulation integration for MatrAIx.

from environments.oasis.persona_adapter import (
    OasisUserInfo,
    adapt_single_persona,
    load_personas_from_directory,
    load_personas_from_files,
    personas_to_oasis_dicts,
)

__all__ = [
    "OasisUserInfo",
    "adapt_single_persona",
    "load_personas_from_directory",
    "load_personas_from_files",
    "personas_to_oasis_dicts",
]
