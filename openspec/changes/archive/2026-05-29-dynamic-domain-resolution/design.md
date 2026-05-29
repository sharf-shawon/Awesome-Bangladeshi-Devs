## Context

Absolute URLs are required for XML sitemaps, Open Graph metadata, and canonical link tags. Currently, these are hardcoded to a specific domain.

## Goals / Non-Goals

**Goals:**
- Resolve the site's base URL dynamically.
- Support `CNAME` files (custom domains).
- Support `SITE_URL` environment variable for CI/CD overrides.

**Non-Goals:**
- Redesigning the URL structure or permalinks.

## Decisions

### 1. Data File for Site Metadata
**Decision:** Create `site/_data/site.js`.
**Rationale:** This provides a globally accessible `site` object in all templates.

### 2. URL Resolution Priority
**Decision:** 
1. `process.env.SITE_URL`
2. `CNAME` file content (prefixed with `https://`)
3. Fallback to `http://localhost:8080` for local dev.
**Rationale:** Environment variables allow for the most flexibility in CI, while the `CNAME` file provides a sensible default for production deployments.

## Risks / Trade-offs

- **[Risk] Missing protocol in CNAME** → [Mitigation] Explicitly prefix with `https://` in the data loader.
