# TokenCleanUpCLI

Bash CLI to find and remove unused LaunchDarkly access tokens.

LaunchDarkly does not provide a built-in unused-token report. This tool uses the [Access Tokens API](https://launchdarkly.com/docs/api/access-tokens):

- [List access tokens](https://launchdarkly.com/docs/api/access-tokens/get-tokens) — reads `lastUsed`
- [Delete access token](https://launchdarkly.com/docs/api/access-tokens/delete-token) — removes selected tokens

## `lastUsed` semantics

| Value | Meaning |
|-------|---------|
| `0` | Never used |
| `> 0` | Unix timestamp (milliseconds) of last use |

## Requirements

- `bash`
- `curl`
- `jq`

## Auth

Pass an API access token with `-k` / `--api-key`, or set `LD_API_KEY`.

Use an **Admin** token (or custom role with token-management actions) so `showAll=true` can return personal tokens for all members. Invalid keys surface HTTP status plus LaunchDarkly `code` / `message` (e.g. 401 unauthorized).

Optional: `LD_API_BASE` (default `https://app.launchdarkly.com`; federal: `https://app.launchdarkly.us`).

## Usage

```bash
chmod +x token_cleanup.sh

# List tokens never used or unused 90+ days (default)
./token_cleanup.sh list -k "$LD_API_KEY"

# Custom inactivity window
./token_cleanup.sh list -k "$LD_API_KEY" --days 180

# Never-used only
./token_cleanup.sh list -k "$LD_API_KEY" --never-used

# Personal tokens only
./token_cleanup.sh list -k "$LD_API_KEY" --personal-only -o report.json

# Delete by ID
./token_cleanup.sh remove -k "$LD_API_KEY" --id TOKEN_ID --yes

# Delete all matching the same filters as list (prompts unless --yes)
./token_cleanup.sh remove -k "$LD_API_KEY" --days 90 --yes
```

### Commands

| Command | Behavior |
|---------|----------|
| `list` | Read-only. Prints a table and writes a JSON report. |
| `remove` | Deletes by `--id` (repeatable), or all tokens matching list filters. |

### Safety

- `list` never mutates.
- `remove` asks for confirmation unless `--yes`.
- Skips deleting a token whose reported last-4 matches the API key in use (best-effort).

## Error examples

```
Error: HTTP 401 — unauthorized: Invalid access token
  Hint: Invalid or missing API key (unauthorized).

Error: HTTP 403 — forbidden: ...
  Hint: Forbidden — key likely lacks Admin / token-management permission.
```
