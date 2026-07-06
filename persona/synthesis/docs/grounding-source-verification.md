# Persona Graph Grounding Source Verification

This document tracks verification notes for the grounding sources listed in
`grounding-sources.md`. It mirrors the `Source Catalog` sections in that file so
the source list and verification notes stay aligned.

Each row combines:

- source-level verification: who provides the source, what scope it covers, and
  what type of data it provides;
- dimension-level verification: which MatrAIx dimension areas the source
  supports;
- status: whether the source is currently usable for grounding.

## Status Labels

- `Verified`: The source is official or credible and supports the listed
  dimension areas.
- `Needs review`: The source appears relevant, but scope, access, or dimension
  fit needs another pass.
- `Replace`: The source is weak, broken, not official enough, or not directly
  relevant.
- `Remove`: The source should be removed from the grounding list.

## Population And Demographics

| Source | Source-level verification | Dimension-level support | Status |
| --- | --- | --- | --- |
| UN World Population Prospects | Official UN Population Division population estimates and projections; global coverage across countries, regions, subregions, age, and sex. | Region / population distribution; Age; Sex / gender; Migration / citizenship context | Verified |
| UN Population Division Data Portal | Official UN Population Division data portal with interactive demographic indicators by indicator and location. | Region / population distribution; Age; Household / family / marital status; Migration / citizenship context | Verified |
| UN World Urbanization Prospects | Official UN Population Division urbanization estimates and projections. | Urbanicity; Region / population distribution | Verified |
| World Bank World Development Indicators | Official World Bank country-year and regional aggregate indicator database. | Region / population distribution; Age; Sex / gender; Urbanicity; Income / socioeconomic status; Technology / internet access | Verified |
| World Bank DataBank | Official World Bank platform for accessing World Bank datasets including WDI and related indicators. | Region / population distribution; Education; Income / socioeconomic status; Technology / internet access | Verified |
| WorldPop | Open spatial demographic datasets from WorldPop / University of Southampton, focused on high-resolution population distributions and spatial demographics. | Region / population distribution; Urbanicity | Verified |
| Eurostat | Official European Union statistics portal, with population and demographic indicators for Europe. | Region / population distribution; Age; Sex / gender; Urbanicity | Verified, Europe-focused |
| U.S. Census ACS PUMS | Official U.S. Census public-use person and household microdata. | Age; Sex / gender; Education; Employment / occupation / work; Income / socioeconomic status; Household / family / marital status; Health / disability; Migration / citizenship | Verified, U.S.-focused |
| ACS data portal | Official U.S. Census ACS data access portal. | Urbanicity; Population and demographic context; U.S. geography-linked demographic validation | Verified, U.S.-focused |
| IPUMS | University of Minnesota IPUMS data platform for harmonized census and survey microdata. | Age; Sex / gender; Education; Employment / occupation / work; Income / socioeconomic status; Household / family / marital status; Migration / citizenship | Verified |
| IPUMS International | Harmonized cross-national census microdata. | Age; Sex / gender; Education; Household / family / marital status; Migration / citizenship | Verified, account/license may be required |
| IPUMS USA | Harmonized U.S. census and ACS microdata. | Age; Sex / gender; Education; Employment / occupation / work; Income / socioeconomic status; Household / family / marital status; Migration / citizenship | Verified, U.S.-focused |

## Education, Work, And Socioeconomics

| Source | Source-level verification | Dimension-level support | Status |
| --- | --- | --- | --- |
| UNESCO Institute for Statistics | Official UNESCO statistics source for education indicators. | Education | Verified |
| World Bank Education Statistics | World Bank education indicator database. | Education | Verified |
| ILOSTAT data | Official International Labour Organization labor statistics data portal. | Employment / occupation / work; Education; Age; Sex / gender | Verified |
| ILOSTAT explorer | ILOSTAT interactive data explorer for labor-market and population indicators. | Employment / occupation / work; Education; Age; Sex / gender | Verified |
| BLS Occupational Employment and Wage Statistics | Official U.S. Bureau of Labor Statistics occupation employment and wage data. | Employment / occupation / work; Income / socioeconomic status | Verified, U.S.-focused |
| OEWS data overview | BLS overview page for OEWS tables and data products. | Employment / occupation / work; Income / socioeconomic status | Verified, U.S.-focused |
| O*NET Resource Center | U.S. Department of Labor O*NET resource site for occupation taxonomy and ratings. | Employment / occupation / work; Developer / coding / technical tools; Skills and work context | Verified, U.S.-focused |
| O*NET database releases | O*NET database release page for occupation, skills, knowledge, abilities, education, tools, and work-context data. | Employment / occupation / work; Skills and work context | Verified, U.S.-focused |
| OECD employment data | OECD employment and labor-market data resources. | Employment / occupation / work | Verified, OECD-focused |
| OECD Education at a Glance | OECD education indicators report and data resources. | Education | Verified, OECD-focused |
| OECD PISA | OECD student assessment and background data program. | Education | Verified, student-focused |
| OECD Income Distribution Database | OECD income distribution and inequality indicator database. | Income / socioeconomic status | Verified, OECD-focused |
| World Bank Poverty and Inequality Platform | World Bank poverty and inequality data platform. | Income / socioeconomic status | Verified |
| World Inequality Database | Income and wealth inequality data source. | Income / socioeconomic status | Verified |
| Luxembourg Income Study | Harmonized income microdata and inequality research data center. | Income / socioeconomic status | Verified, access may require registration |
| IPUMS CPS | Harmonized U.S. Current Population Survey microdata. | Employment / occupation / work; Income / socioeconomic status | Verified, U.S.-focused |

