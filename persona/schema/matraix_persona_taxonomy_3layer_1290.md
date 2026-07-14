# MatrAIx Persona Three-Layer Taxonomy

## Overview

- **Count unit:** Persona attributes
- **Taxonomy depth:** Layer 1 → Layer 2 → Layer 3
- **Total persona attributes:** **1,290**
- Individual attributes are not displayed below Layer 3 in the main taxonomy.
- A **schema category** is the original flat `category` value in [dimensions.json](./dimensions.json); it is not a literature or grounding source.

## Taxonomy

```text
TOTAL PERSONA ATTRIBUTES [1,290]
|
+-- Background [238]
|   |
|   +-- Demographics [52]
|   |   +-- Core Demographics [25]                  (schema category: Demographic: Core)
|   |   +-- Family [1]                              (schema category: Demographic: Family)
|   |   +-- Cultural Background [2]                 (schema category: Demographic: Cultural)
|   |   +-- Life Events [24]                        (schema category: Demographic: Life Events)
|   |
|   +-- Language [90]
|   |   +-- Language Profile [53]                   (schema category: Linguistic: Language)
|   |   +-- Communication [37]                      (schema category: Linguistic: Communication)
|   |
|   +-- Education [35]
|   |   +-- Academic Background [34]                (schema category: Learning: Academic)
|   |   +-- Learning Style [1]                      (schema category: Learning: Style)
|   |
|   +-- Career [61]
|       +-- Career Profile [4]                      (schema category: Professional: Career)
|       +-- Industry [51]                           (schema category: Professional: Industry)
|       +-- Developer Professional Context [6]      (schema category: Developer: Professional Context)
|
+-- Psychology [210]
|   |
|   +-- Personality [90]
|   |   +-- Character [34]                          (schema category: Personality: Character)
|   |   +-- Big Five [50]                           (schema category: Personality: Big Five)
|   |   +-- MBTI [2]                                (schema category: Personality: MBTI)
|   |   +-- Relationships [4]                       (schema category: Personality: Relationships)
|   |
|   +-- Worldview [113]
|   |   +-- Values & Motivation [46]                (schema category: Values & Motivation)
|   |   +-- Beliefs [67]                            (schema category: Worldview: Beliefs)
|   |
|   +-- Decision-Making [7]
|       +-- Risk & Decision [7]                     (schema category: Risk & Decision)
|
+-- Capability [331]
|   |
|   +-- Domains [144]                               (schema category: Expertise: Domains)
|   |   +-- Cross-Domain Expertise Profile [4]
|   |   +-- Computing, Data & AI [18]
|   |   +-- Engineering, Energy & Infrastructure [16]
|   |   +-- Medicine, Health & Life Sciences [17]
|   |   +-- Natural & Environmental Sciences [17]
|   |   +-- Law, Economics & Finance [17]
|   |   +-- Social Sciences & Public Affairs [7]
|   |   +-- Humanities & Cultural Studies [10]
|   |   +-- Education & Human Services [7]
|   |   +-- Arts, Design & Media [17]
|   |   +-- Business, Management & Marketing [11]
|   |   +-- Hospitality & Culinary [3]
|   |
|   +-- Skills [187]
|       +-- General Skills [64]                     (schema category: Expertise: Skills)
|       +-- Tools [69]                              (schema category: Skills: Tools)
|       +-- Programming [44]                        (schema category: Skills: Programming)
|       +-- Developer Code Maintenance [10]         (schema category: Developer: Code Maintenance)
|
+-- Behavior and Interaction [124]
|   |
|   +-- Personal Behavior [67]
|   |   +-- Preferences [34]                        (schema category: Behavior: Preferences)
|   |   +-- Habits [30]                             (schema category: Behavior: Habits)
|   |   +-- Time Use [3]                            (schema category: Behavior: Time)
|   |
|   +-- Interaction State [5]                       (schema category: State: Emotional)
|   |   +-- Current Emotional State [1]
|   |   +-- Task & Interaction Context [4]
|   |
|   +-- Work Practices [13]
|   |   +-- General Work Practices [2]              (schema category: Behavior: Work)
|   |   +-- Developer Open Source Behavior [7]      (schema category: Developer: Open Source Behavior)
|   |   +-- Developer Community Behavior [4]        (schema category: Developer: Community Behavior)
|   |
|   +-- Technology Use [39]
|       +-- Developer AI Tool Adoption [8]           (schema category: Developer: AI Adoption)
|       +-- Developer AI Workflow Tasks [12]        (schema category: Developer: AI Workflow Tasks)
|       +-- Developer Coding Agent Adoption [11]    (schema category: Developer: Agent Adoption)
|       +-- Developer Technology Evaluation [8]     (schema category: Developer: Technology Evaluation)
|
+-- Lifestyle and Health [387]
    |
    +-- Interests [284]
    |   +-- Broad Interest Areas [78]               (schema category: Interests: Topics)
    |   +-- Media [81]                              (schema category: Interests: Media)
    |   +-- Hobbies [50]                            (schema category: Interests: Hobbies)
    |   +-- Sports [40]                             (schema category: Interests: Sports)
    |   +-- Food [35]                               (schema category: Interests: Food)
    |
    +-- Culture and Daily Life [74]                 (schema category: Interests: Culture)
    |   +-- Cultural Familiarity [40]
    |   +-- Lifestyle Patterns [34]
    |
    +-- Health [29]
        +-- Health Status & Accessibility [25]      (schema category: Health: Physical)
        +-- Health Orientation & Behaviors [4]      (schema categories: Health: Fitness [2]; Health: Lifestyle [2])
```

