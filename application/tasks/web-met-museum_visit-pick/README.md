# Met Museum visit pick (Playwright)

PersonaBench **Playwright** web task on a live public site. Chromium is driven
through the **Playwright Python API** (DOM automation), and the persona browses
the Met's exhibitions and online collection to pick the one thing they would
prioritize seeing on a visit.

- URL: https://www.metmuseum.org/
- Output: `/app/output/visit_pick.json`

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
  -p application/tasks/web-met-museum_visit-pick
```

Oracle (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p application/tasks/web-met-museum_visit-pick -a oracle
```
