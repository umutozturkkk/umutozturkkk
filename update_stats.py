#!/usr/bin/env python3
"""Fetch GitHub stats and write them into dark_mode.svg / light_mode.svg.

Requires:
  ACCESS_TOKEN  - GitHub token (fine-grained PAT for private-repo stats,
                  or the default Actions token for public-only stats)
  USER_NAME     - GitHub login (default: umutozturkkk)

Stdlib only - no third-party dependencies.
"""
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ["ACCESS_TOKEN"]
USER = os.environ.get("USER_NAME", "umutozturkkk")
API = "https://api.github.com"


def request(url, payload=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode() if payload else None,
        headers={
            "Authorization": f"token {TOKEN}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        status = resp.status
        body = resp.read().decode()
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
              nodes { nameWithOwner stargazerCount isFork }
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
        "stars": sum(n["stargazerCount"] for n in repos["nodes"]),
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
    added = deleted = 0
    for repo in repo_names:
        for attempt in range(6):
            status, data = request(f"{API}/repos/{repo}/stats/contributors")
            if status == 200 and data is not None:
                for contributor in data:
                    if contributor["author"] and contributor["author"]["login"] == USER:
                        added += sum(w["a"] for w in contributor["weeks"])
                        deleted += sum(w["d"] for w in contributor["weeks"])
                break
            time.sleep(3)
        else:
            print(f"warning: stats for {repo} not ready, skipped")
    return added, deleted


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
    added, deleted = lines_of_code(stats["repo_names"])
    values = {
        "repo_data": f"{stats['repos']:,}",
        "contrib_data": f"{stats['contributed']:,}",
        "commit_data": f"{commits:,}",
        "star_data": f"{stats['stars']:,}",
        "follower_data": f"{stats['followers']:,}",
        "loc_data": f"{added - deleted:,}",
        "loc_add": f"{added:,}++",
        "loc_del": f"{deleted:,}--",
    }
    print(values)
    update_svg("dark_mode.svg", values)
    update_svg("light_mode.svg", values)


if __name__ == "__main__":
    main()
