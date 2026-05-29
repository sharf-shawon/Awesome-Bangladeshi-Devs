## Why

The data enrichment script `src/enrich_data.py` is currently crashing when it encounters `null` repository nodes or missing contribution data in the GitHub GraphQL API response. This prevents the daily enrichment workflow from completing successfully, leading to stale developer data and potential build failures.

## What Changes

- **Defensive Repo Extraction**: Filter out `null` repository nodes immediately after fetching data.
- **Robust Field Lookups**: Use `.get()` and default fallbacks for nested fields like `stargazerCount`, `primaryLanguage`, and `repositoryTopics`.
- **Contribution Safety**: Add checks for the presence of `contributionsCollection` to prevent crashes on restricted or private profiles.
- **Topic Normalization**: Ensure topic extraction is robust against `null` entries in the topics array.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `data-enrichment`: Enhance script robustness and schema compatibility for long-term data reliability.

## Impact

- **Data Pipeline**: Fixes the immediate crash in GitHub Actions and ensures the pipeline can survive transient API data inconsistencies.
- **Code Quality**: Promotes defensive programming patterns in the data ingestion layer.
