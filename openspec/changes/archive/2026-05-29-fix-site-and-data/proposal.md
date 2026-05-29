## Why

The system currently faces two critical stability issues and a functional gap: a Python script crash during data enrichment due to schema mismatches, a 404 error on the programming languages index page, and a lack of interactive discovery tools for community projects.

## What Changes

- **Reliability Fix**: Update `src/enrich_data.py` to handle both legacy (`last_repo_fetched_at`) and current (`enriched_at`) schema fields, preventing `KeyError` crashes.
- **Routing Fix**: Add explicit permalinks to the languages index to resolve 404 errors.
- **Project Discovery**: Implement a client-side search, filtering (by language), and sorting (by stars/forks) system for the community projects page.
- **Build Optimization**: Filter the projects search index to include only repositories with significant community interest (e.g., stars > 5) to maintain performance.

## Capabilities

### New Capabilities
- `advanced-projects-search`: Interactive discovery tool for community repositories with client-side filtering and sorting.

### Modified Capabilities
- `site-generation`: Update routing and permalink logic to ensure navigation consistency.
- `data-enrichment`: Enhance script robustness and schema compatibility for long-term data reliability.

## Impact

- **Data Pipeline**: More resilient enrichment process that survives schema evolutions.
- **Site Performance**: Reduced HTML size for the projects page by moving to client-side rendering for the full list.
- **User Experience**: Restored navigation and improved searchability for 30k+ community repositories.
