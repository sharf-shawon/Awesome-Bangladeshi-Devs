## ADDED Requirements

### Requirement: Automated sitemap generation
The system SHALL generate a valid `sitemap.xml` file at build time containing all searchable routes.

#### Scenario: Sitemap build
- **WHEN** the site is built with Eleventy
- **THEN** a `_site/sitemap.xml` is created containing URLs for the home page, projects, stats, languages, and every developer profile

### Requirement: Robots.txt configuration
The system SHALL generate a `robots.txt` file that explicitly links to the `sitemap.xml`.

#### Scenario: Robots file creation
- **WHEN** the site is built
- **THEN** `_site/robots.txt` contains `Sitemap: https://bangladeshidevs.com/sitemap.xml`

### Requirement: Dynamic SEO metadata
The system SHALL provide dynamic `<title>` and `<meta name="description">` tags based on page content.

#### Scenario: Developer profile SEO
- **WHEN** a developer profile page is generated
- **THEN** the meta description contains the developer's bio, top language, and total stars
