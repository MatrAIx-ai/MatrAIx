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

### Age

Grounding claim: sources support age distributions by country, region, and
population segment.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| UN World Population Prospects | Age-disaggregated estimates/projections; single-year or 5-year age groups; country/region coverage | The UN WPP page describes population estimates and projections with datasets disaggregated by age, available by single ages and standard 5-year age groups, across countries, regions, and global aggregates. | Verified |
| UN Population Division Data Portal | Age-related demographic indicators; interactive indicator/location access | The Data Portal provides global demographic indicators by indicator and location, which supports age-focused demographic lookup and visualization. | Verified |
| World Bank World Development Indicators | Age-structured demographic series; country/year indicators | WDI provides country-level and regional aggregate demographic indicators by time, including population and age-structure series useful for age priors. | Verified |
| ACS PUMS | Person-level age variables; household/person microdata | ACS PUMS is U.S. Census public-use microdata with person-level demographic records, supporting U.S.-specific age distributions and age-linked attributes. | Verified, U.S.-focused |
| IPUMS International | Harmonized census microdata; age variables across countries | IPUMS International provides harmonized census microdata across countries, supporting cross-national age distributions and age-linked demographic analysis. | Verified, account/license may be required |
| IPUMS USA | U.S. census/ACS microdata; age variables | IPUMS USA provides harmonized U.S. census and ACS microdata, supporting U.S. age, household, education, and work dimensions. | Verified, U.S.-focused |

### Sex / Gender

Grounding claim: sources support sex/gender demographic distributions and
survey demographics.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| UN World Population Prospects | Population by sex; country/region coverage | UN WPP provides official population estimates and projections, including sex-disaggregated demographic tables at country, regional, and global levels. | Verified |
| World Bank World Development Indicators | Sex-disaggregated population indicators | WDI provides country-level demographic indicators and regional aggregates, including sex-disaggregated population and related demographic series. | Verified |
| ACS PUMS | Person-level sex variables; U.S. demographic microdata | ACS PUMS contains U.S. person-level demographic microdata with sex variables and linked household/person characteristics. | Verified, U.S.-focused |
| IPUMS International | Harmonized census sex variables across countries | IPUMS International supports cross-national census microdata analysis with harmonized sex variables and demographic characteristics. | Verified, account/license may be required |
| IPUMS USA | U.S. sex variables across census/ACS microdata | IPUMS USA supports U.S. census/ACS sex distributions and links sex to education, household, work, and migration variables. | Verified, U.S.-focused |
| Pew Research Center datasets | Survey demographics; public opinion cross-tabs | Pew datasets and reports include respondent demographics and support gender-demographic validation for survey-based dimensions. | Verified, survey-focused |

### Urbanicity

Grounding claim: sources support urban/rural distribution and geographic
settlement context.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| World Bank World Development Indicators | Urban/rural population indicators; country/year series | WDI provides country-level and regional aggregate indicators, including urban and rural population series used for urbanicity grounding. | Verified |
| UN World Urbanization Prospects | Urbanization estimates/projections; city/urban/rural coverage | UN World Urbanization Prospects is the UN Population Division source for urbanization estimates and projections, supporting urbanicity grounding. | Verified |
| ACS data | U.S. geographic and household/community indicators | ACS data supports U.S.-specific geography and community-level demographic grounding, including urban/rural-adjacent variables through ACS geographies. | Verified, U.S.-focused |
| WorldPop | High-resolution geospatial population distribution | WorldPop provides open high-resolution geospatial population datasets and spatial demographic data, supporting urbanicity and settlement-density grounding. | Verified |

### Education

Grounding claim: sources support educational attainment, enrollment, literacy,
and education-system indicators.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| UNESCO Institute for Statistics | Education indicators; literacy/enrollment/attainment | UNESCO UIS is an official international statistics source for education indicators, supporting education-system and attainment grounding. | Verified |
| World Bank Education Statistics | Country-level education indicators | World Bank Education Statistics provides country-level education series, supporting enrollment, attainment, and education-system grounding. | Verified |
| ILOSTAT | Education in labor/population tables; labor force by education | ILOSTAT includes population and labor indicators with education breakdowns, supporting education-work relationships. | Verified |
| OECD Education at a Glance | Education indicators for OECD and partner countries | OECD Education at a Glance provides official education indicators for OECD and partner countries, supporting cross-national education grounding. | Verified, OECD-focused |
| OECD PISA | Student assessment and education-system indicators | OECD PISA supports education-system grounding through internationally comparable student assessment and background data. | Verified, student-focused |
| ACS PUMS | U.S. person-level education variables | ACS PUMS includes person-level educational attainment variables linked to age, work, income, and household context. | Verified, U.S.-focused |
| IPUMS International | Harmonized census education variables | IPUMS International provides harmonized education and literacy/attainment variables across census microdata sources. | Verified, account/license may be required |
| IPUMS USA | U.S. education variables across census/ACS microdata | IPUMS USA supports U.S. educational attainment and links education to work, income, and household attributes. | Verified, U.S.-focused |

