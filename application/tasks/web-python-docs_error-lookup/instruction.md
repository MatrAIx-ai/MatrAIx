# Python docs error lookup

Use the official Python documentation:

https://docs.python.org/

Act as the assigned persona. Find the docs needed to answer this question:

What Python `pathlib.Path` method reads a text file into a string, and how
should a user think about the `encoding` argument?

Do not use random blog posts or Q&A sites. Use official Python documentation or
official Python docs pages linked from the docs site.

Write your result to `/app/output/python_docs_lookup.json`:

```json
{
  "source_url": "<official docs.python.org page you used>",
  "topic": "pathlib.Path.read_text",
  "answer_summary": "<plain-language answer grounded in the docs>",
  "documentation_confidence": 1,
  "ease_of_lookup": 1,
  "would_reuse_docs": true,
  "friction_points": ["<where the docs helped or created friction>"]
}
```

Ratings must be integers from 1 to 10. `would_reuse_docs` must be true or false.

Suggested agent: `persona-openhands-sdk` (terminal + Python).
