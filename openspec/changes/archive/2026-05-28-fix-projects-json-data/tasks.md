## 1. Data Generation Fix

- [x] 1.1 Update `site/projects-data.njk` with `| safe` filter for JSON output
- [x] 1.2 Update `site/projects-data.njk` with whitespace control tags (`{%- ... -%}`)
- [x] 1.3 Verify `npm run build` generates a valid and compact `_site/data/projects.json` file

## 2. Validation

- [x] 2.1 Confirm the Projects gallery loads without `SyntaxError` in the browser console
- [x] 2.2 Verify searching and filtering work as expected with the fixed data source
