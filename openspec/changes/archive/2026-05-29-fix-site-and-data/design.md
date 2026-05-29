## Context

The project maintains a dataset of 3600+ Bangladeshi developers and 31,000+ repositories. Recent updates introduced a new date field (`enriched_at`) that caused crashes on legacy records. Additionally, the site's project discovery is hampered by 404 errors and a purely static repositories list that is difficult to navigate.

## Goals / Non-Goals

**Goals:**
- Fix the `KeyError` crash in the enrichment script.
- Resolve the `/languages/` routing 404.
- Implement an interactive, client-side projects gallery with search and filtering.
- Optimize the projects data payload for fast browser loading.

**Non-Goals:**
- Implementing a backend search API.
- Re-enriching all 3600 users from scratch (unless forced).
- Redesigning the entire UI/UX.

## Decisions

### 1. Robust Data Normalization
**Decision:** In `src/enrich_data.py`, replace direct access to `['enriched_at']` with a safe lookup that falls back to `last_repo_fetched_at`.
**Rationale:** The dataset is live and contains legacy records. Python is less forgiving than the current Javascript data loader, so it must mirror the JS robustness.

### 2. Hybrid Project Rendering
**Decision:** Move from static Nunjucks rendering of the full projects list to a JSON-backed client-side gallery.
**Rationale:** 31,000 repositories is too large for a single HTML page. By filtering for "Quality" repos (stars > 5) and offloading rendering to JS, we reduce the initial page weight and enable instant searching.

### 3. Shared Search Engine
**Decision:** Reuse the existing `Fuse.js` implementation from the homepage for the projects page.
**Rationale:** Reduces bundle size and maintains consistent search behavior across the site.

### 4. Explicit Routing
**Decision:** Add `permalink: /languages/` to `site/languages-index.njk`.
**Rationale:** Resolves the discrepancy between the file system location and the site's navigation structure.

## Risks / Trade-offs

- **[Risk] Search index bloat** → [Mitigation] Apply a community-interest threshold (stars > 5) to filter the projects JSON file.
- **[Risk] Javascript Dependency** → [Mitigation] Use the existing pattern where the base layout provides a consistent experience even if search is loading.
- **[Risk] Schema Drift** → [Mitigation] Consolidate field normalization into the data ingestion layer (Python) rather than just the presentation layer (JS).