## Count Validation

### Layer 1 totals

| Layer 1 group | Attributes |
|---|---:|
| Background | 238 |
| Psychology | 210 |
| Capability | 331 |
| Behavior and Interaction | 124 |
| Lifestyle and Health | 387 |
| **Total** | **1,290** |

\[
238 + 210 + 331 + 124 + 387 = 1{,}290
\]

### Structural totals

| Validation item | Result |
|---|---:|
| Layer 1 groups | 5 |
| Layer 2 groups | 16 |
| Layer 3 groups | 55 |
| Original schema categories covered | 43 / 43 |
| Persona attributes assigned | 1,290 / 1,290 |
| Missing attribute assignments | 0 |
| Duplicate attribute assignments | 0 |
| Difference from schema target | 0 |

Layer 3 count by Layer 1 branch:

\[
11_{\text{Background}} + 7_{\text{Psychology}} + 16_{\text{Capability}}
+ 12_{\text{Behavior and Interaction}} + 9_{\text{Lifestyle and Health}} = 55
\]

## Attribute-Level Reassignment Rules

Most Layer 3 groups map directly to one flat schema category. Three schema categories are split at the attribute level: `Expertise: Domains`, `Interests: Culture`, and `State: Emotional`. The `Health: Fitness` and `Health: Lifestyle` categories are combined into one conceptual Layer 3 group.

### `Expertise: Domains` → 12 Layer 3 groups

The following assignments cover all 144 attributes exactly once.

<details>
<summary><strong>Cross-Domain Expertise Profile [4]</strong></summary>

- `domain`
- `subject_specialty`
- `tech_savviness`
- `expertise_gap`

</details>

<details>
<summary><strong>Computing, Data & AI [18]</strong></summary>

- `fam_machine_learning`
- `fam_deep_learning`
- `fam_statistics`
- `fam_data_science`
- `fam_cybersecurity`
- `fam_cryptography`
- `fam_computer_networking`
- `fam_databases`
- `fam_distributed_systems`
- `fam_operating_systems`
- `fam_compilers`
- `fam_cloud_infrastructure`
- `fam_devops`
- `fam_game_development`
- `fam_computer_graphics`
- `fam_computer_vision`
- `fam_natural_language_processing`
- `fam_human_computer_interaction`

</details>

<details>
<summary><strong>Engineering, Energy & Infrastructure [16]</strong></summary>

- `fam_structural_engineering`
- `fam_mechanical_engineering`
- `fam_electrical_engineering`
- `fam_civil_engineering`
- `fam_chemical_engineering`
- `fam_aerospace_engineering`
- `fam_robotics`
- `fam_control_systems`
- `fam_materials_science`
- `fam_nanotechnology`
- `fam_renewable_energy`
- `fam_nuclear_engineering`
- `fam_petroleum_engineering`
- `fam_mining`
- `fam_aviation`
- `fam_maritime_navigation`

</details>

<details>
<summary><strong>Medicine, Health & Life Sciences [17]</strong></summary>

- `fam_cardiology`
- `fam_neurology`
- `fam_oncology`
- `fam_pediatrics`
- `fam_psychiatry`
- `fam_radiology`
- `fam_surgery`
- `fam_immunology`
- `fam_molecular_biology`
- `fam_genetics`
- `fam_veterinary_medicine`
- `fam_nursing`
- `fam_pharmacology`
- `fam_public_health`
- `fam_epidemiology`
- `fam_nutrition`
- `fam_sports_science`

</details>

<details>
<summary><strong>Natural & Environmental Sciences [17]</strong></summary>

- `fam_biochemistry`
- `fam_organic_chemistry`
- `fam_physical_chemistry`
- `fam_particle_physics`
- `fam_astrophysics`
- `fam_astronomy`
- `fam_geology`
- `fam_oceanography`
- `fam_climate_science`
- `fam_ecology`
- `fam_geographic_information_systems`
- `fam_meteorology`
- `fam_forestry`
- `fam_marine_biology`
- `fam_paleontology`
- `fam_agronomy`
- `fam_horticulture`

</details>

<details>
<summary><strong>Law, Economics & Finance [17]</strong></summary>

- `fam_constitutional_law`
- `fam_contract_law`
- `fam_criminal_law`
- `fam_tax_law`
- `fam_intellectual_property`
- `fam_corporate_finance`
- `fam_quantitative_trading`
- `fam_accounting`
- `fam_auditing`
- `fam_macroeconomics`
- `fam_microeconomics`
- `fam_behavioral_economics`
- `fam_venture_capital`
- `fam_private_equity`
- `fam_real_estate`
- `fam_insurance`
- `fam_actuarial_science`

