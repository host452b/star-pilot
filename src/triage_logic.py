"""
triage engine: decides which star list a repo belongs to.
uses keyword matching against repo description, topics, and language.
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from .gh_client import StarredRepo

logger = logging.getLogger(__name__)

DEFAULT_LIST = "07_lab_wild"


@dataclass
class ListRule:
    name: str
    description: str
    description_cn: str
    keywords: list[str]
    language_hints: list[str]


@dataclass
class TriageResult:
    repo: StarredRepo
    target_list: str
    score: int
    matched_keywords: list[str]


class TriageEngine:
    """
    scores each repo against every list's keyword set.
    highest score wins. ties broken by list priority (lower index = higher priority).
    """

    def __init__(self, rules_path: str | Path = "config/rules.yaml"):
        self._rules: list[ListRule] = []
        self._overrides: dict[str, str] = {}
        self._load_rules(Path(rules_path))

    def _load_rules(self, path: Path) -> None:
        with open(path) as f:
            config = yaml.safe_load(f)

        for list_name, rule_data in config.get("lists", {}).items():
            self._rules.append(ListRule(
                name=list_name,
                description=rule_data.get("description", ""),
                description_cn=rule_data.get("description_cn", ""),
                keywords=[k.lower() for k in rule_data.get("keywords", [])],
                language_hints=[lang.lower() for lang in rule_data.get("language_hints", [])],
            ))

        self._overrides = config.get("overrides", {})
        logger.info(f"loaded {len(self._rules)} list rules, {len(self._overrides)} overrides")

    @property
    def rules(self) -> list[ListRule]:
        return self._rules

    def classify(self, repo: StarredRepo) -> TriageResult:
        """classify a single repo into the best-matching list."""
        if repo.full_name in self._overrides:
            target = self._overrides[repo.full_name]
            return TriageResult(
                repo=repo,
                target_list=target,
                score=999,
                matched_keywords=["[override]"],
            )

        searchable = self._build_searchable(repo)
        best_list = DEFAULT_LIST
        best_score = 0
        best_matches = []

        for rule in self._rules:
            score, matches = self._score_against(searchable, repo, rule)
            if score > best_score:
                best_score = score
                best_list = rule.name
                best_matches = matches

        return TriageResult(
            repo=repo,
            target_list=best_list,
            score=best_score,
            matched_keywords=best_matches,
        )

    def classify_batch(self, repos: list[StarredRepo]) -> list[TriageResult]:
        results = [self.classify(repo) for repo in repos]
        classified = sum(1 for r in results if r.score > 0)
        uncategorized = len(results) - classified
        logger.info(f"classified {classified}, uncategorized {uncategorized}")
        return results

    def _build_searchable(self, repo: StarredRepo) -> str:
        """flatten repo metadata into a single lowercase string for matching."""
        parts = [
            repo.description.lower(),
            repo.full_name.lower(),
            " ".join(t.lower() for t in repo.topics),
        ]
        return " ".join(parts)

    def _score_against(
        self, searchable: str, repo: StarredRepo, rule: ListRule
    ) -> tuple[int, list[str]]:
        score = 0
        matches = []

        for kw in rule.keywords:
            if kw in searchable:
                score += 1
                matches.append(kw)

        if repo.language and repo.language.lower() in rule.language_hints:
            score += 2
            matches.append(f"lang:{repo.language}")

        return score, matches
