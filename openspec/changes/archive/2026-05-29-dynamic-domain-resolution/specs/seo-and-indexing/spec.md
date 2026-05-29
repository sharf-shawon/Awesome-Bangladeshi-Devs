## ADDED Requirements

### Requirement: Dynamic Base URL
The system SHALL resolve the site's base URL dynamically at build time.

#### Scenario: Resolve from CNAME
- **WHEN** a `CNAME` file exists in the root directory
- **THEN** the system uses its content (e.g., `memo.pro.bd`) as the domain, prefixed with `https://`

#### Scenario: Resolve from Environment
- **WHEN** the `SITE_URL` environment variable is set
- **THEN** the system prioritizes this value over the `CNAME` file

## MODIFIED Requirements

### Requirement: Automated sitemap generation
The system SHALL generate a valid `sitemap.xml` file at build time using the dynamically resolved base URL.

#### Scenario: Sitemap build
- **WHEN** the site is built
- **THEN** `_site/sitemap.xml` contains absolute URLs starting with the resolved dynamic URL

### Requirement: Robots.txt configuration
The system SHALL generate a `robots.txt` file that explicitly links to the `sitemap.xml` using the dynamically resolved base URL.

#### Scenario: Robots file creation
- **WHEN** the site is built
- **THEN** `_site/robots.txt` contains the correct absolute path to the sitemap
