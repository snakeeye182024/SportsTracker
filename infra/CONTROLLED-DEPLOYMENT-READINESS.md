# Sports Tracker 2.0 — controlled deployment readiness (review only)

> **STOP: This document authorizes no AWS action.** This PR must not assume AWS credentials, attach IAM policies, create/execute a change set, or update production. Keep the offline-only workflow in `.github/workflows/aws-deploy.yml` unchanged.

## Scope and protected boundaries

- Account `814650855040`, region `us-east-2`, stack `sports-tracker-v2`.
- Only intended deployable resources: existing Lambda `sports-tracker-v2-ApiFunction-Edm4e76HAYIf` and HTTP API `qtmj4qlqfb`.
- **Never touch** Sports Tracker 1.0 stack `sports-tracker`, its DynamoDB table `SportsTracker`, or root `index.html`.
- Protect 2.0 DynamoDB logical ID `DataTable`, Cognito `UserPool` and `UserPoolClient`; current stack policy denies updates to these three logical IDs. This does **not** prevent direct service changes or stack deletion.
- Do not execute old change set `samcli-deploy1795021746`. It is historical evidence, not deployment authorization.

## Evidence reviewed (2026-11-18)

- Offline SAM validation, Python backend tests, SAM build and source safety review: green after PR #13.
- Current Lambda: `python3.12`, `app.handler`, 10-second timeout, 256 MB, successful last update; role `sports-tracker-v2-ApiFunctionRole-Rs1WrbFAh2VF`.
- Existing change set: `CREATE_COMPLETE`, `AVAILABLE`, **unexecuted**. `ApiFunction.Code` static modify without replacement; `HttpApi.Body` dynamic modify due to `ApiFunction.Arn` without replacement. No DynamoDB or Cognito modifications listed.
- Live API baseline exported to CloudShell `sports-tracker-v2-api-baseline.json` (local only, not committed). Eight routes verified: public `GET /v1/health`; seven league/team/player operations require Cognito JWT. Audience `6g3a1jmmupiog72v26imo4hve6`; issuer `https://cognito-idp.us-east-2.amazonaws.com/us-east-2_TEYlWvVwP`.
- Existing stack `RoleARN: null`. `SportsTrackerCloudFormationExecution` has no inline or attached managed policies; **leave it unattached and unassociated** pending a separate decision.
- GitHub OIDC role `SportsTrackerGitHubDeploy` has preview-oriented permissions but no `cloudformation:ExecuteChangeSet` or `DeleteStack`. The current GitHub workflow requests no AWS credentials. GitHub production-environment reviewer/branch restrictions remain unverified.

## IAM policy review — unresolved, do not attach

`infra/cloudformation-execution-policy.DRAFT.json` permits Lambda read/update, HTTP API GET/PATCH/PUT and read/pass of the existing Lambda execution role. It does **not** permit DynamoDB or Cognito modifications. It is not yet a complete, tested CloudFormation service policy. Review CloudFormation/SAM transformed dependencies (Lambda permissions, API default stage, generated IAM role), CloudFormation rollback needs, S3/KMS artifact access and exact API Gateway resource ARN coverage. Do not broadly add `iam:*`, `lambda:*`, `apigateway:*`, `cloudformation:*`, or wildcard resource access to work around errors.

**Important persistence risk:** passing a CloudFormation service role during an update can associate it with the stack for subsequent updates. Separately approve whether to use a service role at all. Never add `--role-arn` to an unattended workflow as a trial.

## Required gates before any future deployment (separate approval)

1. **Approval architecture:** verify GitHub `production` required reviewers, prevent self-review where supported, and restrict deployment to protected `main`. Require a distinct, deliberate approval to execute; PR approval alone is not production approval.
2. **Baseline and rollback:** capture live Lambda version/configuration, current API export and integrations, stack events/outputs and an appropriate rollback plan. Confirm backups/PITR and avoid changing protected data resources. Store sensitive snapshots securely, not in Git.
3. **Diff verification:** compare the proposed **packaged/transformed** template against the deployed template and exported API, including routes, method-specific authorization, issuer, audience, CORS, integrations, Lambda env/role/runtime. A `Body` modification can change API behavior even without replacement.
4. **Least privilege:** complete and independently review IAM simulation **with `aws:RequestedRegion=us-east-2`**, including potential CloudFormation rollback operations; check whether service role persistence is acceptable. No IAM attachment in this PR.
5. **Fresh preview:** only after explicit authorization, create a **new** non-executing change set using a reviewed process. Confirm its stack, region, resource IDs, properties, replacement flags, and changes; reject changes to `DataTable`, `UserPool`, `UserPoolClient`, or unrelated resources. Creation of a preview may upload artifacts and interact with AWS, so requires its own authorization.
6. **Execution gate:** execution must remain disabled in GitHub's preview role. A separately authorized human-controlled execution path, rollback plan, and post-deployment health/auth regression checks must be documented before execution.

## Current safe operator action

Continue using the existing offline GitHub Actions workflow: manually dispatch `AWS backend offline validation (no deployment)` on `main` with confirmation `PREVIEW`. This runs local validation/build/safety checks on GitHub-hosted runners and does not request AWS credentials.

## Explicit exclusions from PR #14

No workflow changes; no AWS credential use; no IAM attachments or trust updates; no change-set creation, execution, or deletion; no stack updates; no changes to backend code, SAM template, 1.0 app, 2.0 frontend, or database.
