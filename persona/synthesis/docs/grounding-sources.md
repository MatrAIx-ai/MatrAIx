# Persona Graph Grounding Sources

This document collects real-world data sources used for grounding the Persona
Full DAG. It is intended as a lightweight reference for source review,
documentation, and follow-up validation.

## Dimension Reference Map

| Group | #Dim. | Subgroups | Reference sources |
| --- | ---: | --- | --- |
| Demographic information | 52 | Basic (25), Life Events (24), Cultural (2), Family (1) | UN World Population Prospects; UN Population Division; World Bank WDI; WorldPop; Eurostat; ACS PUMS; IPUMS; DHS; UNICEF MICS; OECD Family Database |
| Language and communication | 90 | Language (53), Communication (37) | ACS PUMS; IPUMS International; IPUMS USA; Pew Research Center; World Values Survey |
| Education and professional background | 90 | Academic (34), Learning Style (1), Career (4), Industry/Role (51) | UNESCO Institute for Statistics; World Bank Education Statistics; ILOSTAT; OECD Education at a Glance; OECD PISA; BLS OEWS; O*NET; ACS PUMS; IPUMS; IPUMS CPS |
| Expertise and skills | 387 | Domains (144), Skills (64), Tools (69), Programming (44), Developer/Coding (66) | ITU statistics; World Bank WDI; DataReportal; Pew Internet & Technology; Stack Overflow Survey; GitHub Octoverse; JetBrains State of Developer Ecosystem; O*NET |
| Personality | 90 | Character (34), Big Five (50), MBTI (2), Relationships (4) | IPIP; MIDUS |
| Values and worldview | 120 | Risk & Decision (7), Values & Motivation (46), Beliefs (67) | Pew Research Center Religion; World Values Survey; General Social Survey; European Social Survey; ISSP; Gallup World Poll; Afrobarometer; Arab Barometer; Asian Barometer; Latinobarometro; Eurobarometer; ARDA |
| Health and accessibility | 29 | Physical Health (25), Fitness (2), Health Lifestyle (2) | WHO Global Health Observatory; IHME Global Burden of Disease; ACS PUMS; CDC NHIS; CDC BRFSS; DHS Program; UNICEF MICS |
| Behavior and interaction state | 74 | Emotional State (5), Time (3), Preferences (34), Work (2), Habits (30) | American Time Use Survey; Consumer Expenditure Surveys; OECD Time Use Database; ITU statistics; DataReportal; Pew Internet & Technology |
| Interests and culture | 358 | Topics (78), Culture (74), Media (81), Food (35), Sports (40), Hobbies (50) | American Time Use Survey; Consumer Expenditure Surveys; OECD Time Use Database; Pew Research Center; World Values Survey; Gallup World Poll |

## Source Catalog

### Population And Demographics

- UN World Population Prospects: https://population.un.org/wpp/
- UN Population Division Data Portal: https://population.un.org/dataportal/
- UN World Urbanization Prospects: https://population.un.org/wup/
- World Bank World Development Indicators: https://databank.worldbank.org/source/world-development-indicators
- World Bank DataBank: https://databank.worldbank.org/
- WorldPop: https://www.worldpop.org/
- Eurostat: https://ec.europa.eu/eurostat
- U.S. Census ACS PUMS: https://www.census.gov/programs-surveys/acs/microdata.html
- ACS data portal: https://www.census.gov/programs-surveys/acs/data.html
- IPUMS: https://www.ipums.org/
- IPUMS International: https://international.ipums.org/international/
- IPUMS USA: https://usa.ipums.org/usa/
- Ethnologue: https://www.ethnologue.com/

### Education, Work, And Socioeconomics

- UNESCO Institute for Statistics: https://uis.unesco.org/
- World Bank Education Statistics: https://databank.worldbank.org/source/education-statistics
- ILOSTAT data: https://ilostat.ilo.org/data/ (interactive explorer: https://rplumber.ilo.org/dataexplorer/?lang=en)
- BLS Occupational Employment and Wage Statistics: https://www.bls.gov/oes/
- OEWS data overview: https://www.bls.gov/oes/tables.htm
- O*NET database releases: https://www.onetcenter.org/database.html (Resource Center: https://www.onetcenter.org/)
- OECD employment data: https://www.oecd.org/employment/
- OECD Education at a Glance: https://www.oecd.org/education/education-at-a-glance/
- OECD PISA: https://www.oecd.org/pisa/
- OECD Income and Wealth Distribution Database: https://www.oecd.org/en/data/datasets/income-and-wealth-distribution-database.html
- World Bank Poverty and Inequality Platform: https://pip.worldbank.org/
- World Inequality Database: https://wid.world/
- Luxembourg Income Study: https://www.lisdatacenter.org/
- IPUMS CPS: https://cps.ipums.org/cps/

### Household, Family, And Migration

- OECD Family Database: https://www.oecd.org/en/data/datasets/oecd-family-database.html
- DHS Program: https://dhsprogram.com/
- UNICEF Multiple Indicator Cluster Surveys: https://mics.unicef.org/
- UN International Migrant Stock: https://www.un.org/development/desa/pd/content/international-migrant-stock
- OECD migration data: https://www.oecd.org/migration/
- World Bank Migration & Labor Mobility: https://www.worldbank.org/ext/en/topic/social-protection/migration
- World Bank Remittances / KNOMAD: https://www.worldbank.org/en/topic/migration/brief/remittances-knomad
- IPUMS International: https://international.ipums.org/international/

### Religion, Values, Politics, And Social Attitudes

