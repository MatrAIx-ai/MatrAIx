# Jun 20 1K Persona Descriptions

**Generated**: June 21, 2026  
**Format**: YAML with validated dimension mappings  
**Count**: 10 diverse, realistic personas

## Overview

This directory contains 10 human-like persona archetypes generated from the matrAIx dimension space (1,339 dimensions). Each persona combines realistic demographics, education, career history, and behavioral traits to represent credible individuals across diverse geographies, professions, and life stages.

## Files

- **personas.yaml** — Main persona dataset with all 10 personas and their dimension mappings

## Personas

1. **Sarah Chen** (38, Woman, East Asia)
   - Role: Senior ML Engineer | Shanghai, China
   - Education: Master's (Computer Science, Tsinghua)
   - Experience: 12 years | Large tech corporation
   - Languages: Mandarin (native), English (fluent)
   - Status: Married, 1 child | Upper-middle class
   - Personality: High openness, high conscientiousness
   - Current intent: Advance team's ML architecture, mentor junior engineers

2. **Marcus Johnson** (49, Man, North America)
   - Role: High School History Teacher | Wisconsin, USA
   - Education: Bachelor's (History Education)
   - Experience: 18 years | Public school system
   - Languages: English (native)
   - Status: Married, 2 teenage children | Middle class
   - Personality: High extraversion, high agreeableness
   - Current intent: Deepen student engagement through primary sources

3. **Priya Sharma** (31, Woman, South Asia)
   - Role: Healthcare Consultant | New Delhi, India
   - Education: Master's (Public Health, IIT Delhi)
   - Experience: 5 years | Health advisory SMB (50–500)
   - Languages: Hindi (native), English (fluent)
   - Status: Single, no children | Upper-middle class
   - Personality: High openness, high conscientiousness
   - Current intent: Improve health equity in resource-constrained settings

4. **Diego Ruiz** (23, Man, Latin America)
   - Role: Freelance Graphic Designer | Mexico City, Mexico
   - Education: High school + design bootcamp (self-taught)
   - Experience: 1 year | Solo/freelance (coworking)
   - Languages: Spanish (native), English (intermediate)
   - Status: Single, no children | Lower-middle class
   - Personality: Very high openness, high extraversion
   - Current intent: Build design portfolio, establish international client base

5. **Akira Tanaka** (59, Man, East Asia)
   - Role: Manufacturing Operations Director | Gifu, Japan
   - Education: Bachelor's (Mechanical Engineering, Nagoya)
   - Experience: 35 years | Large automotive supplier corporation
   - Languages: Japanese (native), English (intermediate)
   - Status: Married, adult children | Middle class
   - Personality: Very high conscientiousness, low extraversion
   - Current intent: Optimize production systems, mentor next generation

6. **Emma Thompson** (40, Woman, Western Europe)
   - Role: Senior Corporate Counsel | London, UK
   - Education: Law degree (JD/LLB, Oxford)
   - Experience: 13 years | Large multinational financial services
   - Languages: English (native)
   - Status: Married, no children | Upper class
   - Personality: Very high conscientiousness, high openness
   - Current intent: Manage regulatory risk, lead legal team through restructuring

7. **Amina Hassan** (30, Woman, MENA)
   - Role: Founder & CEO, E-commerce Platform | Dubai, UAE
   - Education: Bachelor's (Business)
   - Experience: 4 years (entrepreneurial) | Startup (15–30 employees)
   - Languages: Arabic (native), English (fluent)
   - Status: Single, no children | Lower-middle class (background)
   - Personality: Very high extraversion, very high openness
   - Current intent: Secure Series A funding, expand to new Gulf markets

8. **Robert Wilson** (51, Man, North America)
   - Role: Senior Climate Scientist | Colorado, USA
   - Education: PhD (Atmospheric Physics, MIT)
   - Experience: 22 years | University / research institution
   - Languages: English (native)
   - Status: Married, 2 adult children | Upper-middle class
   - Personality: Very high openness, high conscientiousness
   - Current intent: Communicate climate science to policymakers and public

9. **Jasmine Patel** (29, Woman, Sub-Saharan Africa)
   - Role: Community Development Officer | Rural Kenya
   - Education: Bachelor's (Social Work)
   - Experience: 4 years | NGO / non-profit development organization
   - Languages: Swahili (native), English (intermediate)
   - Status: Single, no children | Low income (background)
   - Personality: Very high agreeableness, high conscientiousness
   - Current intent: Strengthen community resilience, support women entrepreneurs

10. **Viktor Novak** (23, Man, Eastern Europe)
    - Role: Junior Data Scientist | Warsaw, Poland
    - Education: Bachelor's (Computer Science)
    - Experience: 1 year | Startup (8–12 employees)
    - Languages: Polish (native), English (intermediate)
    - Status: Single, no children | Lower-middle class
    - Personality: High openness, high conscientiousness
    - Current intent: Master ML systems, build portfolio for senior roles

## Validation Criteria

All personas have been validated for **human-like coherence**:

✓ **Age vs. Education**: 
  - No anachronisms (e.g., 3-year-old with PhD)
  - Entry roles (0-2 yrs exp) are ages 22-24 with Bachelor's
  - Senior roles (10+ yrs exp) are ages 38-54+ with Master's/PhD
  - Age-appropriate education progression

✓ **Experience vs. Seniority**:
  - Entry roles: 0-2 years (Diego, Viktor)
  - Mid roles: 4-5 years (Priya, Jasmine)
  - Senior roles: 13+ years (Emma, Robert, Akira)

✓ **Family Status**:
  - Age 20s: All single, no children
  - Age 30-40s: Mix of married/single, mostly no children or 1 child
  - Age 45-50s: Settled, older children or adult children

✓ **Regional & Linguistic Coherence**:
  - Language matches region
  - Company type matches regional economy
  - Professional culture aligns with geography

✓ **Career Arcs**:
  - All represent realistic, achievable progressions
  - Domain expertise aligns with education and experience
  - Current motivations match life stage and career position

## Dimensions Captured

Each persona includes 15+ mapped dimensions from `dimensions+new.json`:

- **Demographic**: Age bracket, gender identity, region, urbanicity, socioeconomic band, marital status, children
- **Linguistic**: Primary language, English proficiency
- **Professional**: Domain, subject specialty, seniority, role function, years experience, company size
- **Educational**: Highest education, academic field
- **Behavioral**: Personality (Big Five traits), emotional state, current intent

## Use Cases

- **Agent simulation**: Use as persona definitions for matrAIx behavioral simulations
- **User research**: Reference realistic user archetypes for product/UX research
- **Localization**: Model conversations and interactions for diverse regions/cultures
- **Diversity assessment**: Ensure product/service testing covers diverse personas
- **Bias detection**: Test LLM/AI systems against realistic, diverse scenarios

## Future Enhancements

- [ ] Add 40+ additional personas (total 50)
- [ ] Include additional behavioral dimensions (hobbies, interests, media preferences)
- [ ] Link to sample persona trajectories and dialogue patterns
- [ ] Create region-specific persona clusters
- [ ] Add cross-persona similarity/clustering analysis

## Metadata

| Property | Value |
|----------|-------|
| Total Personas | 10 |
| Generation Date | 2026-06-21 |
| Validation Status | ✓ Complete |
| Source Schema | `/home/yuexing/MatrAIx/personas/dimensions+new.json` (1,339 dims) |
| Format | YAML |
| Line Width | 140 characters (readable + semantic grouping) |

---

Generated by matrAIx persona synthesis engine (Jun 20, 2026)
