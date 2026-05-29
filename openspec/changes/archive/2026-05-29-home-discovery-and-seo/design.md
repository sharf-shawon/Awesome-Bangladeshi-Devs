## Context

The site currently relies on static compilation for the most prominent parts of the UI, but this approach is hitting scalability limits for discovery (showing 3,600+ devs) and search engine discoverability. We need a hybrid approach: interactive discovery for humans (lazy loading) and crawlable indexes for machines (pagination and sitemaps).

## Goals / Non-Goals

**Goals:**
- Transition the homepage to a batched rendering system.
- Implement a statically paginated directory at `/all/`.
- Generate `sitemap.xml` and `robots.txt` based on the full page collection.
- Standardize dynamic SEO tags in the base layout.

**Non-Goals:**
- Redesigning the search algorithm or scoring metrics.
- Changing the build system from Eleventy.

## Decisions

### 1. Hybrid Homepage Discovery
**Decision:** Implement a batched list on the homepage that uses the search index JSON.
**Rationale:** This allows us to reuse the existing `search-index.json` payload (~900KB) to show a "Top Developers" list that grows as the user scrolls, similar to the Projects page implementation.

### 2. Static Pagination for SEO
**Decision:** Use Eleventy Pagination to generate `/all/`, `/all/1/`, `/all/2/`, etc.
**Rationale:** While lazy loading is great for users, search engine bots need physical links to discover profile pages. A paginated directory ensures that every `/dev/<username>/` route is linked from a crawlable index.

### 3. Build-Time Meta Generation
**Decision:** Create `site/sitemap.njk` and `site/robots.njk` to output text-based assets.
**Rationale:** Using Nunjucks to generate these files ensures they are always perfectly in sync with the actual routes generated during the build.

### 4. Dynamic Base Template Context
**Decision:** Update `site/_includes/base.njk` to check for page-specific variables (e.g., `seo_description`).
**Rationale:** Enables individual templates (like `dev.njk`) to "override" the generic site description with specific developer data, improving search engine snippet quality.

## Risks / Trade-offs

- **[Risk] Search Index Size** → [Mitigation] We already have a compact index. For 3,600 users, 900KB is acceptable for a modern web app.
- **[Risk] Crawl Budget** → [Mitigation] By providing a clean sitemap and a paginated directory, we make it as easy as possible for bots to traverse the 4,000+ total pages without getting lost in loops.
