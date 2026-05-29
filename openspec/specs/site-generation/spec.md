## ADDED Requirements

### Requirement: Build static site with Eleventy
The system SHALL use Eleventy 3.x (ESM) to generate a static website from the `site/` source and `data/users-enriched.json`. It MUST include a comprehensive stats page that tells the community story through processed historical and organizational data.

#### Scenario: Site build success
- **WHEN** `npm run build` is executed
- **THEN** the `_site/` directory is populated with HTML pages for the homepage, developer profiles, and language indices, including a valid route at `/languages/`

#### Scenario: Search index generation
- **WHEN** the `build_search_index.py` script is run
- **THEN** it creates a JSON file with abbreviated keys to minimize payload size

#### Scenario: Storytelling stats page
- **WHEN** `npm run build` is executed
- **THEN** the `_site/stats/index.html` is generated with pre-calculated growth data, repository leaderboards, and hub rankings
