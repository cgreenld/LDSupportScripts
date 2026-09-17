# Bulk Flag Approval Workflow — Planning Document

## Problem Statement

1. **Prerequisite flags ≠ approval bypass**: Feature flags dependent on a prerequisite "master" flag should not default to TRUE when the prerequisite is off. Prerequisite flags are meant as a master switch, not a workaround for the approval process.

2. **Change management alignment**: Each feature is tied to a Jira issue; production enablement requires CAB approval of the underlying Jira issue. Enabling a flag in production should still require approval regardless of prerequisite structure.

3. **Operational pain**: Enabling 15 flags = 15 toggles = 15 approvals. Bulk operations can reduce manual work while preserving the approval workflow.

---

## Proposed Workflow: Three Phases

| Phase | Purpose | API Token Scope |
|-------|---------|-----------------|
| **1. List input** | Enumerate flags to be changed | Read-only (flags, environments) |
| **2. Approval requests created** | Create approval requests for each flag | `createApprovalRequest` |
| **3. Approval requests applied** | Apply approved requests after CAB sign-off | `applyApprovalRequest` |

This separation supports **least privilege**: different tokens can be used for create vs. apply, and apply can be restricted to post-CAB execution.

---

## Phase 1: List Input

**Input sources (examples):**
- Text file: one flag key per line
- CSV with columns: `flag_key`, optional `jira_key`, `environment`
- Filter: flags with a specific tag (e.g. `march-release`)
- Explicit list from CLI args

**Output:**
- Validated list of `(projectKey, flagKey, environmentKey)` tuples
- Optional: current state (on/off) per flag for confirmation

**APIs used:**
- `GET /api/v2/flags/{projectKey}` — list flags (with `filter` for tags)
- `GET /api/v2/flags/{projectKey}/{flagKey}` — get flag details/status

**Token scope:** `reader` or custom role with `getFeatureFlag`, `listFeatureFlags`

---

## Phase 2: Approval Requests Created

**Input:** List from Phase 1 + optional `notifyMemberIds` (reviewers)

**Process:**
For each flag in the list:
1. Build `resourceId`: `proj/{projectKey}:env/{environmentKey}:flag/{flagKey}`
2. Build `instructions` for the desired change (e.g. turn flag ON)
3. `POST /api/v2/approval-requests` with:
   - `resourceId`
   - `description` (e.g. "Enable flag X in production — Jira PROJ-123")
   - `instructions` (see below)
   - `notifyMemberIds` (optional)

**Output:**
- List of approval request IDs (`_id` from each response)
- Persist to file (e.g. `approval_request_ids.json`) for Phase 3

**API:** `POST https://app.launchdarkly.com/api/v2/approval-requests`

**Token scope:** Custom role with `createApprovalRequest` (and read for validation). No `applyApprovalRequest` needed here.

**Instruction format for "turn flag ON":**  
LaunchDarkly uses instruction objects. For environment targeting changes, the instruction `kind` is typically `updateEnvironment` or similar. Exact schema should be confirmed against [Approvals API docs](https://launchdarkly.com/docs/api/approvals). The segment example in `csv2LDsegment/prod_csv_to_segment.sh` uses `addValuesToClause` / `removeValuesToClause`; flag instructions will differ (environment-level `on` toggle).

---

## Phase 3: Approval Requests Applied

**Input:** List of approval request IDs (from Phase 2 output file or manual input)

**Process:**
For each approval request ID:
1. Optionally verify status is `approved` (if list endpoint available)
2. `POST /api/v2/approval-requests/{approvalRequestId}/apply` (or equivalent apply endpoint for flags)

**Output:**
- Success/failure per request
- Summary report

**Token scope:** Custom role with `applyApprovalRequest` only. This can be a separate token used only after CAB approval.

---

## API Reference Summary

| Operation | Endpoint | Method |
|-----------|----------|--------|
| List flags | `/flags/{projectKey}` | GET |
| Get flag | `/flags/{projectKey}/{flagKey}` | GET |
| Create approval request | `/approval-requests` | POST |
| List approvals for flag | `/flags/{projectKey}/{flagKey}/approval-requests` | GET |
| Apply approval request | `/approval-requests/{id}/apply` (flag-specific path per docs) | POST |

Exact paths should be verified in [LaunchDarkly Approvals API](https://launchdarkly.com/docs/api/approvals).

---

## Least Privilege Token Strategy

| Token | Use case | Actions |
|-------|-----------|---------|
| **List/Create token** | Phase 1 + 2 (automation/requester) | `getFeatureFlag`, `listFeatureFlags`, `createApprovalRequest` |
| **Apply token** | Phase 3 (post-CAB executor) | `applyApprovalRequest`, `getApprovalRequest` (if needed) |

Alternatively:
- Single token with create + apply (simpler, less separation)
- Apply-only token held by CAB/release manager; create token used by automation

---

## Script Structure Proposal

```
BulkChanges/
├── PLAN.md                 # This document
├── approvalRequest.py      # Main entry point (or split into modules)
├── config.py               # Project key, env, API token (from env var)
├── list_flags.py           # Phase 1: list/validate input
├── create_approvals.py     # Phase 2: create approval requests
├── apply_approvals.py      # Phase 3: apply approved requests
├── .env.example            # LD_API_TOKEN, LD_PROJECT_KEY, etc.
└── requirements.txt       # requests (or reuse DevCycle2LD venv)
```

**CLI usage (conceptual):**
```bash
# Phase 1: List flags from file
python -m BulkChanges.list_flags --input flags.txt --project default --env production

# Phase 2: Create approval requests
python -m BulkChanges.create_approvals --input flags.txt --project default --env production --output approval_ids.json

# Phase 3: Apply (after CAB approval)
python -m BulkChanges.apply_approvals --input approval_ids.json
```

---

## Open Questions / Next Steps

1. **Instruction schema for "turn ON"**: Confirm exact `instructions` structure for flag environment `on` toggle via [Create approval request](https://launchdarkly.com/docs/api/approvals/post-approval-request) docs or API explorer.
2. **Batch vs. one-per-flag**: LaunchDarkly appears to use one approval request per resource. Confirming whether a single request can include multiple flags.
3. **Jira linkage**: Optional enhancement — include Jira key in `description` for traceability; no LaunchDarkly API change required.
4. **Dry-run**: Add `--dry-run` to create/apply phases to log intended actions without calling the API.

---

## References

- [LaunchDarkly Feature Flags API](https://launchdarkly.com/docs/api/feature-flags)
- [LaunchDarkly Approvals API](https://launchdarkly.com/docs/api/approvals)
- [Requesting approvals](https://launchdarkly.com/docs/home/releases/approval-requests)
- Existing pattern: `csv2LDsegment/prod_csv_to_segment.sh` (approval request for segment changes)
