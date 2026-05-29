## 1. Defensive Refactoring

- [x] 1.1 Implement node filtering for repositories in `src/enrich_data.py`.
- [x] 1.2 Replace direct subscript access for repository fields with `.get()`.
- [x] 1.3 Add null-checks for `contributionsCollection` and its sub-fields.
- [x] 1.4 Refactor repository topics extraction to handle `null` topics.

## 2. Validation

- [x] 2.1 Run the enrichment script with `--force` on the full dataset to verify stability.
- [x] 2.2 Verify that users with private or restricted profile data no longer cause script crashes.
