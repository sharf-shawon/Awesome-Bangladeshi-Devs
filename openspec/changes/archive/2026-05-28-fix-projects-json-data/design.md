## Context

The community projects discovery page relies on a dynamically generated `data/projects.json` file. During initial implementation, the Nunjucks template was configured with default escaping, resulting in HTML-encoded JSON. The nested loops also introduced significant whitespace bloat.

## Goals / Non-Goals

**Goals:**
- Fix the `projects.json` syntax error by outputting raw JSON.
- Collapse empty lines in the generated data file.
- Verify the build output.

**Non-Goals:**
- Changing the community-interest threshold (stars > 5).
- Modifying the client-side `Fuse.js` logic.

## Decisions

### 1. JSON Output Safety
**Decision:** Use the `| safe` filter in Nunjucks for the final JSON dump.
**Rationale:** Nunjucks automatically escapes quotes for HTML security. Since this template is specifically generating a JSON file, we must disable this escaping to produce valid JSON syntax.

### 2. Whitespace Control
**Decision:** Apply Nunjucks whitespace stripping tags (`{%- ... -%}`) to all loops and conditionals in `site/projects-data.njk`.
**Rationale:** Without control tags, each iteration of the loop (for 31,000 repositories) creates a new line, even for repos that are filtered out. Stripping these reduces the file size from ~1.5MB to ~500KB.

## Risks / Trade-offs

- **[Risk] Unexpected characters in descriptions** → [Mitigation] The `| json` filter already handles escaping special characters within strings; the `| safe` filter only prevents Nunjucks from escaping the JSON structure itself (like quotes and braces).
