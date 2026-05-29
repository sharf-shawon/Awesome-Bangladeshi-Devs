## Context

The community's enriched dataset contains 3,600+ user records and 31,000+ repository records. While this data is rich in metadata (timestamps, topics, company names), the current stats page only visualizes two surface-level metrics. We need to refactor the build-time data aggregation to support a more complex "storytelling" UI.

## Goals / Non-Goals

**Goals:**
- Aggregate community join-years, top topics, and top organizations at build time.
- Identify the absolute top 10 most starred repositories in the community.
- Integrate `Chart.js` for a lightweight, interactive growth timeline.
- Maintain a fast, static build with no runtime database.

**Non-Goals:**
- Implementing individual charts for all 3,600 developers.
- Real-time updates (stats remain build-time consistent).

## Decisions

### 1. Build-Time Aggregation Logic
**Decision:** Implement complex tallying logic in `site/_data/stats.js`.
**Rationale:** Processing 31,000 repositories and 3,600 users client-side would be too heavy. By performing the Counters and sorting at build-time in Node.js, we output a compact, pre-calculated `stats` object to the template.

### 2. Lightweight Charts
**Decision:** Use `Chart.js` (via CDN) for the community timeline.
**Rationale:** It's the industry standard for lightweight, responsive charts. We will pass the pre-calculated arrays (e.g., `[2010, 2011, ...]` and `[5, 12, ...]`) directly into the script tag.

### 3. Data Cleaning (Normalization)
**Decision:** Implement normalization for the `company` field (stripping whitespace, removing `@`, lowercasing).
**Rationale:** Company data is often entered inconsistently (e.g., "@Optimizely" vs "Optimizely"). Normalization ensures hubs like "BRAC University" or "Brain Station 23" are accurately represented.

### 4. Topic Extraction
**Decision:** Flatten the `featured_repos[].topics` array from all users, filter out "noise" (e.g., username-specific tags), and take the top 20.
**Rationale:** This reveals the true technical domains the community is focused on (e.g., "web", "android", "machine-learning").

## Risks / Trade-offs

- **[Risk] Build Time Increase** → [Mitigation] Node.js `Counter` logic is highly efficient; even with 30k items, the aggregation should finish in under 1 second.
- **[Risk] Chart.js Load Time** → [Mitigation] Use the minified CDN and only initialize the chart when it enters the viewport.
