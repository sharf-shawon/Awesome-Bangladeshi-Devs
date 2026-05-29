## 1. Project Foundation

- [x] 1.1 Initialize `package.json` with Eleventy 3.x and ESM configuration
- [x] 1.2 Create `requirements.txt` with `requests`, `PyYAML`, and `pytest`
- [x] 1.3 Create `config/metrics.json` with scoring weights and location aliases
- [x] 1.4 Initialize `.eleventy.js` with ESM filters and passthrough copies
- [x] 1.5 Configure `pytest.ini` and add `__init__.py` files for package discovery

## 2. Core Python Scripts

- [x] 2.1 Implement `src/validate_data.py` for `users.json` schema validation
- [x] 2.2 Implement `src/process_issue.py` for automated issue handling (Add/Remove)
- [x] 2.3 Implement `src/enrich_data.py` with GraphQL batching and scoring logic
- [x] 2.4 Implement `src/build_search_index.py` for Fuse.js index generation
- [x] 2.5 Implement `src/generate_readme.py` for auto-generating the repository README

## 3. Eleventy Site Implementation

- [x] 3.1 Create `site/_data/` files (`enriched.js`, `languages.js`, `stats.js`) using ESM
- [x] 3.2 Implement `site/_includes/base.njk` with Tailwind v4 CDN and dark mode
- [x] 3.3 Create `site/index.njk` (Homepage) with Fuse.js search integration
- [x] 3.4 Create `site/dev.njk` (Developer Profiles) with pagination
- [x] 3.5 Create `site/languages.njk` and `site/stats.njk` pages

## 4. CI/CD Infrastructure

- [x] 4.1 Implement `.github/workflows/pipeline.yml` for CI, issue processing, and deployment
- [x] 4.2 Implement `.github/workflows/enrich.yml` for daily data updates
- [x] 4.3 Setup `.github/ISSUE_TEMPLATE/` for `add_developer` and `remove_developer`

## 5. Testing & Validation

- [x] 5.1 Create unit tests in `tests/` for all Python scripts using `pytest`
- [x] 5.2 Verify local build with `npm run build`
- [x] 5.3 Ensure generated `README.md` passes `awesome-lint`
