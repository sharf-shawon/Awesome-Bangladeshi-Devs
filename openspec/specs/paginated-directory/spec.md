## ADDED Requirements

### Requirement: Statically paginated directory
The system SHALL provide a paginated directory at `/all/` containing all enriched developers.

#### Scenario: Directory generation
- **WHEN** the site is built
- **THEN** it generates a series of HTML pages (e.g., `/all/index.html`, `/all/1/index.html`) using Eleventy pagination

#### Scenario: Authors linked for discovery
- **WHEN** a crawler traverses the `/all/` directory
- **THEN** every developer profile page is discoverable via standard anchor tags
