# AWS GitHub change-set preview (no execution)

This PR is a **preview-only** workflow. The existing backend template and Lambda source are now in `backend/` on `main`. The SAM template has been validated and built in CloudShell, and its eight routes match the live API's methods, paths, and authorization choices. This does not establish code equivalence or guarantee a safe deployment.

## AWS configuration

- Account: `814650855040`; region: `us-east-2`; stack: `sports-tracker-v2`.
- GitHub OIDC role: `SportsTrackerGitHubDeploy`. Its trust subject is the account-specific custom claim shown in `infra/github-oidc-trust-policy.json` (confirmed by the OIDC verification workflow).
- CloudFormation execution role: `SportsTrackerCloudFormationExecution`. **Neither role is yet authorized for deployment until its reviewed IAM policies are attached and tested.**
- Repository Actions variable: `AWS_DEPLOY_ROLE_ARN=arn:aws:iam::814650855040:role/SportsTrackerGitHubDeploy`.
- The `production` GitHub environment must be configured with required reviewers, prevent self-review where supported, and limit deployment branches to `main`. **Verify actual approval enforcement**; merely naming an environment does not require review.

## Preview procedure

1. Review and merge this PR **only after reviewing the workflow**; merging does not trigger deployment.
2. Review IAM policies and attach only permissions required for change-set creation and narrowly scoped CloudFormation updates. Do not grant `cloudformation:ExecuteChangeSet` to the GitHub preview role.
3. From GitHub Actions, manually run **AWS backend change-set preparation (no execution)** on `main` and type `PREVIEW`.
4. Identify the new change-set ID in the output. Use `aws cloudformation describe-change-set` to inspect the exact resources and details. Only `ApiFunction` and `HttpApi` modifications without replacement are expected for the initial release. If anything else appears, stop.
5. **Do not execute** the change set until there is a separate approved execution workflow, IAM permissions, and a rollback plan. An approval in this preview workflow is not permission to deploy.

## Safety notes

- The workflow uses `--no-execute-changeset`. There is **no execute step**.
- The existing production stack policy denies CloudFormation updates to `DataTable`, `UserPool`, and `UserPoolClient`; it does not prevent direct changes or stack deletion.
- `SportsTrackerGitHubDeploy` must not have `cloudformation:ExecuteChangeSet` or stack deletion permissions.
- The preview may associate a CloudFormation service role with the existing stack via `--role-arn`; this association can persist and affects future stack operations. Review this explicitly before running.
- The GitHub environment approval settings are not yet verified.
- The older pending change set `samcli-deploy1795021746` is not approved for execution.
- Leave the Sports Tracker 1.0 stack and `index.html` unchanged.
