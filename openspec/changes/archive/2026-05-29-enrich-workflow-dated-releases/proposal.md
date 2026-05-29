## Why

Currently, the `Daily Enrichment` workflow (`enrich.yml`) commits and pushes data updates but does not create Git tags or GitHub releases. Automated tagging and releases will provide a historical record of data snapshots, making it easier to track changes over time and providing a stable reference for each day's data.

## What Changes

- Modify `.github/workflows/enrich.yml` to generate a Git tag for each successful daily enrichment run.
- Generate a GitHub release corresponding to each new tag.
- Match the existing date-based tagging pattern (`YYYY-MM-DD`).
- Ensure the release title and description are consistent with historical patterns or project conventions.

## Capabilities

### New Capabilities
- `automation-tagging-and-releases`: Automates the creation of Git tags and GitHub releases in the CI/CD pipeline, ensuring every data snapshot is uniquely identified by date.

### Modified Capabilities
<!-- No requirement changes to existing scripts, only to the automation workflow -->

## Impact

- **Affected Code**: `.github/workflows/enrich.yml`.
- **Infrastructure**: GitHub repository tags and releases.
- **Dependencies**: Uses `softprops/action-gh-release` or standard Git commands within the workflow.
