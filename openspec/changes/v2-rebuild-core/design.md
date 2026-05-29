## Context

The v1 "Awesome Bangladeshi Devs" platform suffered from CI/CD instability and architectural friction (CJS/ESM conflicts). This design rebuilds the platform with a "Python for Data, Eleventy for Site" philosophy, emphasizing robustness and simplicity.

## Goals / Non-Goals

**Goals:**
- **Zero-Build CSS**: Use Tailwind v4 CDN to remove the primary point of CI/CD failure.
- **Incremental Enrichment**: Prevent GitHub API rate limiting for the 3500+ user base.
- **ESM-First**: Use modern JavaScript standards throughout the Eleventy site.
- **Automated Issue Handling**: Fully automate the developer lifecycle (add/remove) via GitHub Actions.

**Non-Goals:**
- **Dynamic Backend**: No live API or database; the site remains purely static.
- **Real-time Search**: Search is client-side (Fuse.js), not a server-side index.

## Decisions

### 1. Data Processing with Python 3.12
- **Rationale**: Python's `requests` and `PyYAML` libraries are more stable for large-scale data processing and batch enrichment than Node.js equivalents in a CI/CD environment.
- **Alternatives**: Node.js scripts were considered, but Python offers better handling of local snapshots and JSON-to-YAML transformations.

### 2. GitHub GraphQL API for Enrichment
- **Rationale**: Fetching detailed stats for 3500+ users via REST would require thousands of calls. GraphQL allows batching up to 20 users per call using aliases, reducing the number of requests by 95%.
- **Alternatives**: REST API (too many requests), Scraping (unreliable).

### 3. Tailwind v4 CDN
- **Rationale**: The v1 failure was largely due to PostCSS and build-step incompatibilities. v4 CDN is highly performant and eliminates the need for a local CSS build step.
- **Alternatives**: Tailwind CLI (adds build complexity), Standard CSS (harder to maintain).

### 4. Min-Max Score Normalization
- **Rationale**: Raw metrics (stars, followers) vary wildly. Normalizing scores (0-100) based on the current dataset ensures a fair "Activity Score" that reflects community rank.
- **Alternatives**: Hardcoded scoring brackets (too rigid).

## Risks / Trade-offs

- **[Risk] GitHub Rate Limits** → **Mitigation**: Implement `GH_TOKENS` rotation and incremental updates that skip users enriched in the last 24 hours.
- **[Risk] Large Search Index** → **Mitigation**: Use a compact JSON format with abbreviated keys in `search-index.json`.
- **[Risk] CI/CD Push Conflicts** → **Mitigation**: Use GitHub Action concurrency groups and a rebase-retry loop for all `git push` operations.
