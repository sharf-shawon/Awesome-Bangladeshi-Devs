## 1. Dynamic URL Logic

- [x] 1.1 Create `site/_data/site.js` with resolution logic (Env > CNAME > Localhost).

## 2. Template Refactoring

- [x] 2.1 Update `site/_includes/base.njk` to use `site.url` for OG, Twitter, and Canonical tags.
- [x] 2.2 Update `site/sitemap.njk` to use `site.url` for `<loc>` tags.
- [x] 2.3 Update `site/robots.njk` to use `site.url` for the `Sitemap:` path.

## 3. Validation

- [x] 3.1 Run `npm run build` and verify `_site/sitemap.xml` contains absolute URLs with the `CNAME` domain.
- [x] 3.2 Verify `_site/robots.txt` contains the correct sitemap path.
