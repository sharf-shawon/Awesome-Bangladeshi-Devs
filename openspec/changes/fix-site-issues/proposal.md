## Why

The current deployment has several navigation and data visibility issues:
1.  The `/site` entry in `.gitignore` causes Eleventy to skip template processing, resulting in a broken or empty site build.
2.  The `/languages/` and `/projects/` links point to 404s because of missing permalinks and templates.
3.  The community statistics page is missing the language distribution chart due to data load order and shadowing issues.

## What Changes

- **Build Fix**: Configure Eleventy to ignore `.gitignore` for the `site/` source directory.
- **Navigation Fix**:
    - Add explicit `permalink` to `site/languages-index.njk`.
    - Implement `site/projects.njk` to showcase top community projects.
- **Data Fix**:
    - Optimize `site/_data/stats.js` to provide summary language data directly.
    - Improve `readableDate` filter robustness.

## Capabilities

### New Capabilities
- `projects-showcase`: A new page to discover the most popular Bangladeshi repositories.

### Modified Capabilities
- `site-generation`: Update build configuration and routing logic.

## Impact

- **Build Performance**: Slightly increased build time due to processing the new projects page.
- **SEO**: Improved site discoverability with proper routing and 404 handling.
- **User Experience**: Restores expected navigation functionality across all header links.
