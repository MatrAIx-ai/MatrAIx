#!/usr/bin/env python3
"""Build stable, finer semantic Stack Overflow extraction dimension chunks.

Source and output
-----------------
The authoritative input is ``persona/schema/dimensions.json``. The tracked
output is ``persona/human_extraction/schema/dimension_chunks_finer.jsonl``. Each
JSONL line is one self-contained, nested chunk object containing:

* a stable chunk ID, conceptual label, and description;
* source categories, size, ordered dimension IDs, and full source dimension
  metadata (including allowed values for later JSON Schema construction);
* an explicit semantic justification when its size is outside the preferred
  range; and
* nested manifest context with the source catalog hash, grouping policy,
  manifest version, chunk ordinal, and total chunk count.

Grouping policy
---------------
The reviewed ``GROUP_SPECS`` below use category as the primary signal, explicit
source-order ID spans or named ID sets for coherent subtopics, and deliberate
merges for small related categories. The target is 20 dimensions per chunk and
the preferred range is 15 through 24. A chunk outside that range is rejected
unless its group specification supplies a non-empty ``size_exception``.

Validation and determinism
--------------------------
Before rendering, the script validates catalog structure, IDs, indexes, value
sets, defaults, selector endpoints, chunk IDs, exact one-time coverage, and
size-exception policy. Dimensions retain authoritative index order inside each
chunk. JSON serialization and the source hash are canonical and contain no
timestamps, so identical inputs and grouping rules produce identical output.

Usage from the repository root
------------------------------
Write or refresh the tracked artifact::

    python persona/human_extraction/schema/prepare_dimension_chunks_finer.py

Validate the source and fail if the tracked JSONL is missing or stale::

    python persona/human_extraction/schema/prepare_dimension_chunks_finer.py --check

Validate and print the chunk summary without reading or writing the output::

    python persona/human_extraction/schema/prepare_dimension_chunks_finer.py --dry-run

``--source`` and ``--output`` may be supplied for explicit paths. This script
prepares the schema-first artifact consumed by the V3 Stack Overflow extractor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = REPO_ROOT / "persona" / "schema" / "dimensions.json"
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "persona"
    / "human_extraction"
    / "schema"
    / "dimension_chunks_finer.jsonl"
)
SOURCE_REPOSITORY_PATH = "persona/schema/dimensions.json"
MANIFEST_VERSION = "2.0"
TARGET_SIZE = 20
PREFERRED_MIN_SIZE = 15
PREFERRED_MAX_SIZE = 24
DIMENSION_ID_PATTERN = re.compile(r"[a-z][a-z0-9_]*\Z")


class ValidationError(ValueError):
    """Raised when the catalog, grouping rules, or manifest is invalid."""


@dataclass(frozen=True)
class Selector:
    """Select all, an inclusive source-order span, or named IDs in a category."""

    category: str
    start_id: str | None = None
    end_id: str | None = None
    dimension_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class GroupSpec:
    chunk_id: str
    label: str
    description: str
    selectors: tuple[Selector, ...]
    size_exception: str | None = None


def all_of(category: str) -> Selector:
    return Selector(category=category)


def span(category: str, start_id: str, end_id: str) -> Selector:
    return Selector(category=category, start_id=start_id, end_id=end_id)


def named(category: str, *dimension_ids: str) -> Selector:
    return Selector(category=category, dimension_ids=tuple(dimension_ids))


# These boundaries were reviewed against every ID, label, and description in
# the 1,290-dimension catalog.  Spans follow authoritative source order; named
# selections are used where source order does not follow the concept boundary.
_BASE_GROUP_SPECS: tuple[GroupSpec, ...] = (
    GroupSpec(
        "demographics_identity_household",
        "Identity, household, and cultural demographics",
        "Core identity, household composition, social position, and broad cultural background.",
        (
            all_of("Demographic: Core"),
            all_of("Demographic: Cultural"),
            all_of("Demographic: Family"),
        ),
    ),
    GroupSpec(
        "demographics_life_course",
        "Life course and formative events",
        "Life stage, mobility, adversity, relationships, and other formative experiences.",
        (all_of("Demographic: Life Events"),),
    ),
    GroupSpec(
        "languages_core_europe",
        "Language profile and European languages",
        "Overall language profile plus familiarity with European language families.",
        (
            named(
                "Linguistic: Language",
                "primary_language",
                "english_proficiency",
                "multilingualism",
                "lang_english",
                "lang_french",
                "lang_portuguese",
                "lang_russian",
                "lang_german",
                "lang_italian",
                "lang_turkish",
                "lang_dutch",
                "lang_polish",
                "lang_ukrainian",
                "lang_greek",
                "lang_czech",
                "lang_hungarian",
                "lang_romanian",
                "lang_swedish",
                "lang_norwegian",
                "lang_danish",
                "lang_finnish",
                "lang_serbian",
                "lang_croatian",
                "lang_bulgarian",
                "lang_slovak",
            ),
        ),
    ),
    GroupSpec(
        "languages_asia_africa",
        "Asian and African languages",
        "Familiarity with languages primarily associated with Asia and Africa.",
        (
            named(
                "Linguistic: Language",
                "lang_mandarin",
                "lang_cantonese",
                "lang_spanish",
                "lang_hindi",
                "lang_arabic",
                "lang_bengali",
                "lang_japanese",
                "lang_korean",
                "lang_vietnamese",
                "lang_thai",
                "lang_indonesian",
                "lang_malay",
                "lang_swahili",
                "lang_persian",
                "lang_hebrew",
                "lang_tagalog",
                "lang_urdu",
                "lang_tamil",
                "lang_telugu",
                "lang_marathi",
                "lang_punjabi",
                "lang_gujarati",
                "lang_hausa",
                "lang_yoruba",
                "lang_igbo",
                "lang_amharic",
                "lang_zulu",
                "lang_afrikaans",
            ),
        ),
    ),
    GroupSpec(
        "expertise_computing_data",
        "Computing and data expertise",
        "General expertise calibration, data fields, and core computing specialties.",
        (
            span("Expertise: Domains", "domain", "fam_data_science"),
            span("Expertise: Domains", "fam_cybersecurity", "fam_ux_research"),
        ),
    ),
    GroupSpec(
        "expertise_health_life_sciences",
        "Health and life-science expertise",
        "Clinical medicine, molecular life science, public health, and human performance.",
        (
            span("Expertise: Domains", "fam_cardiology", "fam_immunology"),
            span("Expertise: Domains", "fam_molecular_biology", "fam_physical_chemistry"),
            span("Expertise: Domains", "fam_agronomy", "fam_sports_science"),
        ),
    ),
    GroupSpec(
        "expertise_law_economics_business",
        "Law, economics, and business expertise",
        "Legal, financial, economic, marketing, operations, and management specialties.",
        (
            span("Expertise: Domains", "fam_constitutional_law", "fam_behavioral_economics"),
            span("Expertise: Domains", "fam_journalism", "fam_actuarial_science"),
        ),
    ),
    GroupSpec(
        "expertise_engineering_environment",
        "Engineering, physical science, and environment",
        "Engineering, physical and earth sciences, infrastructure, energy, and transport.",
        (
            span("Expertise: Domains", "fam_structural_engineering", "fam_control_systems"),
            span("Expertise: Domains", "fam_particle_physics", "fam_ecology"),
            span(
                "Expertise: Domains",
                "fam_geographic_information_systems",
                "fam_maritime_navigation",
            ),
        ),
    ),
    GroupSpec(
        "expertise_humanities_creative_service",
        "Humanities, creative, and service expertise",
        "Education, humanities, social science, design, creative production, and public service.",
        (
            span("Expertise: Domains", "fam_curriculum_design", "fam_pedagogy"),
            span("Expertise: Domains", "fam_sociology", "fam_landscape_design"),
            span("Expertise: Domains", "fam_graphic_design", "fam_typography"),
            span("Expertise: Domains", "fam_hospitality_management", "fam_3d_modeling"),
            span("Expertise: Domains", "fam_military_strategy", "fam_library_science"),
        ),
        "Keeping the connected humanities, creative-production, and service fields together is clearer than an arbitrary split.",
    ),
    GroupSpec(
        "personality_character_strengths",
        "Character strengths and dispositions",
        "Broad character traits, strengths, interpersonal virtues, and adaptive dispositions.",
        (all_of("Personality: Character"),),
    ),
    GroupSpec(
        "learning_academic_background",
        "Academic background and subjects",
        "Education level, institutional context, and familiarity with school subjects.",
        (all_of("Learning: Academic"),),
    ),
    GroupSpec(
        "industries_economy_infrastructure",
        "Industry context: economy and infrastructure",
        "Role context and industries spanning technology, finance, production, infrastructure, health, and hospitality.",
        (span("Professional: Industry", "company_size", "ind_media"),),
    ),
    GroupSpec(
        "industries_public_creative_services",
        "Industry context: public, creative, and services",
        "Media, public, transport, professional-service, consumer, sports, and arts industries.",
        (span("Professional: Industry", "ind_entertainment", "ind_fine_art"),),
    ),
    GroupSpec(
        "professional_developer_context",
        "Career and developer participation context",
        "Career stage, work setting, developer role, community participation, and open-source collaboration.",
        (
            all_of("Professional: Career"),
            all_of("Behavior: Work"),
            all_of("Developer: Professional Context"),
            all_of("Developer: Community Behavior"),
            all_of("Developer: Open Source Behavior"),
        ),
    ),
    GroupSpec(
        "psychology_decision_relational_state",
        "Decision, relational, and situational psychology",
        "Risk and closure tendencies, relational orientation, learning style, and current interaction state.",
        (
            all_of("Risk & Decision"),
            all_of("Personality: MBTI"),
            all_of("State: Emotional"),
            all_of("Learning: Style"),
            all_of("Personality: Relationships"),
            named("Worldview: Beliefs", "dospert_health_safety_risk_tolerance"),
        ),
    ),
    GroupSpec(
        "values_personal_priorities",
        "Personal values and priorities",
        "Everyday priorities covering family, achievement, freedom, community, ethics, and identity.",
        (span("Values & Motivation", "values_priority", "val_privacy"),),
    ),
    GroupSpec(
        "values_formal_constructs",
        "Formal value and motivation constructs",
        "Schwartz values, self-determination needs, need for cognition, and moral foundations.",
        (
            span("Values & Motivation", "schwartz_value_self_direction", "need_for_cognition"),
            span("Worldview: Beliefs", "mft_care_harm", "mft_liberty_oppression"),
        ),
    ),
    GroupSpec(
        "worldview_institutions_change",
        "Worldview: institutions and technological change",
        "Political, institutional, economic, scientific, and technology-related beliefs and attitudes.",
        (span("Worldview: Beliefs", "political_lean", "att_rapid_change"),),
    ),
    GroupSpec(
        "worldview_civic_consumer_life",
        "Worldview: civic and everyday life",
        "Attitudes about technology adoption, consumption, rights, work, transport, cities, and education.",
        (span("Worldview: Beliefs", "att_new_technology", "acad_political_theory"),),
    ),
    GroupSpec(
        "communication_cognitive_style",
        "Communication and cognitive style",
        "Tone plus reasoning, explanation, interaction, and response-style preferences.",
        (all_of("Linguistic: Communication"),),
        "The 35 tightly coupled cognitive-style axes and two communication context fields are more useful as one schema.",
    ),
    GroupSpec(
        "behavior_preferences_time",
        "Behavioral preferences and time orientation",
        "Media and accessibility preferences, pet peeves, trade-off preferences, and temporal habits.",
        (all_of("Behavior: Time"), all_of("Behavior: Preferences")),
        "Keeping the preference trade-offs with their closely related time-orientation axes avoids a tiny three-item chunk.",
    ),
    GroupSpec(
        "skills_communication_technical_management",
        "Communication, technical, and management skills",
        "Writing, speaking, software, analysis, leadership, reasoning, and language skills.",
        (span("Expertise: Skills", "skill_writing", "skill_interpretation"),),
    ),
    GroupSpec(
        "skills_creative_practical_applied",
        "Creative, practical, and applied skills",
        "Design and media craft, household and financial skills, learning, facilitation, and commercial skills.",
        (span("Expertise: Skills", "skill_design_thinking", "skill_selling"),),
    ),
    GroupSpec(
        "tools_data_productivity_business",
        "Data, productivity, and business tools",
        "Data analysis, knowledge work, collaboration, CRM, enterprise, document, and planning tools.",
        (
            named(
                "Skills: Tools",
                "tool_excel", "tool_google_sheets", "tool_python", "tool_r", "tool_sql",
                "tool_tableau", "tool_power_bi", "tool_looker", "tool_notion", "tool_obsidian",
                "tool_jira", "tool_linear", "tool_slack", "tool_microsoft_teams", "tool_salesforce",
                "tool_hubspot", "tool_sap", "tool_oracle_erp", "tool_word", "tool_powerpoint",
                "tool_keynote", "tool_trello", "tool_asana",
            ),
        ),
    ),
    GroupSpec(
        "tools_software_cloud_development",
        "Software, cloud, and development tools",
        "Source control, infrastructure, cloud, IDE, statistics, game, web, and API development tools.",
        (
            named(
                "Skills: Tools",
                "tool_git", "tool_github", "tool_gitlab", "tool_docker", "tool_kubernetes",
                "tool_terraform", "tool_aws", "tool_azure", "tool_google_cloud", "tool_vs_code",
                "tool_jetbrains_ides", "tool_vim", "tool_jupyter", "tool_matlab", "tool_stata",
                "tool_spss", "tool_sas", "tool_linux_cli", "tool_unity", "tool_unreal_engine",
                "tool_wordpress", "tool_webflow", "tool_postman",
            ),
        ),
    ),
    GroupSpec(
        "tools_design_commerce_ai",
        "Design, commerce, and AI tools",
        "Creative design and engineering, commerce and finance, communication, AI, and automation tools.",
        (
            named(
                "Skills: Tools",
                "tool_figma", "tool_sketch", "tool_photoshop", "tool_illustrator", "tool_indesign",
                "tool_after_effects", "tool_premiere_pro", "tool_canva", "tool_blender", "tool_autocad",
                "tool_solidworks", "tool_revit", "tool_shopify", "tool_stripe", "tool_quickbooks",
                "tool_xero", "tool_zoom", "tool_airtable", "tool_chatgpt", "tool_claude",
                "tool_github_copilot", "tool_midjourney", "tool_zapier",
            ),
        ),
    ),
    GroupSpec(
        "interests_society_technology_life",
        "Interests: society, technology, and daily life",
        "Public affairs, science, finance, family, home, transport, and active-life interests.",
        (span("Interests: Topics", "topic_politics", "topic_running"),),
    ),
    GroupSpec(
        "interests_arts_spiritual_outdoors_games",
        "Interests: arts, spirituality, outdoors, and games",
        "Visual and performing arts, literature, belief, contemplative practice, nature, and games.",
        (span("Interests: Topics", "topic_photography", "topic_social_media"),),
    ),
    GroupSpec(
        "interests_community_craft_growth",
        "Interests: community, craft, and personal growth",
        "Community and environment, food and drink, making, emerging technology, entrepreneurship, and growth.",
        (span("Interests: Topics", "topic_volunteering", "topic_mindfulness"),),
    ),
    GroupSpec(
        "culture_country_familiarity",
        "Country and regional cultural familiarity",
        "Familiarity with the catalog's country and regional cultures.",
        (span("Interests: Culture", "cult_united_states", "cult_portugal"),),
        "The forty parallel country-culture fields form one indivisible lookup concept and are clearer together.",
    ),
    GroupSpec(
        "lifestyle_consumption_routines",
        "Lifestyle, consumption, and routines",
        "Daily consumption, planning, media, finance, devices, travel, hobbies, and volunteering patterns.",
        (span("Interests: Culture", "lstyle_smoking", "lstyle_volunteering"),),
    ),
    GroupSpec(
        "media_music_genres",
        "Music genre interests",
        "Interest across popular, traditional, regional, electronic, and specialist music genres.",
        (span("Interests: Media", "musg_pop", "musg_bollywood"),),
    ),
    GroupSpec(
        "media_film_genres",
        "Film genre interests",
        "Interest across mainstream, genre, independent, historical, and art-house film.",
        (span("Interests: Media", "filmg_action", "filmg_disaster"),),
    ),
    GroupSpec(
        "media_book_genres",
        "Book genre interests",
        "Interest across fiction, nonfiction, poetry, graphic, travel, culinary, and essay forms.",
        (span("Interests: Media", "bookg_literary_fiction", "bookg_essays"),),
    ),
    GroupSpec(
        "food_cuisine_interests",
        "Cuisine and food interests",
        "Interest in regional cuisines and dietary or specialty food traditions.",
        (all_of("Interests: Food"),),
    ),
    GroupSpec(
        "sports_interests",
        "Sports and physical-activity interests",
        "Interest across team, individual, combat, outdoor, strength, mind-body, and precision sports.",
        (all_of("Interests: Sports"),),
        "The forty parallel sport-interest fields form one cohesive inventory and do not have a principled split.",
    ),
    GroupSpec(
        "personality_big_five_facets",
        "Big Five facets",
        "The catalog's original thirty Big Five facet-level traits.",
        (span("Personality: Big Five", "big5_imagination", "big5_vulnerability"),),
    ),
    GroupSpec(
        "personality_bfi2",
        "BFI-2 domains and facets",
        "The five BFI-2 domains and fifteen associated facet scores.",
        (span("Personality: Big Five", "bfi2_domain_extraversion", "bfi2_facet_creative_imagination"),),
    ),
    GroupSpec(
        "health_physical_fitness_lifestyle",
        "Physical health, fitness, and health lifestyle",
        "General, sensory, mobility, mental, accessibility, fitness, diet, and substance-use health context.",
        (
            all_of("Health: Fitness"),
            all_of("Health: Lifestyle"),
            all_of("Health: Physical"),
        ),
    ),
    GroupSpec(
        "hobbies_crafts_collecting_nature",
        "Hobbies: crafts, collecting, and nature",
        "Textile and material crafts, collecting, gardening, animal keeping, observation, and geocaching.",
        (span("Interests: Hobbies", "hob_knitting", "hob_rock_climbing"),),
    ),
    GroupSpec(
        "hobbies_adventure_food_performance",
        "Hobbies: adventure, food, and performance",
        "Outdoor adventure, food craft, dance and performance, visual making, genealogy, and cosplay.",
        (span("Interests: Hobbies", "hob_bouldering", "hob_cosplay"),),
    ),
    GroupSpec(
        "behavior_habits",
        "Recurring habits and self-management",
        "Routine practices involving reflection, planning, food, health, devices, organization, and communication.",
        (all_of("Behavior: Habits"),),
    ),
    GroupSpec(
        "code_style_maintenance",
        "Code style, quality, and maintenance",
        "Code-writing conventions, structure, testing, maintenance, debugging, security, and onboarding.",
        (
            span("Skills: Programming", "code_comment_style", "code_refactoring_frequency"),
            named("Professional: Industry", "code_function_length"),
            all_of("Developer: Code Maintenance"),
        ),
    ),
    GroupSpec(
        "programming_languages",
        "Programming language proficiency",
        "Proficiency across general-purpose, systems, functional, data, shell, legacy, and query languages.",
        (span("Skills: Programming", "prog_python", "prog_graphql"),),
    ),
    GroupSpec(
        "developer_ai_tools_workflows",
        "Developer AI adoption, agents, and workflows",
        "AI and agent adoption, task fit, trust and control, workflow impact, and technology evaluation criteria.",
        (
            all_of("Developer: AI Adoption"),
            all_of("Developer: Agent Adoption"),
            all_of("Developer: AI Workflow Tasks"),
            all_of("Developer: Technology Evaluation"),
        ),
        "These thirty-nine fields jointly describe one developer-AI adoption model; separating evaluation from use would weaken it.",
    ),
)


# The finer policy preserves every reviewed base group below 25 dimensions,
# keeps five indivisible 25-item inventories with explicit exceptions, and
# replaces only the larger groups with the semantic subdivisions below.
_FINER_REPLACEMENTS: dict[str, tuple[GroupSpec, ...]] = {
    "demographics_identity_household": (
        GroupSpec(
            "demographics_identity_culture",
            "Identity and cultural demographics",
            "Identity, social position, cultural background, and broad demographic context.",
            (
                named(
                    "Demographic: Core",
                    "age_bracket",
                    "region",
                    "gender_identity",
                    "urbanicity",
                    "socioeconomic_band",
                    "register",
                    "att_traditional_gender_roles",
                    "demo_generation",
                    "demo_religion_affiliation",
                    "demo_sexual_orientation",
                    "demo_citizenship_status",
                    "demo_ethnicity_broad",
                    "demo_disability_status",
                ),
                all_of("Demographic: Cultural"),
            ),
        ),
        GroupSpec(
            "demographics_household_social_context",
            "Household and social context",
            "Household composition, employment and housing context, family position, and civic life.",
            (
                named(
                    "Demographic: Core",
                    "demo_marital_status",
                    "demo_children_count",
                    "demo_household_income",
                    "demo_employment_status",
                    "demo_housing_status",
                    "demo_veteran_status",
                    "demo_birth_order",
                    "demo_home_language",
                    "demo_political_engagement",
                    "demo_parental_status",
                    "demo_relationship_length",
                    "demo_driver_status",
                ),
                all_of("Demographic: Family"),
            ),
            "These thirteen tightly related household and social-context fields form a coherent unit that should not be padded with identity fields.",
        ),
    ),
    "languages_asia_africa": (
        GroupSpec(
            "languages_asian",
            "Asian languages",
            "Familiarity with East, Southeast, and South Asian languages.",
            (
                named(
                    "Linguistic: Language",
                    "lang_mandarin",
                    "lang_cantonese",
                    "lang_hindi",
                    "lang_bengali",
                    "lang_japanese",
                    "lang_korean",
                    "lang_vietnamese",
                    "lang_thai",
                    "lang_indonesian",
                    "lang_malay",
                    "lang_tagalog",
                    "lang_urdu",
                    "lang_tamil",
                    "lang_telugu",
                    "lang_marathi",
                    "lang_punjabi",
                    "lang_gujarati",
                ),
            ),
        ),
        GroupSpec(
            "languages_african_middle_eastern_global",
            "African, Middle Eastern, and other global languages",
            "Familiarity with African and Middle Eastern languages plus Spanish from the source grouping.",
            (
                named(
                    "Linguistic: Language",
                    "lang_spanish",
                    "lang_arabic",
                    "lang_swahili",
                    "lang_persian",
                    "lang_hebrew",
                    "lang_hausa",
                    "lang_yoruba",
                    "lang_igbo",
                    "lang_amharic",
                    "lang_zulu",
                    "lang_afrikaans",
                ),
            ),
            "These eleven remaining language-familiarity fields are semantically clearer together than when padded with unrelated dimensions.",
        ),
    ),
    "expertise_law_economics_business": (
        GroupSpec(
            "expertise_law_finance_economics",
            "Law, finance, and economics expertise",
            "Legal fields, finance, accounting, auditing, and economic disciplines.",
            (span("Expertise: Domains", "fam_constitutional_law", "fam_behavioral_economics"),),
            "The twelve law, finance, and economics fields form a complete disciplinary cluster and should remain separate from operating functions.",
        ),
        GroupSpec(
            "expertise_business_operations",
            "Business and operations expertise",
            "Communications, marketing, sales, operations, management, investment, property, and risk fields.",
            (span("Expertise: Domains", "fam_journalism", "fam_actuarial_science"),),
        ),
    ),
    "expertise_engineering_environment": (
        GroupSpec(
            "expertise_engineering_materials_energy",
            "Engineering, materials, and energy expertise",
            "Core engineering disciplines plus physical science, advanced materials, energy, and extraction fields.",
            (
                named(
                    "Expertise: Domains",
                    "fam_structural_engineering",
                    "fam_mechanical_engineering",
                    "fam_electrical_engineering",
                    "fam_civil_engineering",
                    "fam_chemical_engineering",
                    "fam_aerospace_engineering",
                    "fam_robotics",
                    "fam_control_systems",
                    "fam_particle_physics",
                    "fam_materials_science",
                    "fam_nanotechnology",
                    "fam_renewable_energy",
                    "fam_nuclear_engineering",
                    "fam_petroleum_engineering",
                    "fam_mining",
                ),
            ),
        ),
        GroupSpec(
            "expertise_earth_environment_transport",
            "Earth, environment, and transport expertise",
            "Space, earth, ocean, climate, ecology, natural-resource, aviation, and maritime fields.",
            (
                named(
                    "Expertise: Domains",
                    "fam_astrophysics",
                    "fam_astronomy",
                    "fam_geology",
                    "fam_oceanography",
                    "fam_climate_science",
                    "fam_ecology",
                    "fam_geographic_information_systems",
                    "fam_meteorology",
                    "fam_forestry",
                    "fam_marine_biology",
                    "fam_paleontology",
                    "fam_aviation",
                    "fam_maritime_navigation",
                ),
            ),
            "These thirteen earth, environmental, and transport fields form a coherent natural-systems cluster that should not be padded arbitrarily.",
        ),
    ),
    "expertise_humanities_creative_service": (
        GroupSpec(
            "expertise_humanities_social_sciences",
            "Humanities and social-science expertise",
            "Education, social science, humanities, arts scholarship, architecture, and planning.",
            (
                named(
                    "Expertise: Domains",
                    "fam_curriculum_design",
                    "fam_pedagogy",
                    "fam_sociology",
                    "fam_psychology",
                    "fam_cognitive_science",
                    "fam_anthropology",
                    "fam_international_relations",
                    "fam_comparative_literature",
                    "fam_philosophy",
                    "fam_ethics",
                    "fam_history",
                    "fam_archaeology",
                    "fam_linguistics",
                    "fam_art_history",
                    "fam_music_theory",
                    "fam_film_studies",
                    "fam_architecture",
                    "fam_urban_planning",
                    "fam_landscape_design",
                ),
            ),
        ),
        GroupSpec(
            "expertise_creative_service_fields",
            "Creative production and service expertise",
            "Design, hospitality, culinary, media-production, public-service, belief, and information fields.",
            (
                named(
                    "Expertise: Domains",
                    "fam_graphic_design",
                    "fam_industrial_design",
                    "fam_typography",
                    "fam_hospitality_management",
                    "fam_culinary_arts",
                    "fam_sommelier_knowledge",
                    "fam_fashion_design",
                    "fam_textiles",
                    "fam_photography",
                    "fam_cinematography",
                    "fam_music_production",
                    "fam_sound_engineering",
                    "fam_animation",
                    "fam_3d_modeling",
                    "fam_military_strategy",
                    "fam_diplomacy",
                    "fam_social_work",
                    "fam_counseling",
                    "fam_theology",
                    "fam_library_science",
                ),
            ),
        ),
    ),
    "personality_character_strengths": (
        GroupSpec(
            "personality_character_intellectual_interpersonal",
            "Intellectual, courage, and interpersonal strengths",
            "Broad stance plus intellectual, courage, relationship, teamwork, fairness, and leadership strengths.",
            (span("Personality: Character", "domain_characteristics", "trait_leadership"),),
        ),
        GroupSpec(
            "personality_character_self_management_transcendence",
            "Self-management and transcendent strengths",
            "Temperance, appreciation, hope, spirituality, ambition, resilience, loyalty, and adaptability.",
            (span("Personality: Character", "trait_forgiveness", "trait_adaptability"),),
        ),
    ),
    "learning_academic_background": (
        GroupSpec(
            "learning_academic_stem_economics",
            "Academic context, STEM, and economics",
            "Educational background and familiarity with quantitative, scientific, computing, and economics subjects.",
            (span("Learning: Academic", "highest_education", "acad_economics"),),
        ),
        GroupSpec(
            "learning_humanities_social_applied",
            "Humanities, social, and applied subjects",
            "Social science, humanities, arts, physical education, health, business, environment, and logic subjects.",
            (span("Learning: Academic", "acad_psychology", "acad_anthropology"),),
        ),
    ),
    "values_personal_priorities": (
        GroupSpec(
            "values_security_achievement",
            "Security, achievement, and personal priorities",
            "Family, work, material security, health, achievement, growth, enjoyment, order, and privacy priorities.",
            (
                named(
                    "Values & Motivation",
                    "values_priority",
                    "economic_motivation",
                    "val_family",
                    "val_career_success",
                    "val_wealth",
                    "val_health",
                    "val_security_stability",
                    "val_adventure",
                    "val_power_influence",
                    "val_achievement",
                    "val_social_status",
                    "val_recognition",
                    "val_personal_growth",
                    "val_fun_enjoyment",
                    "val_order_structure",
                    "val_privacy",
                ),
            ),
        ),
        GroupSpec(
            "values_expression_social_principles",
            "Expression, social, and principled values",
            "Freedom, tradition, creativity, community, spirituality, truth, justice, loyalty, sustainability, and equality.",
            (
                named(
                    "Values & Motivation",
                    "religiosity",
                    "val_personal_freedom",
                    "val_tradition",
                    "val_creativity_self_expression",
                    "val_community",
                    "val_spirituality_faith",
                    "val_knowledge_truth",
                    "val_independence",
                    "val_justice_fairness",
                    "val_loyalty",
                    "val_sustainability",
                    "val_helping_others",
                    "val_integrity_honesty",
                    "val_beauty_aesthetics",
                    "val_patriotism",
                    "val_equality",
                ),
            ),
        ),
    ),
    "worldview_institutions_change": (
        GroupSpec(
            "worldview_institutions_technology",
            "Institutions, technology, and public policy",
            "Political and institutional orientation plus technology, work, markets, regulation, and climate attitudes.",
            (span("Worldview: Beliefs", "political_lean", "att_climate_action"),),
        ),
        GroupSpec(
            "worldview_science_economy_change",
            "Science, economy, authority, and change",
            "Energy, medicine, religion, finance, labor, education, risk, authority, and social-change attitudes.",
            (span("Worldview: Beliefs", "att_nuclear_energy", "att_rapid_change"),),
        ),
    ),
    "worldview_civic_consumer_life": (
        GroupSpec(
            "worldview_consumer_technology",
            "Consumer and technology worldview",
            "Technology adoption, brands, media, consumption, mobility, exploration, and lifestyle attitudes.",
            (span("Worldview: Beliefs", "att_new_technology", "att_fast_fashion"),),
        ),
        GroupSpec(
            "worldview_civic_work_life",
            "Civic, work, and everyday-life worldview",
            "Rights, justice, supply chains, workplace, education, transport, cities, and political theory.",
            (span("Worldview: Beliefs", "att_gun_ownership", "acad_political_theory"),),
        ),
    ),
    "communication_cognitive_style": (
        GroupSpec(
            "communication_expression_interaction",
            "Communication expression and interaction",
            "Tone, formality, directness, emotion, conflict, feedback, and ambiguity in communication.",
            (span("Linguistic: Communication", "tone_expected", "cog_ambiguity_tolerance"),),
        ),
        GroupSpec(
            "communication_reasoning_response_style",
            "Reasoning and response style",
            "Work habits, attention, learning, decisions, modality, framing, empathy, storytelling, and language precision.",
            (span("Linguistic: Communication", "cog_perfectionism", "cog_politeness"),),
        ),
    ),
    "behavior_preferences_time": (
        GroupSpec(
            "behavior_context_pet_peeves",
            "Behavioral context and pet peeves",
            "Time, modality, accessibility, media, sleep context, and recurring sources of irritation.",
            (
                all_of("Behavior: Time"),
                span("Behavior: Preferences", "modality_pref", "peeve_paywalls"),
            ),
        ),
        GroupSpec(
            "behavior_preference_tradeoffs",
            "Behavioral preference trade-offs",
            "Work, planning, environment, quality, decision, communication, novelty, and change preferences.",
            (span("Behavior: Preferences", "pref_team_vs_solo", "pref_stability_vs_change"),),
        ),
    ),
    "skills_communication_technical_management": (
        GroupSpec(
            "skills_communication_technical",
            "Communication, technical, and analytical skills",
            "Writing and speaking plus software, data, statistical, spreadsheet, and financial modeling skills.",
            (span("Expertise: Skills", "skill_writing", "skill_financial_modeling"),),
        ),
        GroupSpec(
            "skills_management_reasoning_language",
            "Management, reasoning, and language skills",
            "Strategy, leadership, collaboration, research, reasoning, mathematics, and language mediation skills.",
            (span("Expertise: Skills", "skill_project_management", "skill_interpretation"),),
        ),
    ),
    "skills_creative_practical_applied": (
        GroupSpec(
            "skills_creative_practical",
            "Creative and practical skills",
            "Design and media craft plus cooking, finance, repair, gardening, and driving skills.",
            (span("Expertise: Skills", "skill_design_thinking", "skill_driving"),),
        ),
        GroupSpec(
            "skills_applied_commercial",
            "Applied knowledge and commercial skills",
            "Learning, listening, facilitation, forecasting, verification, presentation, networking, and selling skills.",
            (span("Expertise: Skills", "skill_technical_writing", "skill_selling"),),
        ),
    ),
    "interests_arts_spiritual_outdoors_games": (),
    "interests_community_craft_growth": (),
    "culture_country_familiarity": (
        GroupSpec(
            "culture_americas_europe_oceania",
            "Cultures of the Americas, Europe, and Oceania",
            "Familiarity with cultures across the Americas, Europe, Russia and Turkey, Australia, and New Zealand.",
            (
                named(
                    "Interests: Culture",
                    "cult_united_states",
                    "cult_canada",
                    "cult_mexico",
                    "cult_brazil",
                    "cult_argentina",
                    "cult_united_kingdom",
                    "cult_france",
                    "cult_germany",
                    "cult_italy",
                    "cult_spain",
                    "cult_netherlands",
                    "cult_sweden",
                    "cult_poland",
                    "cult_russia",
                    "cult_turkey",
                    "cult_australia",
                    "cult_new_zealand",
                    "cult_greece",
                    "cult_portugal",
                ),
            ),
        ),
        GroupSpec(
            "culture_africa_middle_east_asia",
            "Cultures of Africa, the Middle East, and Asia",
            "Familiarity with cultures across Africa, the Middle East, South Asia, East Asia, and Southeast Asia.",
            (
                named(
                    "Interests: Culture",
                    "cult_egypt",
                    "cult_saudi_arabia",
                    "cult_uae",
                    "cult_israel",
                    "cult_iran",
                    "cult_nigeria",
                    "cult_kenya",
                    "cult_south_africa",
                    "cult_ethiopia",
                    "cult_india",
                    "cult_pakistan",
                    "cult_bangladesh",
                    "cult_china",
                    "cult_japan",
                    "cult_south_korea",
                    "cult_vietnam",
                    "cult_thailand",
                    "cult_indonesia",
                    "cult_philippines",
                    "cult_singapore",
                    "cult_malaysia",
                ),
            ),
        ),
    ),
    "lifestyle_consumption_routines": (
        GroupSpec(
            "lifestyle_daily_consumption_routines",
            "Daily consumption and routines",
            "Consumption, travel, pets, time use, social energy, planning, organization, giving, news, reading, and gaming.",
            (span("Interests: Culture", "lstyle_smoking", "lstyle_gaming_freq"),),
        ),
        GroupSpec(
            "lifestyle_media_finance_identity",
            "Media, finance, devices, and lifestyle identity",
            "Streaming and audio, communication platforms, devices, payments, finance, subscriptions, style, hobbies, travel, and volunteering.",
            (span("Interests: Culture", "lstyle_streaming_hours", "lstyle_volunteering"),),
        ),
    ),
    "media_music_genres": (
        GroupSpec(
            "media_music_mainstream_traditional",
            "Mainstream, traditional, and roots music",
            "Popular, rock, hip-hop, R&B, jazz, classical, country, folk, reggae, guitar, gospel, soul, and roots genres.",
            (
                named(
                    "Interests: Media",
                    "musg_pop",
                    "musg_rock",
                    "musg_hip_hop",
                    "musg_r_b",
                    "musg_jazz",
                    "musg_blues",
                    "musg_classical",
                    "musg_opera",
                    "musg_country",
                    "musg_folk",
                    "musg_reggae",
                    "musg_reggaeton",
                    "musg_metal",
                    "musg_punk",
                    "musg_indie",
                    "musg_gospel",
                    "musg_soul",
                    "musg_bluegrass",
                ),
            ),
        ),
        GroupSpec(
            "media_music_electronic_global_specialty",
            "Electronic, global, and specialty music",
            "Dance and electronic styles plus East Asian, Latin, African, funk, ambient, retro, trap, and film-associated genres.",
            (
                named(
                    "Interests: Media",
                    "musg_electronic",
                    "musg_house",
                    "musg_techno",
                    "musg_trance",
                    "musg_drum_bass",
                    "musg_k_pop",
                    "musg_j_pop",
                    "musg_latin",
                    "musg_afrobeats",
                    "musg_funk",
                    "musg_disco",
                    "musg_ambient",
                    "musg_lo_fi",
                    "musg_ska",
                    "musg_synthwave",
                    "musg_trap",
                    "musg_bollywood",
                ),
            ),
        ),
    ),
    "food_cuisine_interests": (
        GroupSpec(
            "food_europe_americas_dietary",
            "European, American, and dietary food interests",
            "European and American cuisines plus Caribbean, Russian, dietary, and seafood traditions.",
            (
                named(
                    "Interests: Food",
                    "cuis_italian",
                    "cuis_french",
                    "cuis_spanish",
                    "cuis_greek",
                    "cuis_mexican",
                    "cuis_peruvian",
                    "cuis_brazilian",
                    "cuis_american_bbq",
                    "cuis_southern_soul_food",
                    "cuis_cajun",
                    "cuis_caribbean",
                    "cuis_german",
                    "cuis_scandinavian",
                    "cuis_russian",
                    "cuis_spanish_tapas",
                    "cuis_vegan",
                    "cuis_vegetarian",
                    "cuis_seafood",
                ),
            ),
        ),
        GroupSpec(
            "food_asia_middle_east_africa",
            "Asian, Middle Eastern, and African food interests",
            "East, Southeast, and South Asian cuisines plus Middle Eastern and African traditions and specialties.",
            (
                named(
                    "Interests: Food",
                    "cuis_chinese",
                    "cuis_sichuan",
                    "cuis_cantonese",
                    "cuis_japanese",
                    "cuis_korean",
                    "cuis_thai",
                    "cuis_vietnamese",
                    "cuis_indian",
                    "cuis_pakistani",
                    "cuis_middle_eastern",
                    "cuis_lebanese",
                    "cuis_turkish",
                    "cuis_moroccan",
                    "cuis_ethiopian",
                    "cuis_nigerian",
                    "cuis_sushi",
                    "cuis_ramen",
                ),
            ),
        ),
    ),
    "sports_interests": (
        GroupSpec(
            "sports_team_endurance_action",
            "Team, endurance, combat, and action sports",
            "Team and racket sports, endurance activities, combat sports, winter sports, surfing, and skating.",
            (span("Interests: Sports", "sport_soccer", "sport_skateboarding"),),
        ),
        GroupSpec(
            "sports_individual_strength_precision",
            "Individual, strength, mind-body, and precision sports",
            "Climbing, gymnastics, track, racket and water sports, martial arts, strength, esports, and precision activities.",
            (span("Interests: Sports", "sport_climbing", "sport_triathlon"),),
        ),
    ),
    "personality_big_five_facets": (
        GroupSpec(
            "personality_big_five_openness_conscientiousness",
            "Big Five openness and conscientiousness facets",
            "The six openness facets and six conscientiousness facets from the original Big Five inventory.",
            (span("Personality: Big Five", "big5_imagination", "big5_cautiousness"),),
            "These twelve facets preserve two complete Big Five domains and should not be mixed with a partial third domain merely to reach fifteen.",
        ),
        GroupSpec(
            "personality_big_five_social_emotional",
            "Big Five social and emotional facets",
            "The extraversion, agreeableness, and neuroticism facet families.",
            (span("Personality: Big Five", "big5_friendliness", "big5_vulnerability"),),
        ),
    ),
    "health_physical_fitness_lifestyle": (
        GroupSpec(
            "health_general_functioning_wellbeing",
            "General functioning and wellbeing",
            "Fitness and lifestyle context plus general, sensory, mobility, mental-health, stress, energy, and sleep status.",
            (
                all_of("Health: Fitness"),
                all_of("Health: Lifestyle"),
                span("Health: Physical", "health_general_health", "health_sleep_quality"),
            ),
        ),
        GroupSpec(
            "health_management_accessibility",
            "Health management and accessibility",
            "Pain, medication, dietary needs, neurodivergence, caregiving, health access, capacity, and accessibility requirements.",
            (span("Health: Physical", "health_pain_level", "health_attention_condition"),),
            "These fourteen health-management and accessibility fields form one actionable support cluster and should remain together.",
        ),
    ),
    "behavior_habits": (
        GroupSpec(
            "behavior_habits_intentional_routines",
            "Intentional routines and self-management habits",
            "Reflection, planning, tracking, preparation, movement, downtime, gratitude, reading, rest, and meal habits.",
            (span("Behavior: Habits", "habit_journaling", "habit_skipping_breakfast"),),
        ),
        GroupSpec(
            "behavior_habits_incidental_digital",
            "Incidental, digital, and maintenance habits",
            "Fidgeting, scrolling, browsing, inbox and receipt practices, travel preparation, expressive habits, health tracking, backups, and cleaning.",
            (span("Behavior: Habits", "habit_late_night_snacking", "habit_procrasti_cleaning"),),
        ),
    ),
    "programming_languages": (
        GroupSpec(
            "programming_languages_mainstream_application",
            "Mainstream and application programming languages",
            "Widely used application, web, mobile, systems, scripting, and concurrent programming languages.",
            (span("Skills: Programming", "prog_python", "prog_erlang"),),
        ),
        GroupSpec(
            "programming_languages_functional_data_systems",
            "Functional, data, systems, and query languages",
            "Functional and scientific languages plus data, shell, systems, legacy, smart-contract, and query languages.",
            (span("Skills: Programming", "prog_clojure", "prog_graphql"),),
        ),
    ),
    "developer_ai_tools_workflows": (
        GroupSpec(
            "developer_ai_agent_adoption",
            "Developer AI and agent adoption",
            "AI and coding-agent use, sentiment, trust, learning, autonomy, control, context, security, memory, and workflow impact.",
            (
                all_of("Developer: AI Adoption"),
                all_of("Developer: Agent Adoption"),
            ),
        ),
        GroupSpec(
            "developer_ai_tasks_tool_evaluation",
            "Developer AI tasks and tool evaluation",
            "AI task fit plus reliability, openness, security, ethics, alternatives, and obsolescence criteria for coding tools.",
            (
                all_of("Developer: AI Workflow Tasks"),
                all_of("Developer: Technology Evaluation"),
            ),
        ),
    ),
}


_RETAINED_25_EXCEPTIONS = {
    "languages_core_europe": (
        "These twenty-five core profile and European language fields remain one reviewed inventory; splitting them would create two undersized fragments."
    ),
    "industries_economy_infrastructure": (
        "These twenty-five economy and infrastructure industry fields remain one reviewed inventory; splitting them would weaken the shared employment context."
    ),
    "industries_public_creative_services": (
        "These twenty-five public, creative, and service industry fields remain one reviewed inventory; splitting them would create arbitrary boundaries."
    ),
    "hobbies_crafts_collecting_nature": (
        "These twenty-five craft, collecting, and nature hobbies remain one reviewed inventory; splitting them would create undersized fragments."
    ),
    "hobbies_adventure_food_performance": (
        "These twenty-five adventure, food, and performance hobbies remain one reviewed inventory; splitting them would create undersized fragments."
    ),
}


_TOPIC_INTEREST_REPLACEMENTS: tuple[GroupSpec, ...] = (
    GroupSpec(
        "interests_arts_media_performance",
        "Interests in arts, media, and performance",
        "Visual and narrative media, music, literature, cultural subjects, audio and social media, dance, comedy, and performance.",
        (
            named(
                "Interests: Topics",
                "topic_photography",
                "topic_film",
                "topic_tv_series",
                "topic_anime",
                "topic_comics",
                "topic_music",
                "topic_live_concerts",
                "topic_theater",
                "topic_visual_art",
                "topic_literature",
                "topic_poetry",
                "topic_history",
                "topic_philosophy",
                "topic_true_crime",
                "topic_podcasts",
                "topic_social_media",
                "topic_dance",
                "topic_stand_up_comedy",
                "topic_magic_tricks",
            ),
        ),
    ),
    GroupSpec(
        "interests_spiritual_outdoors_games_community",
        "Interests in spirituality, outdoors, games, and community",
        "Belief and contemplative practices, nature, tabletop and strategy games, civic involvement, environment, astronomy, and growth.",
        (
            named(
                "Interests: Topics",
                "topic_religion",
                "topic_meditation",
                "topic_yoga",
                "topic_hiking",
                "topic_camping",
                "topic_fishing",
                "topic_birdwatching",
                "topic_board_games",
                "topic_tabletop_rpgs",
                "topic_puzzles",
                "topic_chess",
                "topic_astrology",
                "topic_volunteering",
                "topic_activism",
                "topic_environment",
                "topic_sustainability",
                "topic_astronomy",
                "topic_self_improvement",
                "topic_mindfulness",
            ),
        ),
    ),
    GroupSpec(
        "interests_craft_technology_growth",
        "Interests in craft, technology, and growth",
        "Food and drink, design, language and family history, collecting and making, emerging technology, finance, entrepreneurship, and productivity.",
        (
            named(
                "Interests: Topics",
                "topic_wine",
                "topic_coffee",
                "topic_craft_beer",
                "topic_tea",
                "topic_baking",
                "topic_interior_design",
                "topic_architecture",
                "topic_languages",
                "topic_genealogy",
                "topic_collecting",
                "topic_knitting",
                "topic_woodworking",
                "topic_calligraphy",
                "topic_robotics",
                "topic_drones",
                "topic_3d_printing",
                "topic_investmentoring",
                "topic_entrepreneurship",
                "topic_productivity",
            ),
        ),
    ),
)


def _build_finer_group_specs() -> tuple[GroupSpec, ...]:
    refined: list[GroupSpec] = []
    topic_replacements_added = False
    for base in _BASE_GROUP_SPECS:
        if base.chunk_id in {
            "interests_arts_spiritual_outdoors_games",
            "interests_community_craft_growth",
        }:
            if not topic_replacements_added:
                refined.extend(_TOPIC_INTEREST_REPLACEMENTS)
                topic_replacements_added = True
            continue
        replacements = _FINER_REPLACEMENTS.get(base.chunk_id)
        if replacements is not None:
            refined.extend(replacements)
            continue
        exception = _RETAINED_25_EXCEPTIONS.get(base.chunk_id)
        if exception is not None:
            refined.append(
                GroupSpec(
                    chunk_id=base.chunk_id,
                    label=base.label,
                    description=base.description,
                    selectors=base.selectors,
                    size_exception=exception,
                )
            )
            continue
        refined.append(base)
    return tuple(refined)


GROUP_SPECS = _build_finer_group_specs()


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_and_validate_catalog(path: Path) -> dict[str, Any]:
    try:
        catalog = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError(f"source catalog not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValidationError(f"source catalog is not valid JSON: {path}: {exc}") from exc

    if not isinstance(catalog, dict):
        raise ValidationError("source catalog root must be a JSON object")
    dimensions = catalog.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        raise ValidationError("source catalog dimensions must be a non-empty array")
    if catalog.get("targetDimensions") != len(dimensions):
        raise ValidationError(
            "targetDimensions does not equal the dimensions array length: "
            f"{catalog.get('targetDimensions')!r} != {len(dimensions)}"
        )

    seen_ids: set[str] = set()
    required = ("id", "label", "category", "description", "values", "index")
    for expected_index, dimension in enumerate(dimensions, start=1):
        if not isinstance(dimension, dict):
            raise ValidationError(f"dimension {expected_index} must be an object")
        missing = [field for field in required if field not in dimension]
        if missing:
            raise ValidationError(
                f"dimension {expected_index} is missing required fields: {', '.join(missing)}"
            )
        dimension_id = dimension["id"]
        if not isinstance(dimension_id, str) or not DIMENSION_ID_PATTERN.fullmatch(dimension_id):
            raise ValidationError(f"invalid dimension id at index {expected_index}: {dimension_id!r}")
        if dimension_id in seen_ids:
            raise ValidationError(f"duplicate dimension id: {dimension_id}")
        seen_ids.add(dimension_id)
        if dimension["index"] != expected_index:
            raise ValidationError(
                f"dimension {dimension_id} has index {dimension['index']!r}; expected {expected_index}"
            )
        for field in ("label", "category", "description"):
            if not isinstance(dimension[field], str) or not dimension[field].strip():
                raise ValidationError(f"dimension {dimension_id} has invalid {field}")
        values = dimension["values"]
        if (
            not isinstance(values, list)
            or not values
            or any(not isinstance(value, str) or not value for value in values)
            or len(values) != len(set(values))
        ):
            raise ValidationError(f"dimension {dimension_id} has invalid or duplicate values")
        default = dimension.get("defaultValue")
        defaults = default if isinstance(default, list) else [default]
        if any(value is not None and value not in values for value in defaults):
            raise ValidationError(
                f"dimension {dimension_id} has defaultValue outside its allowed values"
            )
        if "phrase" in dimension and not isinstance(dimension["phrase"], str):
            raise ValidationError(f"dimension {dimension_id} has a non-string phrase")
    return catalog


def _selector_ids(
    selector: Selector,
    category_dimensions: dict[str, list[dict[str, Any]]],
) -> list[str]:
    dimensions = category_dimensions.get(selector.category)
    if dimensions is None:
        raise ValidationError(f"group selector references missing category: {selector.category}")
    category_ids = [dimension["id"] for dimension in dimensions]
    if selector.dimension_ids:
        missing = [dimension_id for dimension_id in selector.dimension_ids if dimension_id not in category_ids]
        if missing:
            raise ValidationError(
                f"selector for {selector.category} references missing IDs: {', '.join(missing)}"
            )
        return list(selector.dimension_ids)
    if selector.start_id is None and selector.end_id is None:
        return category_ids
    if selector.start_id is None or selector.end_id is None:
        raise ValidationError(f"selector for {selector.category} has an incomplete span")
    try:
        start = category_ids.index(selector.start_id)
        end = category_ids.index(selector.end_id)
    except ValueError as exc:
        raise ValidationError(
            f"selector span for {selector.category} has a missing endpoint: "
            f"{selector.start_id}..{selector.end_id}"
        ) from exc
    if start > end:
        raise ValidationError(
            f"selector span for {selector.category} is reversed: "
            f"{selector.start_id}..{selector.end_id}"
        )
    return category_ids[start : end + 1]


def build_manifest(
    catalog: dict[str, Any],
    *,
    source_path: str = SOURCE_REPOSITORY_PATH,
) -> dict[str, Any]:
    dimensions: list[dict[str, Any]] = catalog["dimensions"]
    by_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_id: dict[str, dict[str, Any]] = {}
    source_position: dict[str, int] = {}
    for position, dimension in enumerate(dimensions):
        by_category[dimension["category"]].append(dimension)
        by_id[dimension["id"]] = dimension
        source_position[dimension["id"]] = position

    chunk_ids = [spec.chunk_id for spec in GROUP_SPECS]
    if len(chunk_ids) != len(set(chunk_ids)):
        duplicates = sorted(
            chunk_id for chunk_id, count in Counter(chunk_ids).items() if count > 1
        )
        raise ValidationError(f"duplicate chunk IDs in grouping rules: {', '.join(duplicates)}")

    assignments: dict[str, str] = {}
    selected_by_chunk: dict[str, list[str]] = {}
    for spec in GROUP_SPECS:
        selected: set[str] = set()
        for selector in spec.selectors:
            for dimension_id in _selector_ids(selector, by_category):
                if dimension_id in selected:
                    raise ValidationError(
                        f"chunk {spec.chunk_id} selects {dimension_id} more than once"
                    )
                selected.add(dimension_id)
                previous = assignments.get(dimension_id)
                if previous is not None:
                    raise ValidationError(
                        f"dimension {dimension_id} is assigned to both {previous} and {spec.chunk_id}"
                    )
                assignments[dimension_id] = spec.chunk_id
        selected_by_chunk[spec.chunk_id] = sorted(selected, key=source_position.__getitem__)

    catalog_ids = [dimension["id"] for dimension in dimensions]
    missing = [dimension_id for dimension_id in catalog_ids if dimension_id not in assignments]
    extra = sorted(set(assignments) - set(catalog_ids))
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing ({len(missing)}): {', '.join(missing[:20])}")
        if extra:
            details.append(f"unknown ({len(extra)}): {', '.join(extra[:20])}")
        raise ValidationError("group coverage is not exact; " + "; ".join(details))

    chunks: list[dict[str, Any]] = []
    for spec in GROUP_SPECS:
        dimension_ids = selected_by_chunk[spec.chunk_id]
        size = len(dimension_ids)
        outside_preferred = size < PREFERRED_MIN_SIZE or size > PREFERRED_MAX_SIZE
        if outside_preferred and not spec.size_exception:
            raise ValidationError(
                f"chunk {spec.chunk_id} has size {size} outside "
                f"{PREFERRED_MIN_SIZE}..{PREFERRED_MAX_SIZE} without a justification"
            )
        if not outside_preferred and spec.size_exception:
            raise ValidationError(
                f"chunk {spec.chunk_id} has an unnecessary size exception at size {size}"
            )
        source_categories = list(
            dict.fromkeys(by_id[dimension_id]["category"] for dimension_id in dimension_ids)
        )
        chunk: dict[str, Any] = {
            "chunk_id": spec.chunk_id,
            "label": spec.label,
            "description": spec.description,
            "source_categories": source_categories,
            "size": size,
            "dimension_ids": dimension_ids,
            "dimensions": [by_id[dimension_id] for dimension_id in dimension_ids],
        }
        if spec.size_exception:
            chunk["size_exception"] = spec.size_exception
        chunks.append(chunk)

    flattened = [dimension_id for chunk in chunks for dimension_id in chunk["dimension_ids"]]
    counts = Counter(flattened)
    duplicates = sorted(dimension_id for dimension_id, count in counts.items() if count > 1)
    if len(flattened) != len(catalog_ids) or set(flattened) != set(catalog_ids) or duplicates:
        raise ValidationError("final manifest coverage/uniqueness validation failed")

    category_chunks: dict[str, list[str]] = defaultdict(list)
    for chunk in chunks:
        for category in chunk["source_categories"]:
            category_chunks[category].append(chunk["chunk_id"])
    split_categories = {
        category: chunk_list
        for category, chunk_list in category_chunks.items()
        if len(chunk_list) > 1
    }
    merged_chunks = {
        chunk["chunk_id"]: chunk["source_categories"]
        for chunk in chunks
        if len(chunk["source_categories"]) > 1
    }
    sizes = [chunk["size"] for chunk in chunks]
    exceptions = [
        {
            "chunk_id": chunk["chunk_id"],
            "size": chunk["size"],
            "reason": chunk["size_exception"],
        }
        for chunk in chunks
        if "size_exception" in chunk
    ]

    return {
        "manifest_version": MANIFEST_VERSION,
        "source_catalog": {
            "path": source_path,
            "schema_version": catalog.get("schemaVersion"),
            "canonical_json_sha256": canonical_sha256(catalog),
            "dimension_count": len(dimensions),
        },
        "grouping": {
            "strategy": (
                "Finer reviewed semantic groups using category as the primary signal, explicit ID "
                "boundaries or named sets for subtopics, and limited merges for small related categories."
            ),
            "dimension_order": "ascending authoritative dimension index within each chunk",
            "target_size": TARGET_SIZE,
            "preferred_min_size": PREFERRED_MIN_SIZE,
            "preferred_max_size": PREFERRED_MAX_SIZE,
            "size_exception_policy": (
                "Every chunk outside the preferred range must carry a non-empty semantic justification."
            ),
        },
        "summary": {
            "chunk_count": len(chunks),
            "covered_dimension_count": len(flattened),
            "unique_dimension_count": len(counts),
            "min_chunk_size": min(sizes),
            "median_chunk_size": statistics.median(sizes),
            "max_chunk_size": max(sizes),
            "size_exceptions": exceptions,
            "split_categories": split_categories,
            "merged_chunks": merged_chunks,
        },
        "chunks": chunks,
    }


def render_manifest(manifest: dict[str, Any]) -> str:
    """Render one self-contained, nested chunk object per JSONL record."""
    lines = []
    chunk_count = manifest["summary"]["chunk_count"]
    for chunk_number, chunk in enumerate(manifest["chunks"], start=1):
        record = {
            **chunk,
            "manifest_context": {
                "manifest_version": manifest["manifest_version"],
                "chunk_number": chunk_number,
                "chunk_count": chunk_count,
                "source_catalog": manifest["source_catalog"],
                "grouping": manifest["grouping"],
            },
        }
        lines.append(
            json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        )
    return "\n".join(lines) + "\n"


def write_manifest(path: Path, rendered: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(rendered)


def print_summary(manifest: dict[str, Any]) -> None:
    summary = manifest["summary"]
    print(
        "chunks={chunk_count} dimensions={covered_dimension_count} "
        "sizes(min/median/max)={min_chunk_size}/{median_chunk_size}/{max_chunk_size}".format(
            **summary
        )
    )
    exceptions = summary["size_exceptions"]
    if exceptions:
        print(
            f"size exceptions ({len(exceptions)}): "
            + ", ".join(f"{item['chunk_id']}={item['size']}" for item in exceptions)
        )
    else:
        print("size exceptions (0): none")
    splits = summary["split_categories"]
    print(
        f"category splits ({len(splits)}): "
        + (", ".join(f"{category}={len(chunks)}" for category, chunks in splits.items()) or "none")
    )
    merges = summary["merged_chunks"]
    print(
        f"category merges ({len(merges)} chunks): "
        + (", ".join(f"{chunk_id}={len(categories)}" for chunk_id, categories in merges.items()) or "none")
    )
    print(
        f"coverage=exact unique={summary['unique_dimension_count']} "
        f"total={summary['covered_dimension_count']}"
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="authoritative dimensions catalog",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="generated chunk manifest",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="validate and fail if the tracked manifest is missing or stale",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="validate and print the summary without reading or writing the output",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        catalog = load_and_validate_catalog(args.source)
        source_path = (
            SOURCE_REPOSITORY_PATH
            if args.source.resolve() == DEFAULT_SOURCE.resolve()
            else args.source.as_posix()
        )
        manifest = build_manifest(catalog, source_path=source_path)
        rendered = render_manifest(manifest)
        print_summary(manifest)
        if args.dry_run:
            print("dry-run=ok (no files written)")
            return 0
        if args.check:
            try:
                existing = args.output.read_text(encoding="utf-8")
            except FileNotFoundError:
                print(f"ERROR: manifest is missing: {args.output}", file=sys.stderr)
                return 1
            if existing != rendered:
                print(
                    f"ERROR: manifest is stale; regenerate with {Path(__file__).name}: {args.output}",
                    file=sys.stderr,
                )
                return 1
            print(f"check=ok output={args.output}")
            return 0
        write_manifest(args.output, rendered)
        print(f"wrote={args.output}")
        return 0
    except ValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
