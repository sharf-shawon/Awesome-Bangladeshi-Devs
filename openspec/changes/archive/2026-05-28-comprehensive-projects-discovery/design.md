## Context

The community projects page currently filters out repositories with 5 or fewer stars to maintain client-side performance, restricting the searchable index to ~1,800 out of ~31,000 available repositories. To provide a comprehensive discovery experience, we need to expose the entire dataset. However, rendering 31,000 DOM elements simultaneously will cause severe browser lag. We also need to connect the project authors back to their platform profiles.

## Goals / Non-Goals

**Goals:**
- Include all repositories in the client-side search index.
- Implement efficient batch rendering (lazy loading) to maintain UI responsiveness.
- Link project authors to their `/dev/<username>/` profiles.

**Non-Goals:**
- Implementing server-side search or pagination APIs.
- Storing full repository readmes or deep contents in the search index.

## Decisions

### 1. Complete Dataset Export
**Decision:** Remove the `stars > 5` conditional filter in `site/projects-data.njk`.
**Rationale:** Fulfills the requirement to make all Bangladeshi developer projects searchable in one place.

### 2. Batch Rendering via IntersectionObserver
**Decision:** Implement an `IntersectionObserver` in `assets/projects.js` to lazy-load project cards.
**Rationale:** Instead of rendering the entire `filteredProjects` array at once, we will render chunks (e.g., 50 projects at a time). A sentinel `<div>` placed at the bottom of the grid will trigger the observer when scrolled into view, appending the next batch of projects. This keeps the initial DOM light and scrolling smooth.

### 3. Native Profile Routing
**Decision:** Wrap the developer's avatar and username in the project card template with `<a href="/dev/${repo.o.toLowerCase()}/">`.
**Rationale:** Provides seamless internal navigation, mirroring the behavior established on the homepage. Using `.toLowerCase()` ensures route matching.

## Risks / Trade-offs

- **[Risk] Large JSON Payload Transfer** → [Mitigation] A JSON file with 31,000 abbreviated objects will be relatively large (estimated ~10-15MB uncompressed). However, static hosts like GitHub Pages automatically apply GZIP/Brotli compression, which typically reduces JSON size by 80-90% during network transfer.
- **[Risk] Fuse.js Memory/CPU Usage** → [Mitigation] Indexing 31k items client-side requires more memory. We will stick to indexing only the essential keys (`n`, `d`, `o`) and rely on the existing base layout to display content while the index builds asynchronously.
