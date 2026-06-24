"""Built-in survey instruments for PersonaEval survey tasks."""

from __future__ import annotations

from typing import Dict, List

from backend.service.harbor_survey_eval import SurveyInstrument, SurveyQuestion

__all__ = [
    "DEFAULT_SURVEY_INSTRUMENT_ID",
    "get_survey_instrument",
    "list_survey_instruments",
]

DEFAULT_SURVEY_INSTRUMENT_ID = "product_attitudes_v1"


def _product_attitudes_v1() -> SurveyInstrument:
    return SurveyInstrument(
        id=DEFAULT_SURVEY_INSTRUMENT_ID,
        title="Product Attitudes",
        description=(
            "A short product-concept survey completed directly by the simulated "
            "persona respondent."
        ),
        questions=[
            SurveyQuestion(
                id="concept_fit",
                prompt="This product would fit my current needs.",
                type="likert",
                min_value=1,
                max_value=5,
                construct="product_need_fit",
            ),
            SurveyQuestion(
                id="preference_fit",
                prompt="This product matches my personal preferences.",
                type="likert",
                min_value=1,
                max_value=5,
                construct="personal_preference_fit",
            ),
            SurveyQuestion(
                id="adoption_barrier",
                prompt="What would be your biggest barrier to using this product?",
                type="single_choice",
                options=["price", "privacy", "complexity", "trust", "no clear need"],
                construct="adoption_barrier",
            ),
            SurveyQuestion(
                id="purchase_likelihood",
                prompt="How likely would you be to try or purchase this product?",
                type="single_choice",
                options=["very unlikely", "unlikely", "neutral", "likely", "very likely"],
                construct="purchase_likelihood",
            ),
            SurveyQuestion(
                id="open_feedback",
                prompt="Briefly explain what most influenced your reaction.",
                type="free_text",
                construct="open_feedback",
            ),
        ],
    )


def _registry() -> Dict[str, SurveyInstrument]:
    instruments = [_product_attitudes_v1()]
    return {instrument.id: instrument for instrument in instruments}


def list_survey_instruments() -> List[SurveyInstrument]:
    """Return all built-in survey instruments in stable display order."""
    registry = _registry()
    return [registry[DEFAULT_SURVEY_INSTRUMENT_ID]]


def get_survey_instrument(instrument_id: str) -> SurveyInstrument:
    """Return one built-in survey instrument, or raise ``KeyError``."""
    registry = _registry()
    try:
        return registry[instrument_id]
    except KeyError:
        raise KeyError("unknown survey instrument: {}".format(instrument_id))
