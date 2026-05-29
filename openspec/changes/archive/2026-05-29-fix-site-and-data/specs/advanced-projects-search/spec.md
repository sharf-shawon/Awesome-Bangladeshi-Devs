## ADDED Requirements

### Requirement: Interactive project discovery
The system SHALL provide an interactive projects page that allows users to explore community repositories with real-time feedback.

#### Scenario: Filter by language
- **WHEN** a user selects a language from the filter list
- **THEN** the projects gallery immediately updates to show only repositories primarily written in that language

#### Scenario: Search by keyword
- **WHEN** a user types a keyword into the project search box
- **THEN** the system performs a fuzzy search across repository names and descriptions, updating the gallery in real-time

#### Scenario: Dynamic sorting
- **WHEN** a user changes the sort order (e.g., from Stars to Forks)
- **THEN** the gallery re-orders the repositories based on the selected metric without a page reload

### Requirement: Optimized projects index
The system SHALL generate a dedicated JSON index for community repositories, filtered by a minimum quality threshold (e.g., stars > 5).

#### Scenario: Index size optimization
- **WHEN** the site build occurs
- **THEN** a `data/projects.json` file is generated containing only the top-tier repositories, ensuring fast initial load times