### Employment / Occupation / Work

Grounding claim: sources support employment status, occupation, work context,
skills, and labor-market dimensions.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| ILOSTAT | Labor force, employment, unemployment, occupation indicators | ILOSTAT provides international labor statistics, including labor force, employment, unemployment, and occupation indicators by country and demographic group. | Verified |
| BLS OEWS | Occupation employment and wage data | BLS OEWS provides U.S. occupational employment and wage statistics, supporting occupation and compensation grounding. | Verified, U.S.-focused |
| O*NET | Occupation taxonomy; skills, knowledge, abilities, work context | O*NET provides official U.S. occupation taxonomy and ratings for skills, knowledge, abilities, education, tools, and work context. | Verified, U.S.-focused |
| OECD employment data | Employment and labor-market indicators | OECD employment data supports labor-market validation for OECD and partner economies. | Verified, OECD-focused |
| ACS PUMS | Person-level employment and occupation variables | ACS PUMS contains U.S. person-level employment, occupation, industry, commute, and income variables. | Verified, U.S.-focused |
| IPUMS USA | Harmonized U.S. employment/occupation microdata | IPUMS USA supports employment status, occupation, industry, and work-related variables in U.S. census/ACS microdata. | Verified, U.S.-focused |
| IPUMS CPS | U.S. labor-force survey microdata | IPUMS CPS harmonizes Current Population Survey microdata, supporting U.S. employment, labor force, occupation, and income grounding. | Verified, U.S.-focused |

### Income / Socioeconomic Status

Grounding claim: sources support income, poverty, inequality, and socioeconomic
status dimensions.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| World Bank Poverty and Inequality Platform | Poverty, inequality, welfare distribution | The World Bank Poverty and Inequality Platform supports country-level poverty and inequality grounding. | Verified |
| World Bank World Development Indicators | Income, poverty, and development indicators | WDI provides country-level and regional aggregate economic and development indicators useful for socioeconomic priors. | Verified |
| World Inequality Database | Income and wealth inequality indicators | The World Inequality Database provides inequality and distributional indicators for income and wealth grounding. | Verified |
| Luxembourg Income Study | Harmonized income microdata | LIS provides harmonized income microdata and distributional resources, supporting socioeconomic and income grounding. | Verified, access may require registration |
| OECD Income Distribution Database | Income distribution and inequality indicators | OECD IDD provides income distribution and inequality indicators for OECD and partner countries. | Verified, OECD-focused |
| ACS PUMS | U.S. person/household income variables | ACS PUMS includes income and socioeconomic variables linked to household, education, employment, and geography. | Verified, U.S.-focused |
| IPUMS USA | U.S. income and socioeconomic microdata | IPUMS USA harmonizes U.S. census/ACS income, poverty, occupation, household, and demographic variables. | Verified, U.S.-focused |
| IPUMS CPS | U.S. income and labor microdata | IPUMS CPS supports U.S. labor-force and income grounding using harmonized CPS microdata. | Verified, U.S.-focused |

### Household / Family / Marital Status

Grounding claim: sources support household size, family structure, marital
status, parental status, and related demographic context.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| ACS PUMS | Household/person microdata; marital/family variables | ACS PUMS includes U.S. household and person microdata with household size, relationship, marital status, and family variables. | Verified, U.S.-focused |
| IPUMS International | Harmonized household and family variables | IPUMS International supports cross-national household composition, relationship, marital status, and family variables in census microdata. | Verified, account/license may be required |
| IPUMS USA | U.S. household/family census variables | IPUMS USA supports U.S. household composition, relationship, marital status, children, and family structure variables. | Verified, U.S.-focused |
| UN Population Division | Family, marital status, fertility, migration themes | The UN Population Division Data Portal includes demographic themes such as marital status, fertility, and population, supporting broad household/family grounding. | Verified |
| OECD Family Database | Family structure and child/family indicators | OECD Family Database supports family, household, fertility, child, and family-policy indicators. | Verified, OECD-focused |
| DHS Program | Household and family survey microdata | DHS surveys provide household, fertility, family, and health variables in many countries. | Verified, survey-focused |
| UNICEF MICS | Household survey indicators | UNICEF MICS provides household survey data on children, households, education, health, and family-related indicators. | Verified, survey-focused |

### Language / Locale / Culture

