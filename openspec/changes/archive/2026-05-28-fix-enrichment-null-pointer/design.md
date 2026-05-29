## Context

The enrichment script `src/enrich_data.py` processes thousands of GitHub users. The GitHub GraphQL API can return `null` nodes for repositories if a repository is in an inconsistent state or if there are permission issues. The current code assumes all nodes in the `repositories` array are objects and attempts to subscript them, leading to `TypeError`.

## Goals / Non-Goals

**Goals:**
- Eliminate `TypeError` crashes during data enrichment.
- Ensure all loops iterating over API nodes handle `None` values.
- Standardize defensive data extraction for all user and repository fields.

**Non-Goals:**
- Changing the GraphQL query itself.
- Modifying the scoring algorithm.

## Decisions

### 1. Immediate Filtering of Nodes
**Decision:** All lists of nodes returned by the API (repositories, topics, etc.) will be filtered for truthiness immediately before processing.
**Rationale:** This is the most efficient way to ensure downstream loops only deal with valid objects, avoiding multiple `if r:` checks inside nested loops.

### 2. Dict.get() with Defaults
**Decision:** Replace direct subscript access (`r['key']`) with `.get('key', default)`.
**Rationale:** Provides a safe fallback for missing fields within valid objects.

### 3. Null-Coalescing for Contributions
**Decision:** Treat missing `contributionsCollection` as an empty dictionary.
**Rationale:** Some profiles may have restricted contribution data. Defaulting to an empty dict prevents the script from crashing while still allowing it to process other profile metrics.

## Risks / Trade-offs

- **[Risk] Data incompleteness** → [Mitigation] Skipping a single null repository node is preferable to crashing the entire batch of 20 users.
