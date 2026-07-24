# awesome-selfhosted note-tool comparison (Playwright)

MatrAIx **Playwright** web task using the live, public HTML edition of
awesome-selfhosted. The user reviews the **Note-taking & Editors** category,
compares three self-hosted open-source tools in more depth, and selects the one
they would most realistically try.

- Start URL: https://awesome-selfhosted.net/tags/note-taking--editors.html
- Output: `/app/output/selfhosted_note_tool_comparison.json`
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
  -p application/tasks/web-awesome-selfhosted-note-tool-comparison
```

Oracle (live Playwright browsing; needs outbound network):

```bash
uv run harbor run \
  -p application/tasks/web-awesome-selfhosted-note-tool-comparison \
  -a oracle
```

The verifier checks the category identity, minimum review count, three-item
shortlist, distinct project/source URLs, and internal consistency between the
selected project and shortlist. Persona alignment is reported separately from
objective completion; there is no single globally correct project.

## Known limitations

awesome-selfhosted and the linked project sites are live dependencies. Project
descriptions, maintenance dates, deployment labels, licenses, and external
links can change without notice. In accordance with the live-web contract, the
verifier validates the submission schema and internal consistency rather than
making a second network request against mutable pages.
