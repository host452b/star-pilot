"""
star-pilot: automated github star triage & navigator.
entry point for CLI operations.
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from src.gh_client import GitHubClient
from src.triage_logic import TriageEngine
from src.translator import Translator
from src.readme_builder import ReadmeBuilder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("star-pilot")


def cmd_triage(args: argparse.Namespace) -> None:
    """classify all starred repos and print results."""
    client = GitHubClient(token=args.token)
    engine = TriageEngine(rules_path=args.rules)

    logger.info("fetching starred repos...")
    repos = client.fetch_starred_repos()
    logger.info(f"found {len(repos)} starred repos")

    results = engine.classify_batch(repos)

    for r in sorted(results, key=lambda x: x.target_list):
        kw = ", ".join(r.matched_keywords[:3])
        print(f"  [{r.target_list}] {r.repo.full_name:40s} (score={r.score}, kw={kw})")

    report_path = Path(args.output) / "triage_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_data = [
        {
            "repo": r.repo.full_name,
            "target": r.target_list,
            "score": r.score,
            "keywords": r.matched_keywords,
        }
        for r in results
    ]
    report_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False))
    logger.info(f"triage report saved to {report_path}")


def cmd_readme(args: argparse.Namespace) -> None:
    """generate dual-language README portal."""
    client = GitHubClient(token=args.token)
    engine = TriageEngine(rules_path=args.rules)
    translator = Translator(api_key=args.openai_key)

    logger.info("fetching starred repos...")
    repos = client.fetch_starred_repos()
    logger.info(f"found {len(repos)} starred repos")

    results = engine.classify_batch(repos)

    builder = ReadmeBuilder(
        rules=engine.rules,
        translator=translator,
        username=args.username,
        output_dir=args.output,
    )
    en_path, cn_path = builder.build(results)
    logger.info(f"portal generated:\n  {en_path}\n  {cn_path}")


def cmd_migrate(args: argparse.Namespace) -> None:
    """migrate stars into new GitHub lists (create lists + assign repos)."""
    client = GitHubClient(token=args.token)
    engine = TriageEngine(rules_path=args.rules)

    logger.info("fetching starred repos...")
    repos = client.fetch_starred_repos()
    logger.info(f"found {len(repos)} starred repos")

    results = engine.classify_batch(repos)

    existing_lists = client.fetch_lists()
    list_map = {sl.name: sl.id for sl in existing_lists}
    logger.info(f"found {len(existing_lists)} existing lists")

    for rule in engine.rules:
        if rule.name not in list_map:
            logger.info(f"creating list: {rule.name}")
            sl = client.create_list(rule.name, rule.description)
            list_map[sl.name] = sl.id

    total = len(results)
    ok_count = 0
    fail_count = 0

    for i, r in enumerate(results, 1):
        list_id = list_map.get(r.target_list)
        if not list_id:
            logger.warning(f"[{i}/{total}] no list ID for {r.target_list}, skip {r.repo.full_name}")
            fail_count += 1
            continue

        node_id = client.get_repo_node_id(r.repo.full_name)
        if not node_id:
            logger.warning(f"[{i}/{total}] cannot resolve node ID for {r.repo.full_name}")
            fail_count += 1
            continue

        success = client.add_repo_to_list(list_id, node_id)
        if success:
            ok_count += 1
            logger.info(f"[{i}/{total}] OK   {r.repo.full_name} -> {r.target_list}")
        else:
            fail_count += 1
            logger.warning(f"[{i}/{total}] FAIL {r.repo.full_name} -> {r.target_list}")

        time.sleep(0.15)

    logger.info(f"migration complete: {ok_count} ok, {fail_count} failed, {total} total")


def cmd_full(args: argparse.Namespace) -> None:
    """full pipeline: triage + readme + migrate in one run."""
    client = GitHubClient(token=args.token)
    engine = TriageEngine(rules_path=args.rules)
    translator = Translator(api_key=args.openai_key)

    logger.info("=== phase 1: fetch & classify ===")
    repos = client.fetch_starred_repos()
    logger.info(f"found {len(repos)} starred repos")

    results = engine.classify_batch(repos)

    report_path = Path(args.output) / "triage_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_data = [
        {
            "repo": r.repo.full_name,
            "target": r.target_list,
            "score": r.score,
            "keywords": r.matched_keywords,
        }
        for r in results
    ]
    report_path.write_text(json.dumps(report_data, indent=2, ensure_ascii=False))
    logger.info(f"triage report saved to {report_path}")

    logger.info("=== phase 2: generate portal ===")
    builder = ReadmeBuilder(
        rules=engine.rules,
        translator=translator,
        username=args.username,
        output_dir=args.output,
    )
    en_path, cn_path = builder.build(results)
    logger.info(f"portal generated:\n  {en_path}\n  {cn_path}")

    logger.info("=== phase 3: migrate star lists ===")
    existing_lists = client.fetch_lists()
    list_map = {sl.name: sl.id for sl in existing_lists}
    logger.info(f"found {len(existing_lists)} existing lists")

    for rule in engine.rules:
        if rule.name not in list_map:
            logger.info(f"creating list: {rule.name}")
            sl = client.create_list(rule.name, rule.description)
            list_map[sl.name] = sl.id

    total = len(results)
    ok_count = 0
    fail_count = 0

    for i, r in enumerate(results, 1):
        list_id = list_map.get(r.target_list)
        if not list_id:
            logger.warning(f"[{i}/{total}] no list ID for {r.target_list}, skip {r.repo.full_name}")
            fail_count += 1
            continue

        node_id = client.get_repo_node_id(r.repo.full_name)
        if not node_id:
            logger.warning(f"[{i}/{total}] cannot resolve node ID for {r.repo.full_name}")
            fail_count += 1
            continue

        success = client.add_repo_to_list(list_id, node_id)
        if success:
            ok_count += 1
        else:
            fail_count += 1

        if i % 20 == 0:
            logger.info(f"[{i}/{total}] progress: {ok_count} ok, {fail_count} failed")

        time.sleep(0.15)

    logger.info(f"=== done: {ok_count} ok, {fail_count} failed, {total} total ===")


def cmd_cleanup(args: argparse.Namespace) -> None:
    """delete all existing star lists (stars themselves are preserved)."""
    client = GitHubClient(token=args.token)
    existing = client.fetch_lists()

    if not existing:
        logger.info("no lists to delete")
        return

    logger.info(f"deleting {len(existing)} lists...")
    for sl in existing:
        logger.info(f"  deleting: {sl.name} ({sl.id})")
        client.delete_list(sl.id)
        time.sleep(0.2)
    logger.info("all lists deleted")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="star-pilot",
        description="automated github star triage & navigator",
    )
    parser.add_argument("--token", help="github token (defaults to gh CLI auth)")
    parser.add_argument("--openai-key", help="openai API key for translation")
    parser.add_argument("--rules", default="config/rules.yaml", help="path to rules.yaml")
    parser.add_argument("--output", default="output", help="output directory")
    parser.add_argument("--username", default="host452b", help="github username")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("triage", help="classify all starred repos")
    sub.add_parser("readme", help="generate README portal")
    sub.add_parser("migrate", help="create lists and assign repos")
    sub.add_parser("full", help="full pipeline: triage + readme + migrate")
    sub.add_parser("cleanup", help="delete all existing star lists")

    args = parser.parse_args()

    dispatch = {
        "triage": cmd_triage,
        "readme": cmd_readme,
        "migrate": cmd_migrate,
        "full": cmd_full,
        "cleanup": cmd_cleanup,
    }

    handler = dispatch.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    handler(args)


if __name__ == "__main__":
    main()
