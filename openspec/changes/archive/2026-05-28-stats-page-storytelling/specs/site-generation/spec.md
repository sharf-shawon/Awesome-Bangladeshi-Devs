## MODIFIED Requirements

### Requirement: Build static site with Eleventy
The system SHALL use Eleventy 3.x (ESM) to generate a static website from the `site/` source and `data/users-enriched.json`. It MUST include a comprehensive stats page that tells the community story through processed historical and organizational data.

#### Scenario: Storytelling stats page
- **WHEN** `npm run build` is executed
- **THEN** the `_site/stats/index.html` is generated with pre-calculated growth data, repository leaderboards, and hub rankings
