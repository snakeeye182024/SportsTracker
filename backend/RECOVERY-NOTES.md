# Sports Tracker 2.0 — recovered backend baseline

The deployed AWS Lambda function is `sports-tracker-v2-ApiFunction-Edm4e76HAYIf` in `us-east-2` (stack `sports-tracker-v2`).

The uploaded Lambda ZIP contained only `app.py` (6,344 bytes). The original CloudFormation/SAM template has also been recovered from the deployed stack.

## Current backend behavior

- Python 3.12 Lambda, handler `app.handler`.
- Public `GET /v1/health`; Cognito JWT required for league, team, and player endpoints.
- `GET/POST /v1/leagues`, `GET /v1/leagues/{leagueId}`.
- `GET/POST /v1/leagues/{leagueId}/teams`.
- `GET/POST /v1/leagues/{leagueId}/teams/{teamId}/players`.
- DynamoDB single-table keys `PK` and `SK`.
- League authorization is **owner-only**, based on JWT `sub` matching `ownerSub`.
- No invitation, role assignment, or email sending endpoints are implemented yet.

## Safety gates before deployment

1. Import the *exact* reviewed Lambda source from the recovered ZIP into `backend/app.py`; preserve its behavior.
2. Reconcile the original stack template with the deployed CloudFormation stack and source package. The exported template's `CodeUri` points to a previously uploaded S3 object, **not** a checked-in source directory.
3. Add tests for existing league/team/player behavior and authorization before implementing invitations.
4. Review a CloudFormation change set and drift; do not replace the existing DynamoDB table, Cognito pool/client, or HTTP API.
5. Review least-privilege IAM deployment permissions. The successful OIDC identity test alone does not establish deployment permissions.
6. Do not merge/run PR #6's deployment workflow until all above gates are complete.

This documentation PR is **non-deploying** and does not change the live application.
