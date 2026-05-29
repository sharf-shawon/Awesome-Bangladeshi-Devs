## MODIFIED Requirements

### Requirement: Enrich developer metadata
The system SHALL fetch detailed profile information and activity stats for all users in `data/users.json` and existing records in `data/users-enriched.json` using the GitHub GraphQL API. It MUST handle records with missing or legacy timestamp fields (`last_repo_fetched_at`) gracefully by treating them as eligible for re-enrichment.

#### Scenario: Incremental enrichment
- **WHEN** the enrichment script runs without the `--force` flag
- **THEN** it skips users who were enriched within the last 24 hours, safely resolving timestamps from either `enriched_at` or `last_repo_fetched_at` fields

#### Scenario: Batch processing
- **WHEN** fetching data for multiple users
- **THEN** the system uses GraphQL aliases to fetch up to 20 users in a single request
