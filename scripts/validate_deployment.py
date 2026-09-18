#!/usr/bin/env python3
"""Post-deployment verification against the live Fabric workspace.

Calls the Fabric REST API directly (rather than re-using fabric-cicd
internals) to list items in the target workspace and assert that the
Sales semantic model and report were actually published. This is the
final step of the protected ``deploy-fabric.yml`` workflow, run after
``deploy_to_fabric.py``.

Required environment variables
-------------------------------
FABRIC_WORKSPACE_ID
    GUID of the workspace to inspect.

Authentication
---------------
Uses ``azure.identity.AzureCliCredential`` against the
``https://api.fabric.microsoft.com/.default`` scope -- the same identity
``deploy_to_fabric.py`` used to publish the items.
"""

from __future__ import annotations

import os
import sys

import requests
from azure.identity import AzureCliCredential
from fabric_items import EXPECTED_ITEMS

FABRIC_API_BASE = "https://api.fabric.microsoft.com/v1"
FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"


def _get_access_token() -> str:
    credential = AzureCliCredential()
    token = credential.get_token(FABRIC_SCOPE)
    return token.token


def _list_workspace_items(workspace_id: str, access_token: str) -> list[dict]:
    items: list[dict] = []
    url = f"{FABRIC_API_BASE}/workspaces/{workspace_id}/items"
    headers = {"Authorization": f"Bearer {access_token}"}

    while url:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        items.extend(payload.get("value", []))
        continuation = payload.get("continuationUri")
        url = continuation if continuation else None

    return items


def find_missing_items(items: list[dict], expected: list[dict]) -> list[dict]:
    """Return the subset of ``expected`` items not present in ``items``.

    ``items`` is the raw Fabric REST API item list (each with
    ``displayName``/``type``); ``expected`` is ``fabric_items.EXPECTED_ITEMS``.
    Pulled out as a pure function so the matching logic is unit-testable
    without a live Fabric workspace or network access.
    """
    found_by_key = {(item.get("displayName"), item.get("type")) for item in items}
    return [
        item
        for item in expected
        if (item["name"], item["type"]) not in found_by_key
    ]


def main() -> int:
    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    if not workspace_id:
        print(
            "ERROR: FABRIC_WORKSPACE_ID environment variable is required and was not set.",
            file=sys.stderr,
        )
        return 1

    print(f"Verifying deployed items in Fabric workspace {workspace_id}...")

    try:
        access_token = _get_access_token()
        items = _list_workspace_items(workspace_id, access_token)
    except Exception as exc:  # noqa: BLE001 - surface any auth/HTTP failure clearly
        print(f"ERROR: failed to query the Fabric REST API: {exc}", file=sys.stderr)
        return 1

    missing = find_missing_items(items, EXPECTED_ITEMS)

    if missing:
        print("ERROR: expected Fabric items were not found in the workspace:", file=sys.stderr)
        for item in missing:
            print(f"  - {item['name']} ({item['type']})", file=sys.stderr)
        present = sorted((item.get("displayName"), item.get("type")) for item in items)
        print(f"Items actually present: {present}", file=sys.stderr)
        return 1

    print("Deployment verification passed. Found expected items:")
    for expected in EXPECTED_ITEMS:
        print(f"  - {expected['name']} ({expected['type']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
