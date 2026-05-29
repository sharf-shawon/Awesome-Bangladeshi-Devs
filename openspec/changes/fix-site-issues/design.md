## Context

The initial v2 deployment failed to render templates because the source directory `site/` was ignored by a root `.gitignore` entry intended for `mkdocs`. Additionally, several routes were missing or incorrectly configured, leading to 404 errors.

## Goals / Non-Goals

**Goals:**
- **Build Restoration**: Ensure `site/` templates are processed regardless of `.gitignore`.
- **Navigation Completeness**: Fix all broken links in the header.
- **Data Integrity**: Ensure the `/stats/` page correctly displays the language distribution.

**Non-Goals:**
- **Re-enrichment**: This change does not touch the data enrichment scripts.
- **UI Redesign**: No major visual changes; focus on bug fixes.

## Decisions

### 1. Disable .gitignore for Eleventy Build
- **Rationale**: Eleventy's default behavior of respecting `.gitignore` is colliding with the project's existing ignore rules for other tools. Disabling this at the config level is the safest way to ensure the `site/` directory is always processed.
- **Implementation**: `eleventyConfig.setUseGitIgnore(false)` in `.eleventy.js`.

### 2. Move Language Distribution to stats.js
- **Rationale**: Currently, `stats.njk` tries to use the global `languages` data, which contains the full `devs` array for every language. This causes extreme memory pressure and template engine failures. Moving a summarized version into `stats.js` ensures it is lightweight and readily available.
- **Implementation**: Update `site/_data/stats.js` to return a `top_languages` array with counts only.

### 3. Explicit Permalink for Languages Index
- **Rationale**: Eleventy's default mapping for `site/languages-index.njk` is `/languages-index/`. Explicitly setting the permalink ensures it matches the navigation link.

## Risks / Trade-offs

- **[Risk] Unintended Files in Build** → **Mitigation**: Use explicit `eleventyConfig.addPassthroughCopy` and `templateFormats` to control exactly what ends up in `_site`.
- **[Risk] Large Projects Page** → **Mitigation**: Limit the initial list to the top 100 repositories by stars.