</details>

<details>
<summary><strong>Social Sciences & Public Affairs [7]</strong></summary>

- `fam_sociology`
- `fam_psychology`
- `fam_cognitive_science`
- `fam_anthropology`
- `fam_international_relations`
- `fam_military_strategy`
- `fam_diplomacy`

</details>

<details>
<summary><strong>Humanities & Cultural Studies [10]</strong></summary>

- `fam_comparative_literature`
- `fam_philosophy`
- `fam_ethics`
- `fam_history`
- `fam_archaeology`
- `fam_linguistics`
- `fam_theology`
- `fam_art_history`
- `fam_music_theory`
- `fam_film_studies`

</details>

<details>
<summary><strong>Education & Human Services [7]</strong></summary>

- `fam_curriculum_design`
- `fam_pedagogy`
- `fam_organizational_psychology`
- `fam_human_resources`
- `fam_counseling`
- `fam_library_science`
- `fam_social_work`

</details>

<details>
<summary><strong>Arts, Design & Media [17]</strong></summary>

- `fam_architecture`
- `fam_urban_planning`
- `fam_landscape_design`
- `fam_ux_research`
- `fam_graphic_design`
- `fam_industrial_design`
- `fam_typography`
- `fam_journalism`
- `fam_public_relations`
- `fam_fashion_design`
- `fam_textiles`
- `fam_photography`
- `fam_cinematography`
- `fam_music_production`
- `fam_sound_engineering`
- `fam_animation`
- `fam_3d_modeling`

</details>

<details>
<summary><strong>Business, Management & Marketing [11]</strong></summary>

- `fam_brand_marketing`
- `fam_performance_marketing`
- `fam_seo`
- `fam_sales_engineering`
- `fam_supply_chain`
- `fam_logistics`
- `fam_operations_management`
- `fam_lean_manufacturing`
- `fam_quality_assurance`
- `fam_project_management`
- `fam_product_management`

</details>

<details>
<summary><strong>Hospitality & Culinary [3]</strong></summary>

- `fam_hospitality_management`
- `fam_culinary_arts`
- `fam_sommelier_knowledge`

</details>

Domain count check:

\[
4 + 18 + 16 + 17 + 17 + 17 + 7 + 10 + 7 + 17 + 11 + 3 = 144
\]

### `Interests: Culture` → 2 Layer 3 groups

- **Cultural Familiarity [40]:** all attributes in `Interests: Culture` whose IDs match `cult_*`.
- **Lifestyle Patterns [34]:** all attributes in `Interests: Culture` whose IDs match `lstyle_*`.

This preserves all 74 attributes:

\[
40 + 34 = 74
\]

For example, `lstyle_smoking` remains in the flat schema category `Interests: Culture`, but the conceptual taxonomy places it under **Lifestyle Patterns**, not **Cultural Familiarity**.

### `State: Emotional` → 2 Layer 3 groups under Behavior and Interaction

- **Current Emotional State [1]:** `emotional_state`
- **Task & Interaction Context [4]:** `intent`, `query_complexity`, `prior_context`, and `device_context`

The schema category name emphasizes emotion, but four of its five attributes describe the current request and interaction setting. The conceptual taxonomy therefore places the full category under **Behavior and Interaction** and separates transient emotion from task context.

### `Health: Fitness` + `Health: Lifestyle` → Health Orientation & Behaviors [4]

This group combines health-related motivation and recurring practices:

- `topic_fitness` — interest in fitness
- `lstyle_exercise_freq` — exercise frequency
- `lstyle_diet_type` — diet type
- `lstyle_alcohol_use` — alcohol use

The first attribute measures orientation, while the remaining three measure behavior. This is why the combined group is named **Health Orientation & Behaviors**, rather than only **Health Behaviors**.

## Scope Notes

- The count includes all 1,290 attributes in [dimensions.json](./dimensions.json).
- The graph's 18 latent/helper nodes are excluded because they are not persona attributes.
- `Developer` is treated as a Layer 3 scope qualifier rather than a Layer 2 facet.
- `Domains` and `Skills` remain Layer 2 facets under `Capability`.
- The original `Expertise: Domains` category is split into 12 Layer 3 groups through explicit attribute-level reassignment.
- The original `Interests: Culture` category is split into `Cultural Familiarity` and `Lifestyle Patterns` using attribute ID prefixes.
- The original `State: Emotional` category is moved from `Psychology` to `Behavior and Interaction` and split into `Current Emotional State` and `Task & Interaction Context`.
- The original `Health: Fitness` and `Health: Lifestyle` categories are combined into `Health Orientation & Behaviors` because fitness engagement is a health-oriented behavior domain.
- The taxonomy is a conceptual organization of the attributes. The separate grounding-source table may regroup the same attributes differently for evidence attribution.
