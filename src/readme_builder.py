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
# ⭐ Star Pilot — GitHub Star Navigator

> auto-generated knowledge portal — organized by [star-pilot](https://github.com/{username}/star-pilot)

| section | count | description |
| :--- | :---: | :--- |
{nav_table}

**total: {total} starred repos** | last updated: {updated}

---
"""

HEADER_CN = """\
# ⭐ Star Pilot — GitHub 收藏导航

> 自动生成的知识门户 — 由 [star-pilot](https://github.com/{username}/star-pilot) 驱动

| 分区 | 数量 | 说明 |
| :--- | :---: | :--- |
{nav_table}

**共 {total} 个收藏项目** | 最后更新: {updated}

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
            updated=now,
        )

        sections = []
        for list_name in sorted(grouped.keys()):
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
            updated=now,
        )

        sections = []
        for list_name in sorted(grouped.keys()):
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

            sections.append(section)

        path = self._output_dir / "README_CN.md"
        path.write_text(header + "\n".join(sections))
        return path

    def _sanitize(self, text: str) -> str:
        """escape pipe chars for markdown table safety."""
        if not text:
            return ""
        return text.replace("|", "\\|").replace("\n", " ").strip()
