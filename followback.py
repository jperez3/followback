from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Iterable

import requests


class RateLimitError(Exception):
    """Raised when the Instagram API returns a 429 Too Many Requests."""


def _build_session(sessionid: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0",
            "X-IG-App-ID": "936619743392459",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.instagram.com/",
        }
    )
    session.cookies.set("sessionid", sessionid)
    return session


def _fetch_user_id(session: requests.Session, username: str) -> str:
    response = session.get(
        "https://i.instagram.com/api/v1/users/web_profile_info/",
        params={"username": username},
        timeout=30,
    )
    response.raise_for_status()
    user = response.json().get("data", {}).get("user")
    if not user or "id" not in user:
        raise ValueError(f"Could not find user '{username}'")
    return str(user["id"])


def _fetch_user_profile(session: requests.Session, username: str) -> tuple[int, bool]:
    """Return (follower_count, is_business) for the given username.

    Uses the web_profile_info endpoint. "is_business_account" or
    "is_professional_account" indicate a business/professional account and will
    cause `is_business` to be True.

    Raises ValueError if the profile or follower count cannot be determined.
    """
    response = session.get(
        "https://i.instagram.com/api/v1/users/web_profile_info/",
        params={"username": username},
        timeout=30,
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        # Convert 429 responses into a RateLimitError so callers can handle them specially
        if response.status_code == 429:
            raise RateLimitError("rate limit hit") from exc
        raise
    user = response.json().get("data", {}).get("user")
    if not user:
        raise ValueError(f"Could not find user '{username}' when fetching profile")

    # follower count shapes
    edge = user.get("edge_followed_by")
    if isinstance(edge, dict) and "count" in edge:
        count = int(edge["count"])
    elif "follower_count" in user:
        count = int(user["follower_count"])
    else:
        raise ValueError(f"Could not determine follower count for '{username}'")

    is_business = bool(user.get("is_business_account")) or bool(user.get("is_professional_account"))

    return count, is_business


def _fetch_friendship_usernames(
    session: requests.Session,
    user_id: str,
    endpoint: str,
) -> set[str]:
    usernames: set[str] = set()
    next_max_id: str | None = None

    while True:
        # `count` is an int but `max_id` (when present) is a str, so use a union-typed mapping
        params: dict[str, int | str] = {"count": 200}
        if next_max_id:
            params["max_id"] = next_max_id

        response = session.get(
            f"https://i.instagram.com/api/v1/friendships/{user_id}/{endpoint}/",
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()

        for user in payload.get("users", []):
            username = user.get("username")
            if username:
                usernames.add(username)

        next_max_id = payload.get("next_max_id")
        if not payload.get("next_max_id"):
            break

    return usernames


def get_followers_and_following(
    username: str, sessionid: str, session: requests.Session | None = None
) -> tuple[set[str], set[str]]:
    """Return (followers, following) for username. If a session is provided it will be reused.

    Reusing the session avoids re-authenticating for subsequent per-user profile requests.
    """
    if session is None:
        session = _build_session(sessionid)
    user_id = _fetch_user_id(session, username)
    followers = _fetch_friendship_usernames(session, user_id, "followers")
    following = _fetch_friendship_usernames(session, user_id, "following")
    return followers, following


def find_not_following_back(
    followers: Iterable[str],
    following: Iterable[str],
) -> list[str]:
    return sorted(set(following) - set(followers))


def find_following_back(
    followers: Iterable[str],
    following: Iterable[str],
) -> list[str]:
    return sorted(set(following) & set(followers))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Show Instagram accounts a user follows that do not follow back",
    )
    parser.add_argument("username", help="Instagram username to inspect")
    parser.add_argument(
        "--sessionid",
        default=os.getenv("INSTAGRAM_SESSIONID"),
        help="Instagram sessionid cookie (or set INSTAGRAM_SESSIONID)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--opposite",
        action="store_true",
        help="Show accounts the user follows that DO follow back, instead of ones that don't",
    )
    args = parser.parse_args()

    if not args.sessionid:
        raise SystemExit("Missing sessionid. Pass --sessionid or set INSTAGRAM_SESSIONID.")

    # configure logging early so any errors are visible when --debug is passed
    logger = logging.getLogger(__name__)
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)

    # build a single session and reuse it for per-user profile checks
    session = _build_session(args.sessionid)
    followers, following = get_followers_and_following(args.username, args.sessionid, session=session)

    finder = find_following_back if args.opposite else find_not_following_back

    for user in finder(followers, following):
        try:
            # fetch profile info once and filter out business/professional accounts
            count, is_business = _fetch_user_profile(session, user)
        except RateLimitError:
            # If the API rate limits us, print a clear message and stop the script.
            print("Error: rate limit hit (received HTTP 429). Stopping.", file=sys.stderr)
            return 1
        except Exception as exc:
            # Catch other exceptions during profile fetch and continue with other users.
            # Log the exception at debug so it can be inspected when running with --debug.
            logger.debug("skipping user %s due to error fetching profile: %s", user, exc, exc_info=args.debug)
            continue
        if is_business:
            continue
        if count < 10_000:
            print(user)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
