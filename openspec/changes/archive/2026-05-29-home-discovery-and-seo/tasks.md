## 1. Homepage Lazy Loading

- [x] 1.1 Update `site/index.njk` to include a sentinel element for lazy loading.
- [x] 1.2 Refactor the inline script in `site/index.njk` to implement batch rendering using `IntersectionObserver` and the `search-index.json`.

## 2. Paginated Directory

- [x] 2.1 Create `site/all.njk` with Eleventy pagination to generate a list of all developers.
- [x] 2.2 Style the `/all/` directory to match the homepage grid.
- [x] 2.3 Add a link to the `/all/` directory in the site footer or header.

## 3. SEO & Indexing Infrastructure

- [x] 3.1 Update `site/_includes/base.njk` to support dynamic `seo_title` and `seo_description`.
- [x] 3.2 Update `site/dev.njk` to provide specific SEO metadata from the developer's profile.
- [x] 3.3 Create `site/sitemap.njk` with `permalink: /sitemap.xml` to generate a Google-compatible XML sitemap.
- [x] 3.4 Create `site/robots.njk` with `permalink: /robots.txt` that points to the sitemap.
- [x] 3.5 Add Open Graph and Twitter Card tags to `site/_includes/base.njk`.

## 4. Validation

- [x] 4.1 Run `npm run build` and verify `_site/sitemap.xml` and `_site/robots.txt` exist and are valid.
- [x] 4.2 Confirm that the `/all/` directory pages are generated and navigate correctly.
- [x] 4.3 Verify that the homepage successfully lazy-loads developers beyond the initial batch.
