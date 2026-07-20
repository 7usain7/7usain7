#!/usr/bin/env python3

import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

OWNER = "7usain7"
README_PATH = Path("README.md")

START_MARKER = "<!-- GITHUB-LANGUAGES:START -->"
END_MARKER = "<!-- GITHUB-LANGUAGES:END -->"

TOKEN = os.environ.get("GITHUB_TOKEN", "")

if not TOKEN:
    print("GITHUB_TOKEN is missing.", file=sys.stderr)
    sys.exit(1)


def github_api(path: str):
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "github-profile-language-updater",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def get_repositories():
    repositories = []
    page = 1

    while True:
        result = github_api(
            f"/users/{OWNER}/repos"
            f"?type=owner&sort=full_name&per_page=100&page={page}"
        )

        if not result:
            break

        repositories.extend(
            repository
            for repository in result
            if not repository.get("fork", False)
            and not repository.get("archived", False)
            and not repository.get("disabled", False)
        )

        if len(result) < 100:
            break

        page += 1

    return repositories


def get_languages(repo_name: str):
    return github_api(f"/repos/{OWNER}/{repo_name}/languages")


def calculate_language_percentages():
    repos = get_repositories()
    language_totals = defaultdict(int)

    for repo in repos:
        repo_name = repo["name"]
        try:
            langs = get_languages(repo_name)
            for lang, bytes_count in langs.items():
                language_totals[lang] += bytes_count
        except Exception as e:
            print(f"Warning: Could not fetch languages for {repo_name}: {e}", file=sys.stderr)

    total_bytes = sum(language_totals.values())

    if total_bytes == 0:
        return []

    sorted_langs = sorted(
        language_totals.items(), key=lambda item: item[1], reverse=True
    )

    result = []
    for lang, bytes_count in sorted_langs:
        percentage = (bytes_count / total_bytes) * 100
        if percentage >= 0.5:  # filter out languages less than 0.5%
            result.append((lang, percentage, bytes_count))

    return result


def generate_markdown(languages):
    if not languages:
        return "_No language data available yet._"

    lines = ["<p align=\"center\">"]
    for lang, percentage, _ in languages:
        color = "5EEAD4" if percentage > 20 else ("A78BFA" if percentage > 10 else "FBBF24")
        badge_name = lang.replace("-", "_").replace(" ", "_")
        lines.append(
            f'  <img src="https://img.shields.io/badge/{badge_name}-{percentage:.1f}%25-{color}?style=flat-square&labelColor=0d1117" alt="{lang}" />'
        )
    lines.append("</p>")
    return "\n".join(lines)


def update_readme():
    if not README_PATH.exists():
        print(f"Error: {README_PATH} does not exist.", file=sys.stderr)
        sys.exit(1)

    content = README_PATH.read_text(encoding="utf-8")

    if START_MARKER not in content or END_MARKER not in content:
        print(f"Error: Markers {START_MARKER} and {END_MARKER} not found in README.md", file=sys.stderr)
        sys.exit(1)

    languages = calculate_language_percentages()
    new_languages_md = generate_markdown(languages)

    start_idx = content.find(START_MARKER) + len(START_MARKER)
    end_idx = content.find(END_MARKER)

    updated_content = (
        content[:start_idx]
        + "\n\n"
        + new_languages_md
        + "\n\n"
        + content[end_idx:]
    )

    README_PATH.write_text(updated_content, encoding="utf-8")
    print("README.md updated successfully with latest language statistics!")


if __name__ == "__main__":
    update_readme()
