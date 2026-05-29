## Why

The data enrichment pipeline is currently suffering from 502 Bad Gateway errors and timeouts, primarily due to high GraphQL query complexity when fetching 20 users at once. Additionally, the pipeline needs smarter handling of multiple GitHub tokens to ensure it can rotate effectively when individual tokens approach their rate limits, preventing workflow failures during large-scale enrichment.

## What Changes

- **Optimized Batching**: Reduce the default batch size from 20 to 10 to decrease query complexity and prevent 502/timeout errors.
- **Smart Token Rotation**: Implement proactive token rotation by checking the `X-RateLimit-Remaining` header after every request, switching to the next available token if a threshold is reached.
- **Resilient Request Logic**: Add an exponential backoff retry mechanism for 502/503/504 errors.
- **Robust Error Handling**: Wrap network calls in try-except blocks to handle `ChunkedEncodingError` and other protocol-level failures gracefully.

## Capabilities

### New Capabilities
- `resilient-token-rotation`: Logic to smartly manage multiple API tokens and rotate them based on real-time rate limit headers.

### Modified Capabilities
- `data-enrichment`: Harden the enrichment process against network timeouts and API gateway errors.

## Impact

- **Pipeline Stability**: Eliminates the recurring 502 errors in GitHub Actions.
- **Enrichment Throughput**: Allows the script to process all 3,600+ users in a single run by utilizing the combined rate limits of all supplied tokens.
- **Resource Efficiency**: Fewer failed batches lead to less wasted API quota.
