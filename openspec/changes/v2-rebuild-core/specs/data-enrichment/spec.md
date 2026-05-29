## ADDED Requirements

### Requirement: Enrich developer metadata
The system SHALL fetch detailed profile information and activity stats for all users in `data/users.json` using the GitHub GraphQL API.

#### Scenario: Incremental enrichment
- **WHEN** the enrichment script runs without the `--force` flag
- **THEN** it skips users who were enriched within the last 24 hours

#### Scenario: Batch processing
- **WHEN** fetching data for multiple users
- **THEN** the system uses GraphQL aliases to fetch up to 20 users in a single request

### Requirement: Compute activity score
The system SHALL compute a normalized activity score (0-100) for each developer based on weighted metrics defined in `config/metrics.json`.

#### Scenario: Score normalization
- **WHEN** computing scores for the entire dataset
- **THEN** the system applies min-max normalization based on the current distribution of metrics
