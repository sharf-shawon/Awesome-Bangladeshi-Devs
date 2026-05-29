## ADDED Requirements

### Requirement: Lazy loading project cards
The system SHALL progressively render project cards as the user scrolls down the page to maintain UI performance with a large dataset.

#### Scenario: Initial load
- **WHEN** the projects page is first loaded or a new search/filter is applied
- **THEN** the system renders a limited initial batch of project cards

#### Scenario: Infinite scroll
- **WHEN** the user scrolls near the bottom of the rendered project list
- **THEN** the system automatically renders the next batch of project cards until all filtered results are displayed
