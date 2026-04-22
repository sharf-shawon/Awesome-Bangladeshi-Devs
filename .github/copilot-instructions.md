
# Copilot instructions

## Automation, Validation, and Workflow Rules (MUST FOLLOW)

**This repository is fully automated and all code, workflows, and documentation must strictly follow these rules:**

### 1. Data Management
- All user-submitted developer entries are stored in `data/users.json` (single source of truth for manual entries).
- All automated/statistical entries are stored in `data/automated.json` (single source of truth for automated entries).
- No duplicate entries (by username, case-insensitive) are allowed in either file.

### 2. Issue-Driven Automation
- `.github/ISSUE_TEMPLATE/add_developer.yml` and `remove_developer.yml` are used for all add/remove requests.
- `.github/workflows/process-add-remove.yml` automates processing of these issues:
	- Self-removal is automated if the issue author matches the username.
	- Third-party removals require manual review.
	- All adds/removes are validated against `config/metrics.json` (location, required fields, etc).

### 3. Data Aggregation & README Generation
- `src/generate_readme.py` must aggregate and rank from both `users.json` and `automated.json`.
- `README.md` and `contributing.md` must always reflect the latest config and data.
- All public docs must be regenerated on config/data changes.

### 4. CI/CD & Validation
- All workflows must pass awesome-lint, schema validation, and all other checks before merging or deploying.
- `.github/workflows/generate-readme.yml` and `.github/workflows/validate.yml` enforce these checks.
- All scripts and workflows must be tested with ~100% coverage (unit, integration, regression, edge cases).

### 5. Coding Principles
- Use only standard library modules unless a dependency meaningfully reduces complexity.
- Prefer explicit configuration in `config/*.json` over hardcoded constants.
- All validation and ranking logic must use `config/metrics.json` as the single source of truth.
- All code must be robust, handle edge cases, and be easy to review.

### 6. Copilot Response Style
- Always generate complete files for repository features.
- Never introduce frameworks unless explicitly requested.
- Always explain assumptions in comments or docs if they affect data quality, API interpretation, or ranking fairness.
- Always enforce these automation, validation, and workflow rules in all code and documentation.

---

**Copilot must always follow and abide by these instructions for all code, workflow, and documentation generation in this repository.**
