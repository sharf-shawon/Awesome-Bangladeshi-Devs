# Copilot instructions

## Automation, Validation, and Workflow Rules (MUST FOLLOW)

**This repository is fully automated and all code, workflows, and documentation must strictly follow these rules:**

### 1. Data Management
- **Manual Entries:** Stored in `data/users.json` (single source of truth for user-submitted metadata).
- **Automated Stats:** Stored in dated JSON files (e.g., `data/2026-04-22.json`). `data/automated.json` is a legacy fallback/source of truth for the latest stats if dated files are missing.
- **Removals:** Stored in `data/removed_users.json`. No duplicate entries (by username, case-insensitive) are allowed in any file.
- **Config:** `config/metrics.json` defines all ranking weights, location aliases, and `top_n` limits.

### 2. Issue-Driven Automation
- `.github/ISSUE_TEMPLATE/add_developer.yml` and `remove_developer.yml` are used for all add/remove requests.
- `.github/workflows/pipeline.yml` (specifically the `deploy` job) automates processing of these issues:
	- Self-removal is automated if the issue author matches the username.
	- Third-party removals require manual review (labeled with `manual-review`).
	- All adds/removes are validated against `config/metrics.json` (location, required fields, etc).

### 3. Data Aggregation & README Generation
- `src/generate_readme.py` MUST aggregate and rank from `users.json` and the latest dated stats file (or `automated.json`).
- `README.md` and `contributing.md` MUST always reflect the latest config and data.
- **Post-Filtering:** Lists in the README (e.g., Top 25) must be sliced *after* filtering out users in `removed_users.json` to ensure the list remains full.

### 4. CI/CD & Validation
- **Unified Pipeline:** `.github/workflows/pipeline.yml` handles validation, testing, issue processing, and README generation.
- **Stats Collection:** `.github/workflows/collect-stats.yml` runs daily to fetch fresh statistics and save them as dated JSON files.
- **Quality Checks:** All PRs and pushes must pass `awesome-lint`, `validate_data.py`, and `pytest` with high coverage.

### 5. Coding Principles
- **Standard Library:** Use only standard library modules unless a dependency (like `requests`) meaningfully reduces complexity.
- **Single Source of Truth:** All validation and ranking logic must use `config/metrics.json`.
- **Robustness:** All scripts must handle missing data, API timeouts, and edge cases (e.g., users with no name or repos).

### 6. Copilot Response Style
- Always generate complete files for repository features.
- Never introduce frameworks unless explicitly requested.
- Always explain assumptions in comments or docs if they affect data quality, API interpretation, or ranking fairness.
- Always enforce these automation, validation, and workflow rules in all code and documentation.

---

**Copilot must always follow and abide by these instructions for all code, workflow, and documentation generation in this repository.**
