## ADDED Requirements

### Requirement: Interactive project discovery
The system SHALL provide an interactive projects page that allows users to explore community repositories with real-time feedback. Each project card MUST hyperlink the developer's avatar and username to their platform profile (`/dev/<username>/`).

#### Scenario: Filter by language
- **WHEN** a user selects a language from the filter list
- **THEN** the projects gallery immediately updates to show only repositories primarily written in that language

#### Scenario: Search by keyword
- **WHEN** a user types a keyword into the project search box
- **THEN** the system performs a fuzzy search across repository names and descriptions, updating the gallery in real-time

#### Scenario: Dynamic sorting
- **WHEN** a user changes the sort order (e.g., from Stars to Forks)
- **THEN** the gallery re-orders the repositories based on the selected metric without a page reload

#### Scenario: Profile navigation
- **WHEN** a user clicks on the developer's avatar or username in a project card
- **THEN** they are navigated to the developer's dedicated profile page

### Requirement: Optimized projects index
The system SHALL generate a dedicated JSON index containing ALL community repositories, removing previous quality thresholds to ensure comprehensive discovery. It MUST output valid JSON syntax by disabling HTML-escaping for the JSON structure and MUST use compact formatting by stripping unnecessary whitespace.

#### Scenario: Index comprehensiveness
- **WHEN** the site build occurs
- **THEN** a `data/projects.json` file is generated containing all community repositories in a valid, compact JSON format
