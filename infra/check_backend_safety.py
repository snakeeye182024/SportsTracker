#!/usr/bin/env python3
"""Conservative offline guard for the existing Sports Tracker v2 SAM template.

This is not a CloudFormation change-set diff or an authorization proof.
"""
from pathlib import Path
import re
import sys

source = Path("backend/template.yaml").read_text()
built_path = Path(".aws-sam/build/template.yaml")
if not built_path.is_file():
    sys.exit("FAIL: run sam build before safety review")
built = built_path.read_text()

required = {
    "DataTable": "AWS::DynamoDB::Table",
    "UserPool": "AWS::Cognito::UserPool",
    "UserPoolClient": "AWS::Cognito::UserPoolClient",
    "HttpApi": "AWS::Serverless::HttpApi",
    "ApiFunction": "AWS::Serverless::Function",
}
for logical_id, resource_type in required.items():
    pattern = rf"(?m)^  {re.escape(logical_id)}:\s*\n    Type: {re.escape(resource_type)}\s*$"
    if not re.search(pattern, source):
        sys.exit(f"FAIL: expected resource {logical_id} of type {resource_type} not found")

for marker in (
    "DeletionPolicy: Retain",
    "UpdateReplacePolicy: Retain",
    "PointInTimeRecoveryEnabled: true",
    "DefaultAuthorizer: CognitoJwt",
    "Authorizer: NONE",
    "Runtime: python3.12",
    "CodeUri: ./",
):
    if marker not in source:
        sys.exit(f"FAIL: required safeguard missing: {marker}")

for path, method in (
    ("/v1/health", "GET"),
    ("/v1/leagues", "GET"),
    ("/v1/leagues", "POST"),
    ("/v1/leagues/{leagueId}", "GET"),
    ("/v1/leagues/{leagueId}/teams", "GET"),
    ("/v1/leagues/{leagueId}/teams", "POST"),
    ("/v1/leagues/{leagueId}/teams/{teamId}/players", "GET"),
    ("/v1/leagues/{leagueId}/teams/{teamId}/players", "POST"),
):
    if f"Path: {path}\n" not in source or f"Method: {method}\n" not in source:
        sys.exit(f"FAIL: expected route field missing: {method} {path}")

if "AWS::Serverless::Function" not in built:
    sys.exit("FAIL: built SAM template missing function resource")

print("PASS: conservative template guard. This does not prove a safe CloudFormation diff.")
