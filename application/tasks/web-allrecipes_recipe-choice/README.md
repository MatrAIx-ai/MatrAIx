# AllRecipes recipe choice (Playwright)

PersonaBench **Playwright** web task on a live public site. Chromium is driven
through the **Playwright Python API** (DOM automation), and the persona browses
AllRecipes to pick the one recipe they would most realistically cook this week.

- URL: https://www.allrecipes.com/
- Output: `/app/output/recipe_choice.json`

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
  -p application/tasks/web-allrecipes_recipe-choice
```

Oracle (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p application/tasks/web-allrecipes_recipe-choice -a oracle
```
