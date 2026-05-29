## Why

The current version of "Awesome Bangladeshi Devs" has a broken CI/CD pipeline and outdated architectural patterns (CJS/ESM mismatches, complex CSS build steps). This change rebuilds the foundation from scratch to ensure long-term maintainability, robust automation, and a modern, high-performance static site.

## What Changes

- **Repository Structure**: Reorganizes the root to separate concerns: `src/` for logic, `site/` for Eleventy source, `data/` for state, and `config/` for parameters.
- **CI/CD Pipeline**: Implements a modular GitHub Actions workflow for validation, testing, issue processing, and site deployment.
- **Tooling Migration**: Moves to Eleventy 3.x (ESM) and Python 3.12.
- **Styling**: Replaces the complex CSS build process with Tailwind CSS v4 via CDN.
- **Data Processing**: Implements robust scripts for data validation, GitHub GraphQL enrichment, and search index generation.

## Capabilities

### New Capabilities
- `data-validation`: Ensures `users.json` remains the canonical, duplicate-free source of truth with valid GitHub usernames.
- `issue-automation`: Automates the addition and removal of developers via GitHub Issue templates and Actions.
- `data-enrichment`: Performs batch enrichment of developer metadata using the GitHub GraphQL API, including activity scoring.
- `site-generation`: Transforms enriched data into a performant static site with SEO optimization and a Fuse.js search index.

### Modified Capabilities
- None (This is a complete rebuild of the application logic).

## Impact

- **Affected Systems**: Repository structure, GitHub Actions, data processing scripts, and the static site generator.
- **Dependencies**: Introduces Python dependencies (`requests`, `PyYAML`) and Node.js dependencies (`@11ty/eleventy`, `luxon`).
- **Data Integrity**: Preserves existing `data/users.json`, `data/removed_users.json`, and `data/overrides.yml`.
