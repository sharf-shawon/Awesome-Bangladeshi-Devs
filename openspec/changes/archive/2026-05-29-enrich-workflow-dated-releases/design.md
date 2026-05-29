## Context

The `Daily Enrichment` workflow currently automates data updates but lacks automated tagging and releases. Historical tags exist in the repository, but they appear to have been created manually or by a different process that isn't currently active in the `enrich.yml` workflow.

## Goals / Non-Goals

**Goals:**
- Automate Git tag creation matching the `YYYY-MM-DD` pattern.
- Automate GitHub release creation titled `Stats for YYYY-MM-DD`.
- Ensure the workflow handles cases where a tag might already exist.

**Non-Goals:**
- Changing the enrichment logic itself.
- Modifying the site build or deployment process (beyond triggers).

## Decisions

### 1. Use Git commands for tagging
We will use standard Git commands within the `Commit and push changes` step or a subsequent step to create the tag. This allows us to easily use the current date in the `YYYY-MM-DD` format.
- **Rationale**: Avoids extra dependencies for a simple task.
- **Alternatives**: Using a third-party tagging action.

### 2. Use `softprops/action-gh-release` for release creation
We will use this well-established action to create the GitHub release.
- **Rationale**: Simplifies the API calls for release creation and allows for easy expansion (e.g., adding assets) later.
- **Alternatives**: Using `gh release create` directly via the GitHub CLI (which is available on GitHub runners). Given the project already uses some custom scripts, `gh release create` is also a strong candidate. However, `action-gh-release` is more declarative in YAML. We will stick with `softprops/action-gh-release` or `gh release create` based on simplicity. Let's choose `gh release create` to minimize external action dependencies since it's built-in.

### 3. Suffix for duplicate tags
If a tag for the current date already exists, we will append a suffix (e.g., `-v2`, `-v3`) or simply skip if it's a re-run of the same day's data. For simplicity and matching past patterns (which don't show suffixes), we will check for existence and skip or overwrite if appropriate. Given these are daily stats, one tag per day is the norm.

## Risks / Trade-offs

- **[Risk]** Tag collision if the workflow runs multiple times a day. → **Mitigation**: Add a check to see if the tag already exists, or append a sequence number.
- **[Risk]** Permissions failure. → **Mitigation**: Ensure `contents: write` permission is explicitly set for the `GITHUB_TOKEN`.
