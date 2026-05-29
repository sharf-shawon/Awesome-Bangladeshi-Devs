## ADDED Requirements

### Requirement: Display top projects
The system SHALL provide a "Projects" page that lists repositories from the enriched developer dataset, sorted by star count.

#### Scenario: Projects page rendering
- **WHEN** user visits `/projects/`
- **THEN** the page displays a grid of repositories with names, descriptions, stars, and owners.

#### Scenario: Project filtering
- **WHEN** user searches on the projects page
- **THEN** the system filters results by repository name or description.
