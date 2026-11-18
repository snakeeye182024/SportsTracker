# Sports Tracker 2.0: offline validation and deployment design

**No production deployment is authorized by this PR.** The AWS workflow validates the SAM template and Python tests on pull requests. Its optional manual `PREVIEW` job now performs **only an offline SAM build and conservative source checks**; it does not assume an AWS role, create a change set, or modify a stack.

## Verified environment

- AWS application account: `814650855040`; region: `us-east-2`; stack: `sports-tracker-v2` (`CREATE_COMPLETE`).
- Current stack service role: `RoleARN: null`.
- GitHub OIDC role: `SportsTrackerGitHubDeploy`; its region-aware IAM simulation allows `CreateChangeSet` and `DescribeChangeSet`, and implicitly denies `ExecuteChangeSet` and `DeleteStack`. This simulation does **not** prove an end-to-end deployment.
- GitHub environment `production` required reviewers and deployment-branch rules have **not been verified**.
- The AWS Organizations region SCP permits `us-east-2`; the earlier explicit deny was due to missing `aws:RequestedRegion` simulation context.
- A dedicated `SportsTrackerCloudFormationExecution` role exists with CloudFormation trust, **no policies attached**, and **no association with the stack**.

## Review-only execution-role policy

`infra/cloudformation-execution-policy.DRAFT.json` scopes potential future permissions to the current Lambda function, API Gateway and existing Lambda role. **Do not attach it yet.** The SAM transform includes Lambda permissions, an API Gateway stage, and a generated IAM role, and the draft has not been verified to cover all CloudFormation actions or a safe rollback.

Assigning a service role to an existing CloudFormation stack can persist across future updates. Do not add `--role-arn` to a change-set preview without separately reviewing that persistent effect.

## How to run safe offline checks

- On PRs: GitHub Actions runs `sam validate --template-file backend/template.yaml --lint` and `python -m unittest discover -s backend/tests -v`.
- After merging a reviewed workflow, a manual dispatch on `main` with confirmation `PREVIEW` runs `sam build --template-file backend/template.yaml` and `python3 infra/check_backend_safety.py`. **No AWS credentials are requested**.
- The safety script is intentionally conservative. It checks selected template markers and route fields, not the actual deployed stack, generated CloudFormation semantics, or exact route-to-method pairings.

## Before enabling an AWS change-set preview

1. Review the SAM-transformed template and the full permissions required by CloudFormation, including generated Lambda permissions, API stage, IAM role, and any KMS/S3 dependencies.
2. Decide whether to associate a persistent CloudFormation service role with the production stack. Explicitly approve that decision and document recovery and rollback.
3. Verify GitHub production-environment reviewers, self-review restriction and `main` branch restriction.
4. Review a fresh change set, confirm only intended non-replacement Lambda/API modifications, and compare live API authorization, CORS and routes.
5. Maintain separation of duties: GitHub preview role must **not** gain `ExecuteChangeSet` or `DeleteStack`.
6. Do not execute the existing change set `samcli-deploy1795021746`; create and review a fresh one after the deployment design is approved.

The existing CloudFormation stack policy denies updates to `DataTable`, `UserPool` and `UserPoolClient`, but does not protect against direct API changes or full stack deletion. Leave the Sports Tracker 1.0 stack and `index.html` untouched.
