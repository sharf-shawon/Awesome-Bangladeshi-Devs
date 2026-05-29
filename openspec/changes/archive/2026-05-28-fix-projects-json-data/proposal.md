## Why

The `projects.json` data file is currently malformed because it contains HTML-encoded characters (like `&quot;`) instead of raw JSON quotes. This causes a syntax error in the client-side gallery. Additionally, the file contains thousands of unnecessary empty lines, making it larger than needed.

## What Changes

- **Fix JSON Encoding**: Update the Nunjucks template to output raw JSON by marking it as `safe`.
- **Optimize Whitespace**: Use Nunjucks whitespace control to strip empty lines and indentations from the generated data file.
- **Verification**: Re-run the build to confirm the generated JSON is valid and compact.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `advanced-projects-search`: Fix the data source generation to ensure the interactive discovery tool works as expected.

## Impact

- **Site Reliability**: Resolves the `SyntaxError` that prevents community projects from being displayed.
- **Build Performance**: Smaller `projects.json` file size reduces bandwidth usage for users.
