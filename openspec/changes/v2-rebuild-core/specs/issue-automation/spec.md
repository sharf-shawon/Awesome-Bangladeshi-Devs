## ADDED Requirements

### Requirement: Process developer addition requests
The system SHALL process GitHub issues labeled `add-developer` by extracting the username and location, verifying eligibility, and appending the developer to `data/users.json`.

#### Scenario: Valid addition request
- **WHEN** an issue with `add-developer` label is processed and the user is eligible
- **THEN** the system appends the user to `users.json` and comments on the issue

#### Scenario: Blocked user request
- **WHEN** the requested username is found in `data/removed_users.json`
- **THEN** the system rejects the addition and comments that the user is blocked

#### Scenario: Invalid location
- **WHEN** the location in the issue body does not match any allowed Bangladeshi city aliases
- **THEN** the system rejects the addition with an `INVALID_LOCATION` status

### Requirement: Process developer removal requests
The system SHALL process GitHub issues labeled `remove-developer` by moving the user from `data/users.json` to `data/removed_users.json`.

#### Scenario: Self-removal request
- **WHEN** a user checks the self-removal checkbox in the issue
- **THEN** the system moves their entry to `removed_users.json` and closes the issue
