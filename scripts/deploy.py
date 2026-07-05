"""Deploy the stack and run a post-deploy health check.

Runs ``cdk deploy``, reads the stack outputs, then makes an authenticated request
for a non-existent analysis and confirms the API answers 404 — proof the service
is live end to end. Requires real AWS credentials.

Usage::

    uv run python scripts/deploy.py
"""

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

import boto3

_OUTPUTS_FILE = Path("cdk.out/deploy-outputs.json")
_STACK = "LexAgentStack"


def _deploy() -> dict[str, str]:
    subprocess.run(
        ["cdk", "deploy", "--require-approval", "never", "--outputs-file", str(_OUTPUTS_FILE)],
        check=True,
    )
    outputs: dict[str, str] = json.loads(_OUTPUTS_FILE.read_text(encoding="utf-8"))[_STACK]
    return outputs


def _api_key(secret_arn: str) -> str:
    client = boto3.client("secretsmanager")
    value: str = client.get_secret_value(SecretId=secret_arn)["SecretString"]
    return value


def _health_check(api_url: str, api_key: str) -> bool:
    request = urllib.request.Request(
        f"{api_url}/analyses/nonexistent-thread-id", headers={"x-api-key": api_key}
    )
    try:
        urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as exc:
        return bool(exc.code == 404)
    return False


def main() -> int:
    outputs = _deploy()
    api_url = outputs["ApiUrl"]
    print(f"API URL:      {api_url}")
    print(f"Bucket:       {outputs['BucketName']}")
    print(f"DB secret:    {outputs['DbSecretArn']}")
    print(f"API key ARN:  {outputs['ApiKeySecretArn']}")

    api_key = _api_key(outputs["ApiKeySecretArn"])
    if _health_check(api_url, api_key):
        print("Health check passed: the API answered 404 for an unknown analysis.")
        return 0
    print("Health check failed: unexpected response for an unknown analysis.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
