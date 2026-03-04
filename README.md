# Star Pilot

Automated GitHub Star triage & knowledge navigator.

Classifies your starred repos into 7 structured lists using keyword matching, generates a dual-language (EN/CN) README portal, and keeps it updated via GitHub Actions.

## How It Works

```
starred repos ──> triage engine ──> 7 lists ──> README portal (EN + CN)
                  (rules.yaml)                  (auto-generated)
```

1. Fetches all your starred repos via GitHub API
2. Scores each repo against keyword rules in `config/rules.yaml`
3. Assigns to the highest-scoring list (fallback: `07_lab_wild`)
4. Generates navigable README tables sorted by stars

## Lists

| List | Scope |
| :--- | :--- |
| `01_ai_nexus` | LLM, Agent, ML Frameworks, Diffusion, Inference |
| `02_core_infra` | Compilers, HPC, CUDA, Profiling, System Tools |
| `03_dev_libs` | Python/C++ Libraries, SDKs, Parsers, Testing |
| `04_ops_apps` | CLI Tools, Terminal, Editors, Desktop Apps |
| `05_ui_design` | Frontend, Graphics, Fonts, Game Engines |
| `06_res_vault` | Roadmaps, Tutorials, Awesome Lists, Cookbooks |
| `07_lab_wild` | Experimental, Creative, Uncategorized |

## Usage

```bash
pip install -r requirements.txt

# preview classification results
python main.py triage

# generate dual-language README portal
python main.py readme

# create GitHub star lists and assign repos
python main.py migrate

# delete all existing star lists (stars preserved)
python main.py cleanup
```

### Options

```
--token        GitHub token (defaults to gh CLI auth)
--openai-key   OpenAI API key for CN translation
--rules        path to rules.yaml (default: config/rules.yaml)
--output       output directory (default: output/)
--username     GitHub username (default: host452b)
```

## Automation

The included GitHub Action (`.github/workflows/pilot.yml`) triggers on:

- **Star event** — regenerates portal when you star a new repo
- **Weekly CRON** — Monday 08:00 UTC
- **Manual dispatch** — choose `triage`, `readme`, or `migrate`

Required secrets: `GH_PAT` (with `user` scope), `OPENAI_API_KEY` (optional).

## Portal

Browse the generated portal:

- [English Portal](output/README.md)
- [中文门户](output/README_CN.md)

## Project Structure

```
star-pilot/
├── main.py                         # CLI entry point
├── config/rules.yaml               # keyword mapping (22 -> 7 lists)
├── src/
│   ├── gh_client.py                # GitHub REST + GraphQL API wrapper
│   ├── triage_logic.py             # classification engine
│   ├── translator.py               # EN -> CN translation with cache
│   └── readme_builder.py           # dual-language portal generator
├── output/
│   ├── README.md                   # generated EN portal
│   └── README_CN.md                # generated CN portal
├── .github/workflows/pilot.yml    # CI/CD automation
└── requirements.txt
```

## License

MIT
