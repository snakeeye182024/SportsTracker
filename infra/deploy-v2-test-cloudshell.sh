#!/usr/bin/env bash
# Deploy a NEW, isolated Sports Tracker 2.0 test stack from the feature branch.
# Does not touch the production sports-tracker or sports-tracker-v2 stacks.
set -euo pipefail
REGION="us-east-2"
ACCOUNT="814650855040"
STACK="sports-tracker-v2-test"
BRANCH="feature/v2-live-scoring-foundation"
EXPECTED_ORIGIN="https://snakeeye182024.github.io"
REPO="https://github.com/snakeeye182024/SportsTracker.git"

for tool in aws git sam python3; do
  command -v "$tool" >/dev/null || { echo "Missing $tool"; exit 1; }
done
ACTUAL_ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
[[ "$ACTUAL_ACCOUNT" == "$ACCOUNT" ]] || { echo "STOP: Wrong AWS account"; exit 1; }
[[ "$(aws configure get region || true)" == "$REGION" ]] || echo "Using explicit AWS region $REGION"

# Refuse to update an existing stack. Any later updates require a separate review.
if aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" >/dev/null 2>&1; then
  echo "STOP: Test stack already exists. Review its resources before making changes."
  exit 1
fi
WORKDIR="$(mktemp -d)"
trap 'echo "Review checkout retained at: $WORKDIR"' EXIT
git clone --depth 1 --branch "$BRANCH" "$REPO" "$WORKDIR/repo"
cd "$WORKDIR/repo"
python3 -m unittest discover -s backend/tests -v
sam validate --template-file backend/template.yaml --lint
sam build --template-file backend/template.yaml
echo
echo "About to CREATE isolated stack $STACK in account $ACCOUNT, region $REGION."
echo "This creates TEST DynamoDB, Cognito, Lambda, API Gateway, and Lambda IAM role."
echo "It does not attach policies to the production CloudFormation service role."
read -r -p "Type CREATE-TEST-STACK to proceed: " CONFIRM
[[ "$CONFIRM" == "CREATE-TEST-STACK" ]] || { echo "Cancelled"; exit 1; }
sam deploy \
  --template-file .aws-sam/build/template.yaml \
  --stack-name "$STACK" \
  --region "$REGION" \
  --resolve-s3 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides "AllowedOrigin=$EXPECTED_ORIGIN" \
  --no-confirm-changeset \
  --no-fail-on-empty-changeset
aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query 'Stacks[0].{Status:StackStatus,Outputs:Outputs,RoleARN:RoleARN}' --output json
echo "Test backend deployed. The browser test page is NOT published yet."
echo "Keep the output IDs separate from production IDs."
