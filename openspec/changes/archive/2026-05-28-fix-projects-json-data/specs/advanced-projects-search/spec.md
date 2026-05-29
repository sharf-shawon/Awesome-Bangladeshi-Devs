## MODIFIED Requirements

### Requirement: Optimized projects index
The system SHALL generate a dedicated JSON index for community repositories, filtered by a minimum quality threshold (e.g., stars > 5). It MUST output valid JSON syntax by disabling HTML-escaping for the JSON structure and MUST use compact formatting by stripping unnecessary whitespace.

#### Scenario: Index size optimization
- **WHEN** the site build occurs
- **THEN** a `data/projects.json` file is generated containing only the top-tier repositories in a valid, compact JSON format