- Pew Research Center datasets: https://www.pewresearch.org/datasets/
- Pew Research Center Religion: https://www.pewresearch.org/religion/
- 2025 National Public Opinion Reference Survey: https://www.pewresearch.org/dataset/2025-national-public-opinion-reference-survey-npors/
- 2023-24 Religious Landscape Study: https://www.pewresearch.org/dataset/2023-24-religious-landscape-study-rls-dataset/
- World Values Survey Wave 7 documentation: https://www.worldvaluessurvey.org/WVSDocumentationWV7.jsp (main site: https://www.worldvaluessurvey.org/)
- General Social Survey: https://gss.norc.org/
- GSS data access: https://gss.norc.org/get-the-data.html
- Association of Religion Data Archives: https://www.thearda.com/
- European Social Survey: https://www.europeansocialsurvey.org/
- International Social Survey Programme: https://issp.org/
- Gallup World Poll: https://www.gallup.com/analytics/318875/global-research.aspx
- Afrobarometer: https://www.afrobarometer.org/
- Arab Barometer: https://www.arabbarometer.org/
- Asian Barometer: https://www.asianbarometer.org/
- Latinobarometro: https://www.latinobarometro.org/
- Eurobarometer: https://europa.eu/eurobarometer/

### Personality And Psychometrics

- International Personality Item Pool: https://ipip.ori.org/
- Midlife in the United States: https://midus.wisc.edu/

### Health, Disability, And Accessibility

- WHO Global Health Observatory: https://www.who.int/data/gho
- IHME Global Burden of Disease: https://www.healthdata.org/research-analysis/gbd
- CDC National Health Interview Survey: https://www.cdc.gov/nchs/nhis/
- CDC Behavioral Risk Factor Surveillance System: https://www.cdc.gov/brfss/

### Lifestyle, Time Use, And Consumption

- American Time Use Survey: https://www.bls.gov/tus/
- Consumer Expenditure Surveys: https://www.bls.gov/cex/
- OECD Time Use Database: https://www.oecd.org/en/data/datasets/time-use-database.html

### Technology And Developer Behavior

- International Telecommunication Union statistics: https://www.itu.int/itu-d/reports/statistics/
- DataReportal global digital reports: https://datareportal.com/
- Pew Internet & Technology: https://www.pewresearch.org/internet/
- Stack Overflow Survey: https://survey.stackoverflow.co/
- GitHub Octoverse: https://octoverse.github.com/
- JetBrains State of Developer Ecosystem: https://devecosystem-2025.jetbrains.com/

## Source Reference Keys

These shorthand keys identify the grounding sources referenced above.

- `acs_data_portal`: U.S. Census ACS data portal
- `acs_pums_2024_1yr`: U.S. Census ACS PUMS
- `afrobarometer`: Afrobarometer
- `arab_barometer`: Arab Barometer
- `arda`: Association of Religion Data Archives
- `asian_barometer`: Asian Barometer
- `bls_oews_may2025`: BLS Occupational Employment and Wage Statistics
- `cdc_brfss`: CDC Behavioral Risk Factor Surveillance System
- `cdc_nhis`: CDC National Health Interview Survey
- `consumer_expenditure_surveys`: Consumer Expenditure Surveys
- `datareportal`: DataReportal global digital reports
- `dhs_program`: DHS Program
- `ethnologue`: Ethnologue
- `eurobarometer`: Eurobarometer
- `european_social_survey`: European Social Survey
- `eurostat`: Eurostat
- `gallup_world_poll`: Gallup World Poll
- `github_octoverse`: GitHub Octoverse
- `gss_1972_2024`: General Social Survey
- `ihme_gbd`: IHME Global Burden of Disease
- `ilostat`: ILOSTAT
- `ipip`: International Personality Item Pool
- `ipums`: IPUMS
- `ipums_cps`: IPUMS CPS
- `ipums_international`: IPUMS International
- `ipums_usa`: IPUMS USA
- `issp`: International Social Survey Programme
- `itu_statistics`: International Telecommunication Union statistics
- `jetbrains_developer_ecosystem`: JetBrains State of Developer Ecosystem
- `latinobarometro`: Latinobarometro
- `luxembourg_income_study`: Luxembourg Income Study
- `midus`: Midlife in the United States
- `onet_30_3`: O*NET 30.3
- `oecd_education_at_a_glance`: OECD Education at a Glance
- `oecd_employment`: OECD employment data
- `oecd_family_database`: OECD Family Database
- `oecd_income_distribution_database`: OECD Income and Wealth Distribution Database
- `oecd_migration`: OECD migration data
- `oecd_pisa`: OECD PISA
- `oecd_time_use_database`: OECD Time Use Database
- `pew_npors_2025`: Pew 2025 National Public Opinion Reference Survey
- `pew_research_center`: Pew Research Center datasets
- `pew_religion`: Pew Research Center Religion
- `pew_technology`: Pew Internet & Technology
- `pew_rls_2023_2024`: Pew 2023-24 Religious Landscape Study
- `un_wpp_2024`: UN World Population Prospects 2024
- `un_world_urbanization_prospects`: UN World Urbanization Prospects
- `un_international_migrant_stock`: UN International Migrant Stock
- `unesco_uis`: UNESCO Institute for Statistics
- `unicef_mics`: UNICEF Multiple Indicator Cluster Surveys
- `who_gho`: WHO Global Health Observatory
- `world_bank_databank`: World Bank DataBank
- `world_bank_education_statistics`: World Bank Education Statistics
- `world_bank_migration_labor_mobility`: World Bank Migration & Labor Mobility
- `world_bank_remittances_knomad`: World Bank Remittances / KNOMAD
- `world_bank_pip`: World Bank Poverty and Inequality Platform
- `world_bank_wdi`: World Bank World Development Indicators
- `world_inequality_database`: World Inequality Database
- `worldpop`: WorldPop
- `wvs_wave7_csv_v6_0`: World Values Survey Wave 7
- `stackoverflow_survey`: Stack Overflow Survey
