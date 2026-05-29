## ADDED Requirements

### Requirement: Validate users.json integrity
The system SHALL validate the `data/users.json` file to ensure all entries have a valid `github_username`, a matching `profile_url`, and no duplicate usernames.

#### Scenario: Valid users.json
- **WHEN** the validation script is run on a correctly formatted `users.json`
- **THEN** the script exits with code 0

#### Scenario: Missing username
- **WHEN** an entry in `users.json` is missing the `github_username` field
- **THEN** the script exits with code 1 and logs the problematic entry

#### Scenario: Duplicate username
- **WHEN** multiple entries in `users.json` share the same `github_username`
- **THEN** the script exits with code 1 and identifies the duplicate

#### Scenario: Invalid profile URL
- **WHEN** the `profile_url` does not match `https://github.com/{github_username}`
- **THEN** the script exits with code 1 and identifies the mismatch
