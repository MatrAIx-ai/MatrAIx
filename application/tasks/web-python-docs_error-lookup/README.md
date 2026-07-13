# Python Docs Error Lookup

PersonaBench web task on the official Python documentation. The persona agent
uses the docs to answer a concrete usage question and reports whether the docs
were understandable for their background.

- URL: https://docs.python.org/
- Output: `/app/output/python_docs_lookup.json`

No login or external account is required.

## Suggested Setup

| Field | Value |
|---|---|
| Agent | `persona-openhands-sdk` |
| Environment | `docker` (Playwright image, `network_mode = "public"`) |
| Persona | `persona/datasets/bench-dev-sample/persona_0042.yaml` |

```bash
uv run harbor run \
  -a persona-openhands-sdk \
  -m anthropic/claude-sonnet-4-6 \
  --ak persona_path=persona/datasets/bench-dev-sample/persona_0042.yaml \
  -p application/tasks/web-python-docs_error-lookup
```

Oracle check (Playwright fetch; needs outbound network):

```bash
uv run harbor run -p application/tasks/web-python-docs_error-lookup -a oracle
```

## Expected Submission

```json
{
  "source_url": "https://docs.python.org/3/library/pathlib.html",
  "topic": "pathlib.Path.read_text",
  "answer_summary": "Path.read_text reads a text file and accepts an encoding argument.",
  "documentation_confidence": 8,
  "ease_of_lookup": 7,
  "would_reuse_docs": true,
  "friction_points": ["The page is dense for a beginner"]
}
```
