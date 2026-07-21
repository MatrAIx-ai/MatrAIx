# Open Library book choice (Playwright)

PersonaBench **Playwright** web task on a live public site. Chromium is driven
through the **Playwright Python API** (DOM automation), and the persona browses
the Open Library catalog to pick the one book they would most want to read next.

- URL: https://openlibrary.org/
- Output: `/app/output/book_choice.json`

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
  -p application/tasks/web-openlibrary_book-choice
```

Oracle (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p application/tasks/web-openlibrary_book-choice -a oracle
```