## Household, Family, And Migration

| Source | Source-level verification | Dimension-level support | Status |
| --- | --- | --- | --- |
| OECD Family Database | OECD indicators on family structure, fertility, children, household, and family policy. | Household / family / marital status | Verified, OECD-focused |
| DHS Program | Demographic and Health Surveys household and individual survey data across many countries. | Household / family / marital status; Health / disability / accessibility; Migration and demographic context | Verified, survey-focused |
| UNICEF Multiple Indicator Cluster Surveys | UNICEF household survey program covering children, households, health, education, and living conditions. | Household / family / marital status; Health / disability / accessibility; Education | Verified, survey-focused |
| UN International Migrant Stock | UN source for international migrant stock by origin and destination. | Migration / citizenship / country of birth | Verified |
| OECD migration data | OECD migration and immigrant integration data resources. | Migration / citizenship / country of birth; Employment / occupation / work | Verified, OECD-focused |
| World Bank Migration and Remittances | World Bank resources on migration, remittances, and diaspora issues. | Migration / citizenship / country of birth; Income / socioeconomic context | Verified |
| IPUMS International | Harmonized cross-national census microdata with household, family, birthplace, and migration variables. | Household / family / marital status; Migration / citizenship / country of birth | Verified, account/license may be required |

## Language, Culture, And Locale

| Source | Source-level verification | Dimension-level support | Status |
| --- | --- | --- | --- |
| Unicode CLDR | Unicode Common Locale Data Repository for locale, language, script, territory, and formatting metadata. | Language / locale / culture | Verified |
| CLDR project repository | Official CLDR GitHub repository for source data and project artifacts. | Language / locale / culture | Verified |
| Glottolog | Language taxonomy and language reference source. | Language / locale / culture | Verified |
| Glottolog downloads | Glottolog data download page for language taxonomy and metadata files. | Language / locale / culture | Verified |
| World Atlas of Language Structures | Structured cross-linguistic feature database. | Language / locale / culture | Verified |
| Ethnologue | Language reference source covering languages, speaker communities, and language status. | Language / locale / culture | Verified, access may be limited |

## Religion, Values, Politics, And Social Attitudes

| Source | Source-level verification | Dimension-level support | Status |
| --- | --- | --- | --- |
| Pew Research Center datasets | Public opinion survey datasets and reports from Pew Research Center. | Religion / religiosity; Values / politics / trust / social attitudes; Sex / gender survey demographics | Verified |
| Pew Research Center Religion | Pew religion reports and datasets on affiliation, belief, practice, and demographics. | Religion / religiosity | Verified |
| 2025 National Public Opinion Reference Survey | Pew NPORS dataset page for U.S. public opinion and demographics. | Values / politics / trust / social attitudes; Religion / religiosity; Survey demographics | Verified, U.S.-focused |
| 2023-24 Religious Landscape Study | Pew Religious Landscape Study dataset page. | Religion / religiosity; Household/family and demographic context | Verified, U.S.-focused |
| World Values Survey | Cross-national survey data on values, religion, trust, politics, and social attitudes. | Religion / religiosity; Values / politics / trust / social attitudes | Verified |
| World Values Survey Wave 7 documentation | WVS Wave 7 documentation and data access page. | Religion / religiosity; Values / politics / trust / social attitudes | Verified |
| General Social Survey | U.S. survey data on social attitudes, religion, politics, trust, and demographics. | Religion / religiosity; Values / politics / trust / social attitudes | Verified, U.S.-focused |
| GSS data access | GSS official data access page. | Religion / religiosity; Values / politics / trust / social attitudes | Verified, U.S.-focused |
| Association of Religion Data Archives | Religion data archive and metadata source. | Religion / religiosity | Verified |
| European Social Survey | Cross-national European survey data on attitudes, values, politics, trust, and demographics. | Values / politics / trust / social attitudes | Verified, Europe-focused |
| International Social Survey Programme | Cross-national social survey modules on work, family, religion, identity, politics, and social attitudes. | Values / politics / trust / social attitudes; Religion / religiosity; Household / family / marital status | Verified |
| Gallup World Poll | Global survey source for public opinion, wellbeing, and social indicators. | Values / politics / trust / social attitudes | Verified, restricted access |
| Afrobarometer | African public opinion survey source. | Values / politics / trust / social attitudes | Verified, region-focused |
| Arab Barometer | MENA public opinion survey source. | Values / politics / trust / social attitudes; Religion / religiosity | Verified, region-focused |
| Asian Barometer | Asian public opinion survey source. | Values / politics / trust / social attitudes | Verified, region-focused |
| Latinobarometro | Latin American public opinion survey source. | Values / politics / trust / social attitudes | Verified, region-focused |
| Eurobarometer | European Union public opinion survey source. | Values / politics / trust / social attitudes | Verified, Europe-focused |

