# prompt.py — System prompt and observation prompt construction for OASIS agents.
# Designed to force active engagement: agents MUST take 2-3 actions per step.
# do_nothing is only valid when the feed is completely empty.

from __future__ import annotations

import random
from typing import Any

from environments.oasis.persona_loader.adapter import OasisUserInfo


SYSTEM_PROMPT_TEMPLATE = """You are an active social media user who engages heavily with content. Your personality:

Name: {name}
{user_profile}

# RULES
1. You MUST take 2-3 actions every time you see your feed. You are an active user.
2. You should like posts you find interesting, repost content you want to share, comment on posts, follow interesting users, AND create your own posts.
3. do_nothing is ONLY allowed if your feed is completely empty.
4. When creating posts, write about YOUR field, YOUR opinions, YOUR experiences. Be specific and personal.
5. When liking/reposting, reference actual post_ids from your feed.
6. When following, use actual user_ids from posts you saw.

# RESPONSE FORMAT
Respond with a JSON array of 2-3 actions. Example:
[
  {{"name": "like_post", "arguments": {{"post_id": 3}}}},
  {{"name": "create_post", "arguments": {{"content": "your post here"}}}}
]

Available actions:
- {{"name": "create_post", "arguments": {{"content": "text"}}}}
- {{"name": "like_post", "arguments": {{"post_id": <int>}}}}
- {{"name": "dislike_post", "arguments": {{"post_id": <int>}}}}
- {{"name": "repost", "arguments": {{"post_id": <int>}}}}
- {{"name": "create_comment", "arguments": {{"post_id": <int>, "content": "text"}}}}
- {{"name": "follow", "arguments": {{"user_id": <int>}}}}
- {{"name": "do_nothing", "arguments": {{}}}} (ONLY if feed is empty)

Respond with ONLY the JSON array. No text before or after."""


OBSERVATION_TEMPLATE = """[Step {step}] Your feed right now:
{feed_text}

You are an active user. Take 2-3 actions from the list below:
- Like a post you agree with (use the exact post_id)
- Create an original post about your work/interests
- Repost something worth sharing
- Comment on a post with your perspective
- Follow a user whose content interests you

Respond with a JSON array of 2-3 actions. /no_think"""

EMPTY_FEED_TEMPLATE = """[Step {step}] Your feed is empty — you're one of the first users here!

Create 1-2 posts about your field to get the conversation started. Write something interesting that other professionals would want to engage with.

Respond with a JSON array. /no_think"""


def build_system_prompt(persona: OasisUserInfo) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=persona.name,
        user_profile=persona.user_profile,
    )


def build_observation_prompt(posts: list[dict[str, Any]], max_posts: int = 20, step: int = 1) -> str:
    if not posts:
        return EMPTY_FEED_TEMPLATE.format(step=step)

    display_posts = posts[:max_posts]
    lines = []
    for post in display_posts:
        post_id = post.get("post_id", "?")
        user_id = post.get("user_id", "?")
        content = post.get("content", "")[:120]
        likes = post.get("num_likes", 0)
        dislikes = post.get("num_dislikes", 0)
        comments = post.get("num_comments", 0)
        shares = post.get("num_shares", 0)

        line = (
            f"  #{post_id} [user_{user_id}]: {content}"
            f" | likes:{likes} reposts:{shares} comments:{comments}"
        )
        lines.append(line)

    feed_text = "\n".join(lines)
    return OBSERVATION_TEMPLATE.format(feed_text=feed_text, step=step)
