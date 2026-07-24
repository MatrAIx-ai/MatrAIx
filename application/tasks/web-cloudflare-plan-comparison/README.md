# Cloudflare plan comparison (Playwright)

MatrAIx **Playwright** web task on the live public Cloudflare pricing page. The
participant compares all four **Network & CDN** plans and recommends the one
that best fits their organization.

- Start URL: https://www.cloudflare.com/plans/
- Output: `/app/output/cloudflare_plan_comparison.json`
- Authentication: none
- External side effects: none

See [Application Tasks](../README.md) for contribution guidance.

## Suggested setup (non-binding)

| Field | Value |
|-------|-------|
| Agent | `persona-openhands-sdk` |
| Environment | `docker` (Playwright image, `network_mode = "public"`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/web-cloudflare-plan-comparison
```

Oracle (live Playwright browsing; needs outbound network):

```bash
uv run harbor run \
  -p application/tasks/web-cloudflare-plan-comparison \
  -a oracle
```

The verifier checks the four canonical plan identities, the exact Network &
CDN category and source URL, and internal consistency between the selected plan
and the submitted comparison. Context-sensitive alignment is reported
separately from objective task completion; there is no single globally correct
plan.

## Known limitations

Cloudflare can change plan prices, billing language, audience descriptions, or
feature tables without notice. Agents must read those values from the rendered
live page. In accordance with the live-web contract, the verifier validates the
submission schema and internal consistency rather than making a second network
request to compare the artifact against a mutable page.
