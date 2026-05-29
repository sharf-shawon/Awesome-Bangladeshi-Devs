## MODIFIED Requirements

### Requirement: Build static site with Eleventy
The system SHALL use Eleventy 3.x (ESM) to generate a static website from the `site/` source and `data/users-enriched.json`. The build process SHALL ignore the root `.gitignore` to ensure the `site/` directory is processed correctly.

#### Scenario: Site build success
- **WHEN** `npm run build` is executed
- **THEN** the `_site/` directory is populated with HTML pages for the homepage, developer profiles, language indices, and projects.

### Requirement: Route consistency
The system SHALL ensure all navigation links have corresponding valid routes with correct permalinks.

#### Scenario: Language index route
- **WHEN** the site is built
- **THEN** the language listing page is available at `/languages/index.html`.