## Personality And Psychometrics

| Source | Source-level verification | Dimension-level support | Status |
| --- | --- | --- | --- |
| International Personality Item Pool | Public-domain personality item and scale source. | Personality / psychometrics | Verified |
| SAPA Project | Online personality and ability assessment research project. | Personality / psychometrics | Verified |
| Midlife in the United States | Longitudinal U.S. study with psychosocial, personality, wellbeing, and health measures. | Personality / psychometrics; Health / disability / accessibility | Verified, U.S.-focused |

## Health, Disability, And Accessibility

| Source | Source-level verification | Dimension-level support | Status |
| --- | --- | --- | --- |
| WHO Global Health Observatory | Official WHO global health indicator portal. | Health / disability / accessibility | Verified |
| IHME Global Burden of Disease | Global, regional, and national disease burden and health metric source. | Health / disability / accessibility | Verified |
| CDC National Health Interview Survey | U.S. health interview survey source. | Health / disability / accessibility | Verified, U.S.-focused |
| CDC Behavioral Risk Factor Surveillance System | U.S. behavioral health and risk-factor survey source. | Health / disability / accessibility; Lifestyle / time use / consumption | Verified, U.S.-focused |

## Lifestyle, Time Use, And Consumption

| Source | Source-level verification | Dimension-level support | Status |
| --- | --- | --- | --- |
| American Time Use Survey | U.S. time-use survey from BLS. | Lifestyle / time use / consumption | Verified, U.S.-focused |
| Consumer Expenditure Surveys | U.S. household spending and consumption surveys from BLS. | Lifestyle / time use / consumption; Income / socioeconomic status | Verified, U.S.-focused |
| OECD Time Use Database | Cross-national time-use data from OECD. | Lifestyle / time use / consumption | Verified, OECD-focused |

## Technology And Developer Behavior

| Source | Source-level verification | Dimension-level support | Status |
| --- | --- | --- | --- |
| International Telecommunication Union statistics | Official ITU statistics on ICT access, mobile, broadband, and digital adoption. | Technology / internet access / digital behavior | Verified |
| DataReportal global digital reports | Public reports on global internet, social media, mobile, and digital adoption. | Technology / internet access / digital behavior | Verified, report-focused |
| Pew Internet & Technology | Pew survey reports on internet access, device use, and technology behavior. | Technology / internet access / digital behavior | Verified, U.S.-focused |
| Stack Overflow Survey | Developer survey source on languages, tools, AI, platforms, work, and demographics. | Technology / internet access / digital behavior; Developer / coding / technical tools | Verified, developer-focused |
| Stack Overflow Survey 2025 | 2025 Stack Overflow Survey report page. | Technology / internet access / digital behavior; Developer / coding / technical tools | Verified, developer-focused |
| GitHub Octoverse | GitHub report on developer ecosystem and platform trends. | Developer / coding / technical tools | Verified, platform/report-focused |
| JetBrains State of Developer Ecosystem Report 2025 | JetBrains developer ecosystem report covering developer tools, languages, AI, work, productivity, salary, and demographics. | Developer / coding / technical tools | Verified, developer-focused |
| JetBrains State of Developer Ecosystem Report 2024 | JetBrains 2024 developer ecosystem report and raw-data page. | Developer / coding / technical tools | Verified, developer-focused |
| CNCF Annual Survey | Cloud Native Computing Foundation survey/report source on cloud-native tools and practices. | Developer / coding / technical tools | Verified, developer/cloud-focused |

## Verification Templates

### Source-Level Verification Template

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

### Dimension-Level Verification Template

```text
Source:
Source-level verification:
Dimension-level support:
Status:
```
