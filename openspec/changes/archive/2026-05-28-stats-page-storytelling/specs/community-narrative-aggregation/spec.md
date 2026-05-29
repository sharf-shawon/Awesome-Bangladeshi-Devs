## ADDED Requirements

### Requirement: Community growth aggregation
The system SHALL aggregate the number of developers joining GitHub per year based on the `created_at` field.

#### Scenario: Yearly join counts
- **WHEN** the site data is processed
- **THEN** it generates an object mapping years (e.g., 2010) to the count of new community members

### Requirement: Topic frequency analysis
The system SHALL extract and count all unique repository topics from the `featured_repos` list across all community members.

#### Scenario: Top topics discovery
- **WHEN** analyzing the repository dataset
- **THEN** it identifies the top 20 most frequently used topics, excluding generic boilerplate tags

### Requirement: Organizational hub mapping
The system SHALL aggregate developer counts by company/university name, applying normalization to handle casing and symbols.

#### Scenario: Top organization rankings
- **WHEN** processing the `company` field
- **THEN** it generates a ranked list of the top 10 hubs producing or employing community talent

### Requirement: Community Hall of Fame
The system SHALL identify the absolute top 10 most starred repositories in the entire Bangladeshi developer community.

#### Scenario: Global repository leaderboard
- **WHEN** scanning all repository records
- **THEN** it identifies repositories with the highest `stargazerCount` regardless of the developer's activity score
