#!/usr/bin/env python3
"""Fetch GitHub + App Store stats and write them into dark_mode.svg / light_mode.svg.

Run locally, then commit and push the SVGs:
  ACCESS_TOKEN=$(gh auth token) python3 update_stats.py

Requires:
  ACCESS_TOKEN  - GitHub token with access to the counted repos
  USER_NAME     - GitHub login (default: umutozturkkk)

Stdlib only - no third-party dependencies.
"""
import json
import os
import re
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone

TOKEN = os.environ["ACCESS_TOKEN"]
USER = os.environ.get("USER_NAME", "umutozturkkk")
API = "https://api.github.com"

BIRTHDATE = "1999-12-27"  # fills the Uptime line
APPLE_ARTIST_ID = 1759144166  # App Store developer account (Sentez apps)
TOTAL_COLS = 72  # must match gen_svg.py - lines are dot-justified to this width


def request(url, payload=None, headers=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload else None,
        headers=headers if headers is not None else {
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = resp.read().decode()
    except urllib.error.HTTPError as e:
        # Transient 5xx (and 202-style not-ready responses) are handled by
        # callers' retry loops; don't crash the whole run.
        return e.code, None
    return status, json.loads(body) if body else None


def graphql(query, variables):
    _, data = request(f"{API}/graphql", {"query": query, "variables": variables})
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def user_stats():
    data = graphql(
        """
        query ($login: String!) {
          user(login: $login) {
            createdAt
            followers { totalCount }
            repositories(first: 100, ownerAffiliations: OWNER) {
              totalCount
              nodes { nameWithOwner isFork }
            }
            repositoriesContributedTo(
              contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY, PULL_REQUEST_REVIEW]
            ) { totalCount }
          }
        }
        """,
        {"login": USER},
    )["user"]
    repos = data["repositories"]
    return {
        "created_at": data["createdAt"],
        "followers": data["followers"]["totalCount"],
        "repos": repos["totalCount"],
        "contributed": data["repositoriesContributedTo"]["totalCount"],
        "repo_names": [n["nameWithOwner"] for n in repos["nodes"] if not n["isFork"]],
    }


def commit_count(created_at):
    """Total commit contributions (public + private) across all years."""
    total = 0
    start_year = datetime.fromisoformat(created_at.replace("Z", "+00:00")).year
    current_year = datetime.now(timezone.utc).year
    for year in range(start_year, current_year + 1):
        cc = graphql(
            """
            query ($login: String!, $from: DateTime!, $to: DateTime!) {
              user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                  totalCommitContributions
                  restrictedContributionsCount
                }
              }
            }
            """,
            {
                "login": USER,
                "from": f"{year}-01-01T00:00:00Z",
                "to": f"{year}-12-31T23:59:59Z",
            },
        )["user"]["contributionsCollection"]
        total += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
    return total


def lines_of_code(repo_names):
    """Sum additions/deletions authored by USER across owned non-fork repos.

    GitHub computes /stats/contributors lazily and answers 202 until ready.
    """
    added = deleted = succeeded = 0
    for repo in repo_names:
        for attempt in range(8):
            status, data = request(f"{API}/repos/{repo}/stats/contributors")
            if status == 200 and data is not None:
                for contributor in data:
                    if contributor["author"] and contributor["author"]["login"] == USER:
                        added += sum(w["a"] for w in contributor["weeks"])
                        deleted += sum(w["d"] for w in contributor["weeks"])
                succeeded += 1
                break
            if status == 204:  # empty repo, nothing to count
                succeeded += 1
                break
            time.sleep(4)
        else:
            print(f"warning: stats for {repo} not ready (last status {status}), skipped")
    if succeeded < len(repo_names):
        # Partial data would understate the count and make it oscillate
        # night to night - keep the numbers already in the SVG instead.
        return None
    return added, deleted


def uptime():
    """'X years, Y months, Z days' since BIRTHDATE, or None if unset."""
    if not BIRTHDATE:
        return None
    born = date.fromisoformat(BIRTHDATE)
    today = date.today()
    years = today.year - born.year
    months = today.month - born.month
    days = today.day - born.day
    if days < 0:
        months -= 1
        days += (today.replace(day=1) - timedelta(days=1)).day
    if months < 0:
        years -= 1
        months += 12
    plural = lambda n: "" if n == 1 else "s"
    return (f"{years} year{plural(years)}, {months} month{plural(months)}, "
            f"{days} day{plural(days)}")


def app_count():
    """Number of live apps on the App Store under APPLE_ARTIST_ID."""
    url = f"https://itunes.apple.com/lookup?id={APPLE_ARTIST_ID}&entity=software&limit=200"
    status, data = request(url, headers={})
    if status != 200 or not data:
        print("warning: App Store lookup failed, skipping apps row")
        return None
    return sum(1 for r in data["results"] if r.get("wrapperType") == "software")


def justify(key, plain_value):
    """Dots that pad '. key: <dots> value' to exactly TOTAL_COLS chars."""
    n = TOTAL_COLS - len(key) - len(plain_value) - 5
    if n < 1:
        print(f"warning: '{key}' line overflows TOTAL_COLS")
        n = 1
    return f" {'.' * n} "


def update_svg(path, values):
    svg = open(path).read()
    for id_, text in values.items():
        svg = re.sub(
            rf'(<tspan[^>]*id="{id_}"[^>]*>)[^<]*(</tspan>)',
            rf"\g<1>{text}\g<2>",
            svg,
        )
    open(path, "w").write(svg)
    print(f"updated {path}")


def main():
    stats = user_stats()
    commits = commit_count(stats["created_at"])
    loc_result = lines_of_code(stats["repo_names"])
    age = uptime()
    apps = app_count()

    repos, contrib = f"{stats['repos']:,}", f"{stats['contributed']:,}"
    commit_s = f"{commits:,}"
    follower_s = f"{stats['followers']:,}"

    values = {
        "repo_data": repos,
        "contrib_data": contrib,
        "repo_dots": justify("Repos", f"{repos} (Contributed: {contrib})"),
        "commit_data": commit_s,
        "commit_dots": justify("Commits", commit_s),
        "follower_data": follower_s,
        "follower_dots": justify("Followers", follower_s),
    }
    if loc_result is not None:
        added, deleted = loc_result
        loc = f"{added - deleted:,}"
        loc_add, loc_del = f"{added:,}++", f"{deleted:,}--"
        values.update({
            "loc_data": loc,
            "loc_add": loc_add,
            "loc_del": loc_del,
            "loc_dots": justify("Lines of Code", f"{loc} ( {loc_add}, {loc_del} )"),
        })
    if age:
        values["age_data"] = age
        values["age_dots"] = justify("Uptime", age)
    if apps is not None:
        apps_s = f"{apps} live on the App Store"
        values["apps_data"] = apps_s
        values["apps_dots"] = justify("Apps", apps_s)

    print(values)
    update_svg("dark_mode.svg", values)
    update_svg("light_mode.svg", values)


if __name__ == "__main__":
    main()
