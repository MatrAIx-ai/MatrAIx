# Recommender agent chat task

You are a simulated user of a recommendation system. Act according to your
assigned persona.

The recommender application is available through a REST API sidecar named
`rec-agent-api`, reachable from this container at `http://rec-agent-api:8000`.
Use `curl` or a short script to have a real multi-turn conversation with the
recommender.

If `rec-agent-api` is unavailable, unhealthy, or fails during the conversation,
stop and fail the task. Do not simulate the recommender with any other model,
do not call external LLM APIs as a replacement recommender, and do not invent a
conversation or item ids.

For this smoke task, use the `movie` domain unless the run configuration tells
you otherwise. Based on your persona, decide what kind of item you realistically
want, what constraints matter to you, and what personal preferences should guide
recommendations. Do not reveal everything at once. Interact naturally, answer
follow-up questions, provide feedback on recommendations, and continue until you
can judge whether the recommendations satisfy your need.

**Endpoints**

| Method | Path | Body | Response |
| --- | --- | --- | --- |
| `GET` | `/health` | - | `{"status": "ok", ...}` |
| `POST` | `/v1/session` | `{"domain": "movie"}` | `{"sessionId": "...", "config": {...}, ...}` |
| `POST` | `/v1/messages` | `{"sessionId": "...", "message": "<your message>"}` | `{"reply": "...", "turn": {...}, "recommendedItems": [...]}` |
| `GET` | `/v1/conversation?sessionId=...` | - | `{"messages": [...], "turns": [...]}` |
| `GET` | `/v1/recommendations?sessionId=...` | - | `{"recommendedItems": [...], "total": 0}` |

You may omit `sessionId` on the first `/v1/messages` call and include
`{"domain": "movie"}`; the API will create a session automatically.

## Required work

1. Have at least three user turns and three assistant turns.
2. Try to get recommendations that fit your product need, constraints, and
   personal preferences.
3. Save the exact conversation artifact returned by `/v1/conversation` to
   `/app/output/transcript.json`.
4. Save the recommendation artifact to `/app/output/recommendation_result.json`.
5. If possible, save your post-interaction questionnaire to
   `/app/output/user_feedback.json`.

## Output schemas

`/app/output/transcript.json`:

```json
{
  "sessionId": "<string>",
  "domain": "movie",
  "messages": [
    {"role": "user", "content": "<string>"},
    {"role": "assistant", "content": "<string>"}
  ],
  "turns": [
    {
      "turnId": "<string>",
      "userMessage": "<string>",
      "assistantMessage": "<string>",
      "recommendedItems": [
        {"itemId": "<string>", "title": "<string>"}
      ]
    }
  ]
}
```

`/app/output/recommendation_result.json`:

```json
{
  "sessionId": "<string>",
  "domain": "movie",
  "recommendedItems": [
    {"itemId": "<string>", "title": "<string>"}
  ],
  "turnsToRecommendation": 3
}
```

`/app/output/user_feedback.json`:

This file must be a valid JSON object with these fields:

- `productNeedConstraintSatisfaction`: one of `"yes"`, `"partially"`, or
  `"no"`.
- `personalPreferenceSatisfaction`: one of `"yes"`, `"partially"`, or `"no"`.
- `overallExperienceRating`: an integer from 1 to 10.
- `reason`: a short string explaining the rating.
- `askedUsefulClarificationQuestions`: a boolean.

Use this rating scale for `overallExperienceRating`:

- 9-10: grounded recommendations satisfy the user's main need, hard constraints,
  and personal preferences with clear fit.
- 7-8: the run is useful overall; the main need is satisfied, with minor misses,
  extra steering, or imperfect explanations.
- 5-6: the run is usable but important constraints or preferences are only
  partly met.
- 3-4: the run mostly misses the need; at most one useful grounded item appears,
  or the agent needs repeated correction.
- 1-2: no usable grounded recommendation is produced, or the recommender API
  fails.

Make sure the JSON files are valid JSON. Do not invent item ids; use item ids
returned by `/v1/recommendations` or `/v1/messages`. The verifier requires
`recommendation_result.recommendedItems` to be grounded in
`transcript.turns[*].recommendedItems`.
