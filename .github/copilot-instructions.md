# Copilot instructions

## Automation, Validation, and Workflow Rules (MUST FOLLOW)

**This repository is fully automated and all code, workflows, and documentation must strictly follow these rules:**

### 1. Data Management
- `data/users.json`: Source of truth for listed developers (manual/issue entries).
- `data/users-enriched.json`: Enriched data including repository metadata, fetched via GitHub GraphQL.
- `data/search-index.json`: Lightweight index for frontend search.
- `data/overrides.yml`: Manual curation layer for featured devs, aliases, and corrections.
- All ranking and activity scores are precomputed in `src/enrich_data.py`.

### 2. Issue-Driven Automation
- Processing of `add_developer.yml` and `remove_developer.yml` continues via `.github/workflows/pipeline.yml`.
- New entries are added to `data/users.json` and then enriched in the next scheduled run.

### 3. Build & Deployment
- The site is built using **Eleventy (11ty)**.
- Search is powered by **Fuse.js** on the client side.
- All profile pages (`/dev/{username}/`) and category pages (`/languages/{language}/`) are statically generated.
- Deployment is automated via `.github/workflows/deploy-site.yml`.

### 4. Data Pipeline
- `src/enrich_data.py`: Fetches user/repo metadata using GraphQL. Respects rate limits and incremental updates.
- `src/build_search_index.py`: Generates the search index.
- Data enrichment runs daily via `.github/workflows/collect-stats.yml`.

### 5. Coding Principles
- Use standard libraries where possible (exception: `requests`, `PyYAML`).
- Maintain ~100% coverage for all processing scripts.
- No live GitHub API calls from the frontend.

### 6. Copilot Response Style
- Always generate complete files for repository features.
- Never introduce frameworks unless explicitly requested (Eleventy and Fuse.js are approved for this project).
- Always explain assumptions in comments or docs if they affect data quality, API interpretation, or ranking fairness.
- Always enforce these automation, validation, and workflow rules in all code and documentation.

---

**Copilot must always follow and abide by these instructions for all code, workflow, and documentation generation in this repository.**
