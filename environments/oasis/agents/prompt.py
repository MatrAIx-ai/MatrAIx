# prompt.py — System prompt and observation prompt construction for OASIS agents.
# Matches OASIS's UserInfo.to_system_message() + SocialEnvironment.to_text_prompt().
# The system prompt carries persona identity; the observation prompt carries the feed state.

from __future__ import annotations

from typing import Any

from environments.oasis.persona_loader.adapter import OasisUserInfo


SYSTEM_PROMPT_TEMPLATE = """You are a social media user. Your actions must be consistent with your personality and profile described below.

# WHO YOU ARE
Name: {name}
{user_profile}

# OBJECTIVE
You will be shown posts from your social media feed. After reviewing them, choose actions that reflect your personality, interests, and current mood. You may create posts, like, comment, repost, follow users, or do nothing.

# RESPONSE METHOD
Respond by calling one or more of the available tool functions. Pick actions that best reflect your current inclination based on your profile and the posts you see. Do not limit yourself to just liking posts — express yourself naturally."""


OBSERVATION_TEMPLATE = """Here is your social media feed right now:

{feed_text}

Based on your personality and interests, choose what actions to take. You can perform multiple actions or choose do_nothing if nothing interests you."""


def build_system_prompt(persona: OasisUserInfo) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=persona.name,
        user_profile=persona.user_profile,
    )


def build_observation_prompt(posts: list[dict[str, Any]], max_posts: int = 20) -> str:
    if not posts:
        feed_text = "Your feed is empty. No posts to see right now. You may want to create a post or search for content."
        return OBSERVATION_TEMPLATE.format(feed_text=feed_text)

    display_posts = posts[:max_posts]
    lines = []
    for post in display_posts:
        post_id = post.get("post_id", "?")
        user_id = post.get("user_id", "?")
        content = post.get("content", "")
        likes = post.get("num_likes", 0)
        dislikes = post.get("num_dislikes", 0)
        comments = post.get("num_comments", 0)
        shares = post.get("num_shares", 0)

        line = (
            f"[Post #{post_id} by user {user_id}] "
            f"{content} "
            f"(likes: {likes}, dislikes: {dislikes}, comments: {comments}, reposts: {shares})"
        )
        lines.append(line)

    feed_text = "\n".join(lines)
    return OBSERVATION_TEMPLATE.format(feed_text=feed_text)
