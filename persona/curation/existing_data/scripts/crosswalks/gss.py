#!/usr/bin/env python3
"""Crosswalk: General Social Survey (NORC GSS) → the exact/"observed" layer of the 1290 schema.

A second worked example for `crosswalk_engine.py`, alongside `crosswalks/prism.py` — this one shows
a *coded survey* (mostly clean rule-mapping, plus a couple of `compute` functions for numeric fields).
Because GSS is fully coded, the observed layer alone already yields a faithful 1290 record via
`run_pipeline.py --observed-only` (no LLM needed).

Source: raw NORC GSS variables with their standard value labels (lowercased) —
  `age` (numeric), `sex`, `marital`, `degree`, `race`, `region`, `relig`, `wrkstat`,
  `polviews`, `childs`.
Any label the map doesn't recognize falls through to `unmapped` → null (never guessed), so the
crosswalk is safe against release-to-release label variants; add variants to the maps to widen
coverage.

Faithful mapping choices (map value ``None`` = present-but-deliberately-unmapped → null):
  * `degree` "lt high school": spans no-formal…some-secondary with no single schema bucket → null.
  * `degree` "graduate": the schema splits Master's/Doctorate but GSS does not → mapped to the
    Master's floor (matches the choice already made in `crosswalks/prism.py`).
  * `race` "other" and `relig` "other": too coarse for the schema's buckets → null.
  * `relig` "none" is an *observed* answer (no religion) → the schema value `"None"`, not null.

Run ``python crosswalks/gss.py --selftest`` to check it against the engine.
"""

_US_CENSUS_REGIONS = {
    "new england",
    "middle atlantic",
    "e. nor. central",
    "w. nor. central",
    "south atlantic",
    "e. sou. central",
    "w. sou. central",
    "mountain",
    "pacific",
}


def _age_bracket(row):
    """GSS `age` (numeric; top-coded '89 or older') → schema age bracket."""
    a = row.get("age")
    if a is None:
        return None
    s = str(a).strip().lower()
    if not s or s in ("na", "no answer", "dk", "iap"):
        return None
    if "or older" in s or "89+" in s:  # GSS top-code → within 85+
        return "85+"
    try:
        a = int(float(s))
    except (TypeError, ValueError):
        return None
    for lo, hi, lab in (
        (18, 24, "18-24"),
        (25, 34, "25-34"),
        (35, 44, "35-44"),
        (45, 54, "45-54"),
        (55, 64, "55-64"),
        (65, 74, "65-74"),
        (75, 84, "75-84"),
    ):
        if lo <= a <= hi:
            return lab
    return "85+" if a >= 85 else None


def _children_count(row):
    """GSS `childs` (0–7, 'eight or more') → schema demo_children_count."""
    c = row.get("childs")
    if c is None:
        return None
    s = str(c).strip().lower()
    if "eight" in s or "8+" in s:
        return "3+ children"
    try:
        c = int(float(s))
    except (TypeError, ValueError):
        return None
    if c <= 0:
        return "None"
    if c == 1:
        return "1 child"
    if c == 2:
        return "2 children"
    return "3+ children"


def _region_us(row):
    """GSS `region` is US census divisions (+ 'foreign'); every US respondent → North America."""
    r = row.get("region")
    if r is None:
        return None
    s = str(r).strip().lower()
    if not s or "foreign" in s:
        return None
    return "North America" if s in _US_CENSUS_REGIONS else None


CROSSWALK = {
    "age_bracket": {"compute": _age_bracket, "prov": "observed"},
    "gender_identity": {
        "src": "sex",
        "map": {"male": "Man", "female": "Woman"},
        "prov": "observed",
    },
    "demo_marital_status": {
        "src": "marital",
        "map": {
            "married": "Married",
            "widowed": "Widowed",
            "divorced": "Divorced",
            "separated": "Separated",
            "never married": "Single",
        },
        "prov": "observed",
    },
    "highest_education": {
        "src": "degree",
        "map": {
            "lt high school": None,  # no faithful single bucket
            "less than high school": None,
            "high school": "Secondary",
            "junior college": "Associate's",
            "bachelor": "Bachelor's",
            "bachelor's": "Bachelor's",
            "graduate": "Master's",  # Master's floor (GSS can't split Doctorate)
        },
        "prov": "observed",
    },
    "demo_ethnicity_broad": {
        "src": "race",
        "map": {
            "white": "White / European",
            "black": "Black / African",
            "other": None,  # too coarse for the schema's regional buckets
        },
        "prov": "observed",
    },
    "region": {"compute": _region_us, "prov": "observed"},
    "demo_religion_affiliation": {
        "src": "relig",
        "map": {
            "protestant": "Christian",
            "catholic": "Christian",
            "christian": "Christian",
            "orthodox-christian": "Christian",
            "inter-nondenominational": "Christian",
            "jewish": "Jewish",
            "moslem/islam": "Muslim",
            "muslim": "Muslim",
            "buddhism": "Buddhist",
            "hinduism": "Hindu",
            "native american": "Folk / traditional",
            "none": "None",  # observed 'no religion' → schema value, not null
            "other": None,
            "other eastern": None,
            "other eastern religions": None,
        },
        "prov": "observed",
    },
    "demo_employment_status": {
        "src": "wrkstat",
        "map": {
            "working fulltime": "Full-time",
            "working full time": "Full-time",
            "working parttime": "Part-time",
            "working part time": "Part-time",
            "unempl, laid off": "Unemployed",
            "unemployed": "Unemployed",
            "retired": "Retired",
            "school": "Student",
            "in school": "Student",
            "keeping house": "Homemaker",
            "temp not working": None,  # ambiguous (still employed?) → null
            "other": None,
        },
        "prov": "observed",
    },
    "political_lean": {
        "src": "polviews",
        "map": {
            "extremely liberal": "Left",
            "liberal": "Left",
            "slightly liberal": "Center-left",
            "moderate": "Center",
            "slightly conservative": "Center-right",
            "conservative": "Right",
            "extremely conservative": "Right",
            "extrmly conservative": "Right",
        },
        "prov": "observed",
    },
    "demo_children_count": {"compute": _children_count, "prov": "observed"},
}


