<div align="center">

# Star Pilot

**A Python-powered GitHub Star auto-triage engine that classifies your starred repos into structured lists and generates dual-language navigation portals.**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-3776AB?logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/CI-GitHub_Actions-2088FF?logo=githubactions&logoColor=white)](.github/workflows/pilot.yml)
[![Stars Classified](https://img.shields.io/badge/stars_classified-126-yellow?logo=github)](output/README.md)

[English Portal](output/README.md) · [中文门户](output/README_CN.md) · [Quick Start](#quick-start) · [How It Works](#how-it-works)

</div>

---

## Why Star Pilot?

Most developers star hundreds of GitHub repos but never revisit them. Star Pilot solves this by automatically **triaging** your stars into 7 high-level categories using keyword scoring, then generating a browsable **dual-language README portal** — updated weekly via GitHub Actions.

**Key capabilities:**

- **Auto-classification** — scores repos by description, topics, and language against a YAML rule engine
- **Dual-language portal** — generates `README.md` (EN) + `README_CN.md` (CN) with navigation tables
- **GitHub Star List migration** — creates lists via GraphQL and assigns repos automatically
- **CI/CD ready** — triggers on new star events, weekly CRON, or manual dispatch

## How It Works

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐     ┌────────────────┐
│ GitHub Stars │ ──> │ Triage Engine │ ──> │ 7 Star Lists │ ──> │ README Portal  │
│  (REST API)  │     │ (rules.yaml)  │     │  (GraphQL)   │     │  (EN + CN)     │
└──────────────┘     └───────────────┘     └──────────────┘     └────────────────┘
```

The triage engine loads keyword rules from [`config/rules.yaml`](config/rules.yaml), scores each starred repo, and assigns it to the highest-matching list:

| List | Scope | Keywords |
| :--- | :--- | :--- |
| [`01_ai_nexus`](output/README.md#01_ai_nexus) | LLM, Agent, ML Frameworks, Inference | llm, pytorch, transformers, agent, mcp |
| [`02_core_infra`](output/README.md#02_core_infra) | Compilers, HPC, CUDA, Profiling | compiler, ebpf, kernel, profiler, llvm |
| [`03_dev_libs`](output/README.md#03_dev_libs) | Python/C++ Libraries, SDKs, Testing | pydantic, fastapi, linter, parser, sdk |
| [`04_ops_apps`](output/README.md#04_ops_apps) | CLI, Terminal, Desktop Apps | docker, cli, neovim, macos, self-hosted |
| [`05_ui_design`](output/README.md#05_ui_design) | Frontend, Graphics, Game Engines | font, tailwind, game-engine, animation |
| [`06_res_vault`](output/README.md#06_res_vault) | Tutorials, Awesome Lists, Cookbooks | awesome, roadmap, tutorial, cookbook |
| [`07_lab_wild`](output/README.md#07_lab_wild) | Experimental, Uncategorized | fallback for unmatched repos |

## Quick Start

```bash
git clone https://github.com/host452b/star-pilot.git
cd star-pilot
pip install -r requirements.txt
```

### Commands

```bash
# preview: see where each repo would be classified
python main.py triage

# generate: build the dual-language README portal
python main.py readme

# migrate: create GitHub star lists + assign all repos via GraphQL
python main.py migrate

# cleanup: delete all star lists (stars themselves are preserved)
python main.py cleanup
```

### Options

| Flag | Default | Description |
| :--- | :--- | :--- |
| `--token` | gh CLI auth | GitHub Personal Access Token |
| `--openai-key` | `$OPENAI_API_KEY` | OpenAI key for CN translation |
| `--rules` | `config/rules.yaml` | Path to classification rules |
| `--output` | `output/` | Portal output directory |
| `--username` | `host452b` | GitHub username for portal links |

## GitHub Actions Automation

The workflow (`.github/workflows/pilot.yml`) supports three triggers:

| Trigger | Event | Action |
| :--- | :--- | :--- |
| New star | `watch` | Regenerate portal |
| Weekly | CRON Mon 08:00 UTC | Regenerate portal |
| Manual | `workflow_dispatch` | Choose `triage` / `readme` / `migrate` |

**Required secrets:** `GH_PAT` (with `user` scope). **Optional:** `OPENAI_API_KEY` for Chinese translations.

## Project Structure

```
star-pilot/
├── main.py                         # CLI entry point (4 commands)
├── config/rules.yaml               # keyword mapping rules (22 -> 7 lists)
├── src/
│   ├── gh_client.py                # GitHub REST + GraphQL API wrapper
│   ├── triage_logic.py             # keyword scoring classification engine
│   ├── translator.py               # EN -> CN translation (OpenAI + MD5 cache)
│   └── readme_builder.py           # dual-language portal generator
├── output/
│   ├── README.md                   # generated EN portal
│   └── README_CN.md                # generated CN portal
├── .github/workflows/pilot.yml    # CI/CD automation
└── requirements.txt                # httpx, pyyaml, openai
```

## Customization

Edit [`config/rules.yaml`](config/rules.yaml) to tune classification:

- **keywords** — add domain-specific terms to any list
- **language_hints** — boost score for repos in specific languages
- **overrides** — force a specific repo into a specific list

## Browse the Portal

<table>
<tr>
<td align="center"><strong><a href="output/README.md">English Portal</a></strong><br/>126 repos · 7 categories</td>
<td align="center"><strong><a href="output/README_CN.md">中文门户</a></strong><br/>126 个项目 · 7 个分类</td>
</tr>
</table>

## License

[MIT](LICENSE)
