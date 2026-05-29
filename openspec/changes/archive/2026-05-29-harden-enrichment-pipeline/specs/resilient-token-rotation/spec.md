## ADDED Requirements

### Requirement: Real-time rate limit tracking
The system SHALL monitor the `X-RateLimit-Remaining` header for every API request to track the health of each supplied GitHub token.

#### Scenario: Proactive rotation
- **WHEN** a token's remaining quota falls below a safety threshold (e.g., 10)
- **THEN** the system automatically switches to the next available token in the `GH_TOKENS` list for subsequent requests

### Requirement: Smart request retries
The system SHALL automatically retry requests that fail with gateway errors (502, 503, 504) or protocol errors (`ChunkedEncodingError`).

#### Scenario: Exponential backoff
- **WHEN** a request fails with a 502 Bad Gateway
- **THEN** the system waits for an increasing amount of time before re-attempting the request

## MODIFIED Requirements

### Requirement: Batch processing
The system SHALL use GraphQL aliases to fetch multiple users in a single request. The default batch size SHALL be 10 to minimize the risk of server-side timeouts.

#### Scenario: Successful batch fetch
- **WHEN** fetching data for 10 users
- **THEN** the system constructs and executes a single GraphQL query and processes the result without timing out