def _selftest():
    import os
    import sys

    sys.path.insert(
        0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )  # scripts/
    from crosswalk_engine import apply_crosswalk

    # mock allowed sets for the dims this example touches (real runs pass dimensions.json)
    allowed = {
        "age_bracket": {
            "18-24",
            "25-34",
            "35-44",
            "45-54",
            "55-64",
            "65-74",
            "75-84",
            "85+",
        },
        "gender_identity": {"Man", "Woman", "Non-binary"},
        "demo_marital_status": {
            "Single",
            "Married",
            "Divorced",
            "Separated",
            "Widowed",
        },
        "highest_education": {
            "Secondary",
            "Associate's",
            "Bachelor's",
            "Master's",
            "Doctorate",
        },
        "demo_ethnicity_broad": {
            "White / European",
            "Black / African",
            "Hispanic / Latino",
        },
        "region": {"North America"},
        "demo_religion_affiliation": {
            "Christian",
            "Jewish",
            "Muslim",
            "Buddhist",
            "Hindu",
            "Folk / traditional",
            "None",
        },
        "demo_employment_status": {
            "Full-time",
            "Part-time",
            "Unemployed",
            "Retired",
            "Student",
            "Homemaker",
        },
        "political_lean": {"Left", "Center-left", "Center", "Center-right", "Right"},
        "demo_children_count": {"None", "1 child", "2 children", "3+ children"},
    }

    # (a) a fully-answered respondent → clean observed values
    row = {
        "age": 42,
        "sex": "Female",
        "marital": "Never married",
        "degree": "Bachelor",
        "race": "White",
        "region": "Pacific",
        "relig": "None",
        "wrkstat": "Working fulltime",
        "polviews": "Slightly conservative",
        "childs": 2,
    }
    observed, prov, unmapped = apply_crosswalk(row, CROSSWALK, allowed)
    assert observed == {
        "age_bracket": "35-44",
        "gender_identity": "Woman",
        "demo_marital_status": "Single",
        "highest_education": "Bachelor's",
        "demo_ethnicity_broad": "White / European",
        "region": "North America",
        "demo_religion_affiliation": "None",  # observed 'no religion', not a null
        "demo_employment_status": "Full-time",
        "political_lean": "Center-right",
        "demo_children_count": "2 children",
    }, observed
    assert unmapped == {}, unmapped
    assert all(p == "observed" for p in prov.values())

    # (b) faithfulness: coarse / top-coded / unmapped inputs → null, never guessed
    coarse = {
        "age": "89 or older",
        "degree": "lt high school",
        "race": "other",
        "relig": "other eastern",
        "wrkstat": "temp not working",
        "region": "foreign",
        "childs": "eight or more",
    }
    obs2, _p2, um2 = apply_crosswalk(coarse, CROSSWALK, allowed)
    assert obs2 == {"age_bracket": "85+", "demo_children_count": "3+ children"}, obs2
    assert "highest_education" not in obs2  # 'lt high school' → null
    assert "demo_ethnicity_broad" not in obs2  # 'other' → null
    assert "demo_religion_affiliation" not in obs2  # 'other eastern' → null
    assert "region" not in obs2  # 'foreign' → null
    assert um2 == {}, um2  # all the above are deliberate None-maps, not misses

    # (c) an unrecognized label is recorded as unmapped (surfaced for review), stays null
    _, _, um3 = apply_crosswalk({"marital": "civil union"}, CROSSWALK, allowed)
    assert um3 == {"demo_marital_status": "civil union"}, um3

    print(
        f"gss crosswalk self-test: {len(CROSSWALK)} dims, mapping + faithfulness verified against engine ✅"
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(
        description="GSS example crosswalk for crosswalk_engine."
    )
    ap.add_argument(
        "--selftest",
        action="store_true",
        help="verify the crosswalk against the engine",
    )
    args = ap.parse_args()
    if args.selftest:
        _selftest()
    else:
        ap.print_help()
