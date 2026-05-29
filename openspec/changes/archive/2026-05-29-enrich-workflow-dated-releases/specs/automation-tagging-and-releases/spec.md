## ADDED Requirements

### Requirement: Automated Git Tagging
The `Daily Enrichment` workflow SHALL automatically create a Git tag for each successful run that results in a commit. The tag name MUST follow the `YYYY-MM-DD` format, matching the current date of the execution.

#### Scenario: Successful Tag Creation
- **WHEN** the enrichment job completes successfully and commits changes
- **THEN** the workflow creates a Git tag with the format `YYYY-MM-DD` and pushes it to the repository

#### Scenario: Handle Existing Tag
- **WHEN** a tag with the current date already exists (e.g., due to a re-run)
- **THEN** the workflow SHOULD skip tag creation or use a unique suffix (e.g., `-v2`) to avoid conflicts, but primary focus is unique daily tags.

### Requirement: GitHub Release Creation
The `Daily Enrichment` workflow SHALL create a GitHub release for each newly created tag. The release title SHOULD include the date and a brief summary of the enrichment.

#### Scenario: Successful Release Creation
- **WHEN** a new tag is pushed by the workflow
- **THEN** the workflow creates a GitHub release with the tag name as the version and a title like "Daily Data Enrichment - YYYY-MM-DD"

#### Scenario: Release Assets
- **WHEN** a release is created
- **THEN** it SHOULD optionally include a summary of changes or the generated `data/users-enriched.json` as a release asset, though the primary goal is the release record itself.
