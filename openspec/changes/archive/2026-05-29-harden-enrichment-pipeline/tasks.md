## 1. Network Layer Hardening

- [x] 1.1 Implement a `TokenManager` class in `src/enrich_data.py` to track rate limit headers and handle proactive rotation.
- [x] 1.2 Initialize a `requests.Session` with a `urllib3` `Retry` adapter to handle 502, 503, and 504 errors automatically.
- [x] 1.3 Update `fetch_batch` to use the `TokenManager` and `Session` for all requests.

## 2. Enrichment Script Refactoring

- [x] 2.1 Update the default `batch_size` from 20 to 10 in the `main` loop.
- [x] 2.2 Add a recursive split fallback: if a batch of 10 fails after session-level retries, split into two batches of 5 and retry.
- [x] 2.3 Wrap the primary request call in a try-except block to catch `ChunkedEncodingError` and other protocol-level failures.

## 3. Validation

- [x] 3.1 Run the enrichment script with multiple tokens and verify that rotation occurs when `X-RateLimit-Remaining` is low.
- [x] 3.2 Verify that the pipeline completes without 502 errors for a large segment of the community data.
