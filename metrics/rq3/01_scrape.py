#!/usr/bin/env python3
"""Phase 1: scrape Moltbook posts and comments for each RQ2 agent.

Output: data/raw/{agent}.json

Endpoints (discovered by inspecting the live API and the public web client):

- Profile:  GET /api/v1/agents/{username}/profile
- Posts:    GET /api/v1/posts?author={username}&sort=new&limit=20
            (paginated via { has_more, next_cursor })
- Comments: GET /api/v1/agents/{username}/comments?limit=N
            (returns up to N rows; no cursor)
- Parent post body: GET /api/v1/posts/{post_id}

Each user-comment row only exposes its parent *post* (not parent comment),
so we treat the parent post body (title + content) as the parent_body for
the Mirror tone-matching analysis.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from typing import Any

from common import (
    AGENTS,
    DATA_RAW,
    MoltbookClient,
    make_client,
    parse_agent_arg,
    write_json,
)

POST_PAGE_SIZE = 50           # posts per request; well above any agent's count
COMMENT_BULK_LIMIT = 500      # comments are non-paginated; ask for plenty


def log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Pagination (posts)
# ---------------------------------------------------------------------------


def paginate_posts(client: MoltbookClient, username: str) -> list[dict[str, Any]]:
    """Yield all posts authored by `username` using cursor pagination."""
    out: list[dict[str, Any]] = []
    cursor: str | None = None
    pages = 0
    while True:
        params: dict[str, Any] = {
            "author": username,
            "sort": "new",
            "limit": POST_PAGE_SIZE,
        }
        if cursor:
            params["cursor"] = cursor
        resp = client.get("/posts", params=params)
        payload = resp.data or {}
        items = payload.get("posts") or []
        out.extend(items)
        pages += 1

        has_more = bool(payload.get("has_more"))
        next_cursor = payload.get("next_cursor")
        if not has_more or not next_cursor:
            return out
        cursor = next_cursor
        if pages > 200:
            raise RuntimeError(f"posts pagination runaway for {username}")


def fetch_comments(client: MoltbookClient, username: str) -> list[dict[str, Any]]:
    resp = client.get(
        f"/agents/{username}/comments", params={"limit": COMMENT_BULK_LIMIT}
    )
    payload = resp.data or {}
    return list(payload.get("comments") or [])


# ---------------------------------------------------------------------------
# Field extraction
# ---------------------------------------------------------------------------


def normalize_post(item: dict[str, Any]) -> dict[str, Any]:
    title = (item.get("title") or "").strip()
    content = (item.get("content") or "").strip()
    body = "\n\n".join(part for part in (title, content) if part)
    submolt = item.get("submolt") or {}
    return {
        "id": str(item.get("id") or ""),
        "type": "post",
        "title": title or None,
        "body": body,
        "created_at": item.get("created_at"),
        "parent_id": None,
        "parent_body": None,
        "score": item.get("score", item.get("upvotes", 0)),
        "upvotes": item.get("upvotes"),
        "downvotes": item.get("downvotes"),
        "comment_count": item.get("comment_count"),
        "submolt": submolt.get("name") if isinstance(submolt, dict) else submolt,
    }


def normalize_comment(item: dict[str, Any]) -> dict[str, Any]:
    post = item.get("post") or {}
    submolt = post.get("submolt") if isinstance(post, dict) else None
    submolt_name = (
        submolt.get("name") if isinstance(submolt, dict) else submolt
    )
    return {
        "id": str(item.get("id") or ""),
        "type": "comment",
        "title": None,
        "body": item.get("content") or "",
        "created_at": item.get("created_at"),
        "parent_id": str(post.get("id")) if isinstance(post, dict) and post.get("id") else None,
        "parent_post_title": post.get("title") if isinstance(post, dict) else None,
        "parent_body": None,  # filled in by parent resolver
        "score": item.get("score", (item.get("upvotes", 0) - item.get("downvotes", 0))),
        "upvotes": item.get("upvotes"),
        "downvotes": item.get("downvotes"),
        "submolt": submolt_name,
    }


# ---------------------------------------------------------------------------
# Parent post body resolution
# ---------------------------------------------------------------------------


def resolve_parent_post_body(
    client: MoltbookClient, post_id: str, cache: dict[str, str]
) -> str | None:
    if post_id in cache:
        return cache[post_id] or None
    resp = client.get(f"/posts/{post_id}")
    if resp.status == 404 or resp.data is None:
        cache[post_id] = ""
        return None
    data = resp.data
    # API may wrap as { success, post: {...} } or return the post directly.
    if isinstance(data, dict) and isinstance(data.get("post"), dict):
        data = data["post"]
    if not isinstance(data, dict):
        cache[post_id] = ""
        return None
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    merged = "\n\n".join(part for part in (title, content) if part)
    cache[post_id] = merged
    return merged or None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def fetch_profile(client: MoltbookClient, username: str) -> dict[str, Any]:
    resp = client.get(f"/agents/{username}/profile")
    data = resp.data or {}
    if isinstance(data, dict) and isinstance(data.get("agent"), dict):
        data = data["agent"]
    return {
        "id": data.get("id"),
        "username": data.get("name") or username,
        "display_name": data.get("display_name"),
        "description": data.get("description"),
        "karma": data.get("karma"),
        "follower_count": data.get("follower_count"),
        "following_count": data.get("following_count"),
        "posts_count": data.get("posts_count"),
        "comments_count": data.get("comments_count"),
        "fetched_at": dt.datetime.utcnow().isoformat() + "Z",
    }


def scrape_agent(
    client: MoltbookClient, username: str, parent_cache: dict[str, str]
) -> dict[str, Any]:
    log(f"[{username}] fetching profile")
    profile = fetch_profile(client, username)
    log(
        f"[{username}]   karma={profile.get('karma')} "
        f"posts={profile.get('posts_count')} comments={profile.get('comments_count')}"
    )

    log(f"[{username}] fetching posts")
    raw_posts = paginate_posts(client, username)
    log(f"[{username}]   {len(raw_posts)} posts")

    log(f"[{username}] fetching comments")
    raw_comments = fetch_comments(client, username)
    log(f"[{username}]   {len(raw_comments)} comments")

    posts = [normalize_post(p) for p in raw_posts]
    comments = [normalize_comment(c) for c in raw_comments]

    if comments:
        log(f"[{username}] resolving parent post bodies")
    for idx, c in enumerate(comments, 1):
        if c["parent_id"]:
            c["parent_body"] = resolve_parent_post_body(
                client, c["parent_id"], parent_cache
            )
        if idx % 25 == 0:
            log(f"[{username}]   resolved {idx}/{len(comments)}")

    utterances = posts + comments
    expected_total = (profile.get("posts_count") or 0) + (
        profile.get("comments_count") or 0
    )
    if expected_total and len(utterances) < expected_total:
        log(
            f"[{username}] WARNING: scraped {len(utterances)} utterances but "
            f"profile reports {expected_total} (posts_count + comments_count)"
        )

    return {
        "agent": username,
        "profile": profile,
        "utterances": utterances,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape Moltbook content for RQ2 agents.")
    ap.add_argument(
        "--agents",
        help=f"Comma-separated agents (default: {','.join(AGENTS)})",
        default=None,
    )
    ap.add_argument("--delay", type=float, default=0.5, help="Per-request delay (s)")
    ap.add_argument(
        "--force", action="store_true", help="Re-scrape even if output exists"
    )
    args = ap.parse_args()

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    client = make_client(delay=args.delay)
    parent_cache: dict[str, str] = {}

    targets = parse_agent_arg(args.agents)
    for username in targets:
        out_path = DATA_RAW / f"{username}.json"
        if out_path.exists() and not args.force:
            log(f"[{username}] skipping (exists; pass --force to re-scrape)")
            continue
        try:
            payload = scrape_agent(client, username, parent_cache)
        except Exception as exc:
            log(f"[{username}] FAILED: {exc}")
            raise
        write_json(out_path, payload)
        log(
            f"[{username}] wrote {out_path} ({len(payload['utterances'])} utterances)"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
