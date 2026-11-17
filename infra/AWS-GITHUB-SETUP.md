# AWS deployment from GitHub Actions

## Current status

This pull request provides the **deployment pipeline and OIDC trust policy**, not an active deployment. The current AWS SAM template and Lambda source are not in this repository. **Do not dispatch the workflow** until the existing `sports-tracker-v2` stack has been reconciled with a reviewed `backend/template.yaml` and source files. A mismatched template can delete or replace existing resources. Sports Tracker 1.0 must remain untouched.

## One-time AWS setup (account 814650855040, region us-east-2)

1. In AWS IAM > Identity providers, add OpenID Connect provider `https://token.actions.githubusercontent.com` with audience `sts.amazonaws.com`, if it does not already exist.
2. Create an IAM role named `SportsTrackerGitHubDeploy` with the trust policy in `infra/github-oidc-trust-policy.json`. The role trust is limited to the repository's GitHub `production` environment; no long-lived AWS keys are needed.
3. Attach a **reviewed least-privilege deployment policy** covering the existing SAM stack, CloudFormation change sets, approved Lambda/API Gateway/DynamoDB/Cognito/SES operations as needed, S3 artifact uploads, and `iam:PassRole` only for approved execution roles. Do **not** attach AdministratorAccess. The required policy depends on the existing CloudFormation template and cannot be safely finalized until that template is available.
4. In GitHub repository > Settings > Environments, create `production`. Set **Required reviewers** (choose a trusted reviewer), disable self-review if supported, and restrict deployment branches to `main`. GitHub environment protection availability varies by repository visibility and plan. **Verify a run waits for approval** before trusting this workflow for production.
5. In GitHub repository > Settings > Secrets and variables > Actions > Variables, create `AWS_DEPLOY_ROLE_ARN` with value `arn:aws:iam::814650855040:role/SportsTrackerGitHubDeploy`. This is an ARN, not a secret. If you prefer, scope the variable to the `production` environment instead.
6. Recover the deployed stack's original SAM template and Lambda code, add them under `backend/`, review a CloudFormation change set and drift before allowing the workflow to deploy to the existing `sports-tracker-v2` stack. Avoid generating a new SAM template from scratch and overwriting existing resources.
7. Merge a reviewed backend pull request. In GitHub > Actions > **AWS backend deployment (approval required)** > Run workflow, choose `main`, enter `DEPLOY`, then have an authorized reviewer approve the `production` environment deployment.

## Guardrails

- Pull requests run only validation, never AWS deployment.
- Production deployment is manual, requires the exact confirmation `DEPLOY`, uses `main`, and is gated by the GitHub `production` environment.
- OIDC credentials are short-lived and scoped by repository and environment.
- `environment: production` does **not** by itself enforce approval: you must configure and test Required reviewers in GitHub.
- The deployment job intentionally fails validation until `backend/template.yaml` exists.
- Once configured, GitHub Actions manages backend deployment. Runtime manager invitations still require implemented APIs, storage, permissions, and email delivery.
