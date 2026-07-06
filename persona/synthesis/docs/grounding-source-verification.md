# Persona Graph Grounding Source Verification

This document tracks verification notes for the grounding sources listed in
`grounding-sources.md`. The current focus is source-level verification and,
especially, dimension-level verification.

## Verification Levels

### Source-Level Verification

Source-level verification checks whether a source is credible and suitable as a
grounding reference.

For each source, record:

- Provider
- Official page
- Scope
- Data type
- Access type
- Notes
- Status

### Dimension-Level Verification

Dimension-level verification checks whether the listed sources actually support
the persona dimension area where they are cited.

For each dimension area, record:

- Dimension area
- Grounding claim
- Listed sources
- Evidence to look for
- Observed evidence
- Status

## Status Labels

- `Verified`: The source is official or credible, and its page clearly supports
  the dimension claim.
- `Needs review`: The source appears relevant, but the evidence or scope needs
  another pass.
- `Replace`: The source is weak, broken, not official enough, or not directly
  relevant to the dimension claim.
- `Remove`: The source should be removed from the grounding list.

## Dimension-Level Verification Notes

### Region / Population Distribution

Grounding claim: sources support population distribution by country, region,
or geography.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| UN World Population Prospects | Official population estimates/projections; country or area coverage; regional/global/national levels | The WPP page describes the dataset as official United Nations population estimates and projections, covering 237 countries or areas, with results at global, regional, national, subregional, and country/area levels. | Verified |
| UN Population Division Data Portal | Demographic indicators; location/country access; population theme | The Data Portal provides interactive access to global demographic indicators by indicator and location, including Population, Urbanization, and International Migration themes. | Verified |
| World Bank World Development Indicators | Country-level indicators; regional aggregates; population/demographic series | The WDI DataBank includes countries and regional aggregates such as World, South Asia, North America, Sub-Saharan Africa, and Europe & Central Asia. It provides indicator series by country and time. | Verified |
| WorldPop | Population distribution; spatial/geospatial demographic data; subnational population structure | WorldPop describes itself as open spatial demographic data and research, with high-resolution population distribution datasets, spatial demographics, and subnational age/sex structures. | Verified |
| Eurostat | European population statistics; demographic indicators; official EU statistics | Eurostat is the official EU statistics portal. Its key indicators include Population, and it provides databases and statistical themes for European data. | Verified, Europe-focused |

## Source-Level Verification Template

```text
Source:
Provider:
Official page:
Scope:
Data type:
Access type:
Supported dimensions:
Notes:
Status:
```

## Dimension-Level Verification Template

```text
Dimension area:
Grounding claim:
Sources:
- Source 1
- Source 2
- Source 3

Verification notes:
Source 1
- Evidence to look for:
- Observed evidence:
- Status:

Source 2
- Evidence to look for:
- Observed evidence:
- Status:
```

## Next Dimension Areas To Verify

- Age
- Sex / gender
- Urbanicity
- Education
- Employment / occupation / work
- Income / socioeconomic status
- Household / family / marital status
- Language / locale / culture
- Religion / religiosity
- Values / politics / trust / social attitudes
- Personality / psychometrics
- Health / disability / accessibility
- Lifestyle / time use / consumption
- Technology / internet access / digital behavior
- Developer / coding / technical tools
- Migration / citizenship / country of birth