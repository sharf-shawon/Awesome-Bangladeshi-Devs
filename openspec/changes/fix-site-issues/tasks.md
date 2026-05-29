## 1. Build and Configuration Fixes

- [x] 1.1 Update `.eleventy.js` to use `eleventyConfig.setUseGitIgnore(false)`
- [x] 1.2 Update `site/languages-index.njk` with `permalink: /languages/`
- [x] 1.3 Update `site/_data/stats.js` to include `top_languages` distribution data
- [x] 1.4 Update `site/stats.njk` to use `stats.top_languages` for the chart

## 2. New Pages and Navigation

- [x] 2.1 Implement `site/projects.njk` with top repository listing
- [ ] 2.2 Add `projects` search support to `site/index.njk` (optional, if time permits)
- [x] 2.3 Verify all header links in `site/_includes/base.njk` match permalinks

## 3. Validation

- [ ] 3.1 Run `npm run build` and verify `_site` directory contains expected files
- [ ] 3.2 Manually check `/languages/`, `/projects/`, and `/stats/` locally
