"""
portal generator: builds structured README.md and README_CN.md
from triage results.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from .gh_client import StarredRepo
from .triage_logic import ListRule, TriageResult
from .translator import Translator

logger = logging.getLogger(__name__)


HEADER_EN = """\
<div align="center">

# ⭐ Star Pilot — GitHub Star Navigator

**An auto-generated knowledge portal of curated GitHub stars,
classified into {num_lists} structured categories using keyword-based triage.**

[![Portal](https://img.shields.io/badge/stars_classified-{total}-yellow?logo=github)](https://github.com/{username}/star-pilot)
[![CN Portal](https://img.shields.io/badge/中文门户-README__CN-blue)](README_CN.md)

[中文版](README_CN.md) · [Back to Star Pilot](https://github.com/{username}/star-pilot)

</div>

---

## Quick Navigation

| section | count | description |
| :--- | :---: | :--- |
{nav_table}

> **{total} starred repos** · last updated: {updated}

---
"""

HEADER_CN = """\
<div align="center">

# ⭐ Star Pilot — GitHub 收藏导航

**基于关键词分类引擎自动生成的 GitHub 收藏知识门户，
{total} 个精选项目分成 {num_lists} 大类。**

[![Portal](https://img.shields.io/badge/已分类项目-{total}-yellow?logo=github)](https://github.com/{username}/star-pilot)
[![EN Portal](https://img.shields.io/badge/English_Portal-README-blue)](README.md)

[English](README.md) · [返回 Star Pilot](https://github.com/{username}/star-pilot)

</div>

---

## 快速导航

| 分区 | 数量 | 说明 |
| :--- | :---: | :--- |
{nav_table}

> **共 {total} 个收藏项目** · 最后更新: {updated}

---
"""


class ReadmeBuilder:
    """
    builds dual-language README portal files from classified starred repos.
    """

    def __init__(
        self,
        rules: list[ListRule],
        translator: Translator,
        username: str = "host452b",
        output_dir: str = "output",
    ):
        self._rules = {r.name: r for r in rules}
        self._translator = translator
        self._username = username
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    def build(self, results: list[TriageResult]) -> tuple[Path, Path]:
        grouped = self._group_by_list(results)
        en_path = self._build_en(grouped)
        cn_path = self._build_cn(grouped)
        logger.info(f"generated {en_path} and {cn_path}")
        return en_path, cn_path

    def _group_by_list(
        self, results: list[TriageResult]
    ) -> dict[str, list[TriageResult]]:
        grouped: dict[str, list[TriageResult]] = defaultdict(list)
        for r in results:
            grouped[r.target_list].append(r)

        for list_results in grouped.values():
            list_results.sort(key=lambda r: r.repo.stars, reverse=True)

        return grouped

    def _build_en(self, grouped: dict[str, list[TriageResult]]) -> Path:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        total = sum(len(v) for v in grouped.values())

        nav_rows = []
        for list_name in sorted(grouped.keys()):
            rule = self._rules.get(list_name)
            desc = rule.description if rule else ""
            anchor = list_name.lower().replace("_", "-")
            count = len(grouped[list_name])
            nav_rows.append(f"| [{list_name}](#{anchor}) | {count} | {desc} |")

        header = HEADER_EN.format(
            username=self._username,
            nav_table="\n".join(nav_rows),
            total=total,
            num_lists=len(grouped),
            updated=now,
        )

        sections = []
        sorted_keys = sorted(grouped.keys())
        for idx, list_name in enumerate(sorted_keys):
            rule = self._rules.get(list_name)
            desc = rule.description if rule else ""
            section = f"## {list_name}\n\n> {desc}\n\n"
            section += "| project | description | stars | lang |\n"
            section += "| :--- | :--- | :---: | :--- |\n"

            for r in grouped[list_name]:
                repo = r.repo
                name_link = f"[{repo.full_name}]({repo.url})"
                safe_desc = self._sanitize(repo.description)
                section += f"| {name_link} | {safe_desc} | ⭐ {repo.stars} | {repo.language} |\n"

            section += "\n"
            nav = self._section_nav(sorted_keys, idx)
            section += nav

            sections.append(section)

        path = self._output_dir / "README.md"
        path.write_text(header + "\n".join(sections))
        return path

    def _build_cn(self, grouped: dict[str, list[TriageResult]]) -> Path:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        total = sum(len(v) for v in grouped.values())

        nav_rows = []
        for list_name in sorted(grouped.keys()):
            rule = self._rules.get(list_name)
            desc_cn = rule.description_cn if rule else ""
            anchor = list_name.lower().replace("_", "-")
            count = len(grouped[list_name])
            nav_rows.append(f"| [{list_name}](#{anchor}) | {count} | {desc_cn} |")

        header = HEADER_CN.format(
            username=self._username,
            nav_table="\n".join(nav_rows),
            total=total,
            num_lists=len(grouped),
            updated=now,
        )

        sections = []
        sorted_keys = sorted(grouped.keys())
        for idx, list_name in enumerate(sorted_keys):
            rule = self._rules.get(list_name)
            desc_cn = rule.description_cn if rule else ""
            section = f"## {list_name}\n\n> {desc_cn}\n\n"
            section += "| 项目 | 说明 | Stars | 语言 |\n"
            section += "| :--- | :--- | :---: | :--- |\n"

            for r in grouped[list_name]:
                repo = r.repo
                name_link = f"[{repo.full_name}]({repo.url})"
                translated = self._translator.translate(repo.description)
                safe_desc = self._sanitize(translated)
                section += f"| {name_link} | {safe_desc} | ⭐ {repo.stars} | {repo.language} |\n"

            section += "\n"
            nav = self._section_nav(sorted_keys, idx)
            section += nav

            sections.append(section)

        path = self._output_dir / "README_CN.md"
        path.write_text(header + "\n".join(sections))
        return path

    def _section_nav(self, keys: list[str], current: int) -> str:
        """build inter-section navigation links (prev / top / next)."""
        parts = []
        if current > 0:
            prev_anchor = keys[current - 1].lower().replace("_", "-")
            parts.append(f"[⬆ {keys[current - 1]}](#{prev_anchor})")
        parts.append("[🔝 Top](#quick-navigation)")
        if current < len(keys) - 1:
            next_anchor = keys[current + 1].lower().replace("_", "-")
            parts.append(f"[⬇ {keys[current + 1]}](#{next_anchor})")
        return " · ".join(parts) + "\n\n---\n"

    def _sanitize(self, text: str) -> str:
        """escape pipe chars for markdown table safety."""
        if not text:
            return ""
        return text.replace("|", "\\|").replace("\n", " ").strip()
