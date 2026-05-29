## Why

The domain name "bangladeshidevs.com" is currently hardcoded in several SEO-critical files (`base.njk`, `sitemap.njk`, `robots.njk`). This prevents the site from working correctly out-of-the-box when deployed to a different custom domain or a standard GitHub Pages URL (e.g., `user.github.io/repo`).

## What Changes

- **Dynamic URL Data**: Create a global data file `site/_data/site.js` that resolves the base URL dynamically by checking the `SITE_URL` environment variable or the root `CNAME` file.
- **Template Refactoring**: Update `base.njk`, `sitemap.njk`, and `robots.njk` to use `site.url` instead of hardcoded strings.

## Capabilities

### New Capabilities
- `dynamic-url-resolution`: Logic to determine the site's base URL from the environment or configuration files.

### Modified Capabilities
- `seo-and-indexing`: Update assets to use the resolved dynamic URL.

## Impact

- **Portability**: The site can be deployed to any domain or GitHub Pages environment without code changes.
- **Maintainability**: Centralizes domain configuration in a single data file.