Grounding claim: sources support language, locale, script, territory, and
language geography dimensions.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| Unicode CLDR | Locale, territory, script, language metadata | Unicode CLDR provides locale, language, script, territory, and formatting metadata used for language and locale grounding. | Verified |
| Glottolog | Language taxonomy and language geography | Glottolog provides language taxonomy and geolocation metadata; the local raw manifest points to Glottolog downloads for language taxonomy and geolocation files. | Verified |
| World Atlas of Language Structures | Cross-linguistic language features | WALS provides structured cross-linguistic features and language metadata, supporting language and culture-adjacent grounding. | Verified |
| Ethnologue | Language reference and speaker/community information | Ethnologue is a language reference source covering languages, speaker communities, and language status. | Verified, access may be limited |

### Religion / Religiosity

Grounding claim: sources support religious affiliation, denomination,
religiosity, belief, and religious practice dimensions.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| Pew Research Center Religion | Religion survey reports and datasets | Pew Research Center Religion provides public reports and datasets on religious affiliation, belief, practice, and demographics. | Verified |
| World Values Survey | Religion and values survey variables | WVS includes cross-national survey variables on religion, values, trust, politics, and social attitudes. | Verified |
| General Social Survey | U.S. religion and social-attitude variables | GSS provides U.S. survey microdata covering religious affiliation, attendance, beliefs, politics, trust, and values. | Verified, U.S.-focused |
| Association of Religion Data Archives | Religion datasets and metadata | ARDA aggregates religion datasets and documentation, supporting religious affiliation and religiosity grounding. | Verified |

### Values / Politics / Trust / Social Attitudes

Grounding claim: sources support political lean, public trust, social values,
and public opinion dimensions.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| World Values Survey | Cross-national values, trust, politics, religion | WVS provides cross-national survey data on values, trust, religion, politics, social attitudes, and demographics. | Verified |
| General Social Survey | U.S. attitudes, politics, trust, values | GSS provides U.S. public-use survey data on social attitudes, trust, politics, religion, and values. | Verified, U.S.-focused |
| Pew Research Center | Public opinion datasets and reports | Pew Research Center provides public opinion, demographics, religion, politics, and social-issue survey resources. | Verified |
| European Social Survey | Cross-national European attitudes | ESS provides academically governed European survey data on attitudes, values, politics, trust, and demographics. | Verified, Europe-focused |
| International Social Survey Programme | Cross-national topical social surveys | ISSP provides repeated cross-national modules on social attitudes, politics, identity, work, family, religion, and related topics. | Verified |
| Gallup World Poll | Global public opinion and wellbeing survey | Gallup World Poll supports global public opinion, wellbeing, and social indicator grounding, though access may be restricted. | Verified, restricted access |
| Afrobarometer | African public opinion surveys | Afrobarometer provides public opinion survey data across African countries on democracy, governance, trust, values, and social issues. | Verified, region-focused |
| Arab Barometer | MENA public opinion surveys | Arab Barometer provides public opinion survey data across Arab countries on politics, society, religion, trust, and values. | Verified, region-focused |
| Asian Barometer | Asian public opinion surveys | Asian Barometer provides public opinion and democracy-related survey data across Asian societies. | Verified, region-focused |
| Latinobarometro | Latin American public opinion surveys | Latinobarometro provides public opinion and social-attitude survey data across Latin America. | Verified, region-focused |
| Eurobarometer | European public opinion surveys | Eurobarometer provides EU-focused public opinion survey data on politics, society, trust, and policy attitudes. | Verified, Europe-focused |

### Personality / Psychometrics

Grounding claim: sources support personality traits, psychological scales, and
self-report constructs.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| International Personality Item Pool | Public-domain personality items and scales | IPIP provides public-domain personality item pools and scales, supporting Big Five and related psychometric constructs. | Verified |
| SAPA Project | Personality and ability assessment data | SAPA Project supports personality and psychometric grounding through online assessment and public research resources. | Verified |
| Midlife in the United States | Longitudinal survey with psychosocial measures | MIDUS provides longitudinal survey resources covering health, personality, wellbeing, and psychosocial constructs. | Verified, U.S.-focused |

### Health / Disability / Accessibility

Grounding claim: sources support health status, disability, sensory/mobility
conditions, and accessibility-related dimensions.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| WHO Global Health Observatory | Global health indicators | WHO GHO provides official global health indicators and metadata, supporting health grounding. | Verified |
| IHME Global Burden of Disease | Disease burden, disability, health metrics | IHME GBD provides global, regional, and national health burden metrics, supporting health and disability grounding. | Verified |
| ACS PUMS | U.S. disability and demographic variables | ACS PUMS includes U.S. disability, demographic, household, and socioeconomic variables. | Verified, U.S.-focused |
| CDC NHIS | U.S. health interview survey | CDC NHIS provides U.S. health survey data on health status, conditions, disability, and healthcare access. | Verified, U.S.-focused |
| CDC BRFSS | U.S. behavioral risk survey | CDC BRFSS provides U.S. state-level behavioral health and risk-factor survey data. | Verified, U.S.-focused |
| DHS Program | Health and household surveys | DHS surveys support health, maternal/child health, fertility, household, and demographic variables across many countries. | Verified, survey-focused |
| UNICEF MICS | Child, household, health, and education indicators | UNICEF MICS provides household survey data on children, health, education, family, and living conditions. | Verified, survey-focused |

