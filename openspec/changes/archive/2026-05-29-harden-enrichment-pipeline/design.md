## Context

The enrichment script `src/enrich_data.py` currently fetches batches of 20 users per GraphQL request. This has led to 502 Bad Gateway errors and `ChunkedEncodingError` due to query complexity and server-side timeouts. Furthermore, while the environment supports multiple `GH_TOKENS`, the current rotation logic is reactive (only on 403/429) rather than proactive, which can lead to unnecessary retries and slower execution.

## Goals / Non-Goals

**Goals:**
- Eliminate 502/timeout errors by reducing request weight.
- Implement proactive token rotation based on rate limit headers.
- Add robust retry logic for transient network and gateway errors.

**Non-Goals:**
- Splitting the GraphQL query into multiple smaller queries (preserving current structure).
- Implementing a persistent token registry or database.

## Decisions

### 1. Reduced Default Batch Size
**Decision:** Change the default `batch_size` from 20 to 10.
**Rationale:** GraphQL query complexity is multiplicative. Reducing the number of users per request linearly reduces the execution time for the GitHub backend, bringing it well under the proxy timeout threshold.

### 2. Proactive Token Management
**Decision:** Track the `X-RateLimit-Remaining` header for each token in memory.
**Rationale:** By rotating to the next token *before* hitting zero (e.g., at < 10 remaining), we avoid the overhead of receiving and handling 403/429 error responses, making the pipeline smoother and faster.

### 3. Exponential Backoff and Jitter
**Decision:** Use the `urllib3` `Retry` adapter within a `requests.Session`.
**Rationale:** Provides a standard, battle-tested way to handle 502, 503, and 504 errors with automatic backoff, reducing code complexity in the main script.

### 4. Recursive Batch Splitting (Fallback)
**Decision:** If a batch of 10 still fails with a 502 after retries, split it into two batches of 5.
**Rationale:** Some users (with massive amounts of contributions or repos) may be "heavy" enough to cause timeouts even in smaller batches. Recursion ensures these edge cases are eventually processed.

## Risks / Trade-offs

- **[Risk] Slower execution** → [Mitigation] While smaller batches take more requests, the reduction in failed/retried requests and proactive token rotation will result in a more predictable and often faster total completion time for large datasets.
