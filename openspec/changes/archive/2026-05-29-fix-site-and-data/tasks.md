## 1. Data Reliability Fixes

- [x] 1.1 Update `src/enrich_data.py` with safe `enriched_at` lookup using `last_repo_fetched_at` fallback
- [x] 1.2 Update `src/enrich_data.py` to correctly identify users needing enrichment from the combined dataset
- [x] 1.3 Verify enrichment script runs successfully on current `data/users-enriched.json` without `KeyError`

## 2. Site Routing & Build

- [x] 2.1 Update `site/languages-index.njk` with `permalink: /languages/`
- [x] 2.2 Ensure `.eleventy.js` configuration correctly processes the `site/` directory regardless of `.gitignore`
- [x] 2.3 Verify `npm run build` generates a valid `/languages/index.html` file

## 3. Advanced Projects Discovery

- [x] 3.1 Create `site/projects-data.njk` to generate an optimized `data/projects.json` (filtered by community interest threshold)
- [x] 3.2 Implement the Projects UI with search input, language filter chips, and sorting controls in `site/projects.njk`
- [x] 3.3 Implement client-side JavaScript to handle data fetching, Fuse.js search, and dynamic DOM rendering for the projects gallery
- [x] 3.4 Add "No results found" and "Loading" states to the projects gallery

## 4. Validation

- [x] 4.1 Execute `npm run build` and verify all routes (`/languages/`, `/projects/`, etc.) exist in `_site/`
- [x] 4.2 Perform manual verification of the projects search, filtering, and sorting functionality