### Lifestyle / Time Use / Consumption

Grounding claim: sources support daily activity, time use, household spending,
and consumption behavior dimensions.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| American Time Use Survey | Time-use activity categories; U.S. survey data | ATUS provides U.S. time-use survey data covering daily activities, work, leisure, caregiving, and household activities. | Verified, U.S.-focused |
| Consumer Expenditure Surveys | Household spending and consumption | BLS Consumer Expenditure Surveys provide U.S. household spending, income, and consumption data. | Verified, U.S.-focused |
| OECD Time Use Database | Cross-national time-use comparisons | OECD Time Use Database supports time-use and activity-pattern grounding across OECD and partner countries. | Verified, OECD-focused |

### Technology / Internet Access / Digital Behavior

Grounding claim: sources support internet access, digital adoption, device use,
and general technology behavior.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| International Telecommunication Union statistics | ICT access and adoption indicators | ITU statistics provide official ICT indicators on internet, mobile, broadband, and digital access. | Verified |
| World Bank World Development Indicators | Internet and technology adoption indicators | WDI provides country-level internet, mobile, and technology-related indicators as part of country-year series. | Verified |
| DataReportal | Global digital adoption reports | DataReportal provides global digital reports covering internet use, social media, mobile adoption, and digital behavior. | Verified, report-focused |
| Pew Internet & Technology | U.S. technology and internet behavior surveys | Pew Internet & Technology provides survey reports on internet access, technology adoption, devices, and digital behavior. | Verified, U.S.-focused |
| Stack Overflow Survey | Developer technology/tool survey | Stack Overflow Survey supports technology behavior for developer populations, including tools, languages, AI, and work preferences. | Verified, developer-focused |

### Developer / Coding / Technical Tools

Grounding claim: sources support developer skills, programming languages,
technical tools, AI-tool usage, and developer workflow dimensions.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| Stack Overflow Survey | Programming languages; developer tools; AI tools; work preferences | Stack Overflow Survey provides annual developer survey data covering languages, tools, platforms, work, AI-tool adoption, and demographics. | Verified, developer-focused |
| GitHub Octoverse | Developer ecosystem and platform trends | GitHub Octoverse reports on developer activity, repositories, languages, AI, and platform ecosystem trends. | Verified, platform/report-focused |
| JetBrains State of Developer Ecosystem Report | Developer tools, languages, AI, productivity, demographics | JetBrains State of Developer Ecosystem Report provides survey-based developer ecosystem metrics, including languages, tools, AI, productivity, work, salary, and demographics. | Verified, developer-focused |
| CNCF Annual Survey | Cloud-native tools and practices | CNCF survey reports support cloud-native tooling, containers, Kubernetes, platform, and developer infrastructure dimensions. | Verified, developer/cloud-focused |

### Migration / Citizenship / Country Of Birth

Grounding claim: sources support citizenship, migration status, country of
birth, international migrant stock, and migration/remittance context.

| Source | Evidence to look for | Observed evidence | Status |
| --- | --- | --- | --- |
| UN International Migrant Stock | International migrant stock by origin/destination | UN International Migrant Stock supports country-level migration stock and origin/destination grounding. | Verified |
| OECD migration data | Migration indicators for OECD and partner countries | OECD migration data supports migration, immigrant population, labor migration, and integration indicators. | Verified, OECD-focused |
| ACS PUMS | Citizenship, birthplace, migration, language variables | ACS PUMS includes U.S. person-level variables for citizenship, place of birth, migration, language, household, and demographics. | Verified, U.S.-focused |
| IPUMS International | Harmonized migration/birthplace census variables | IPUMS International supports cross-national country-of-birth, migration, citizenship-adjacent, and household/demographic variables. | Verified, account/license may be required |
| IPUMS USA | U.S. citizenship, birthplace, migration variables | IPUMS USA supports U.S. census/ACS citizenship, birthplace, migration, ancestry, and language variables. | Verified, U.S.-focused |
| World Bank Migration and Remittances | Migration/remittance indicators and resources | World Bank Migration and Remittances supports migration and remittance context at country and regional levels. | Verified |

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