#!/usr/bin/env python3
"""Publish the Sales sample (SemanticModel + Report) to a Fabric workspace.

This is the only script in the repository that talks to Azure/Fabric. It
is invoked exclusively by the protected ``deploy-fabric.yml`` workflow (or
manually by an operator who has already run ``az login``) -- it is never
run as part of pull-request validation.

Required environment variables
-------------------------------
FABRIC_WORKSPACE_ID
    GUID of the target Fabric workspace. Must already exist; this script
    never creates workspaces or capacities.

Optional environment variables
-------------------------------
FABRIC_ENVIRONMENT
    Logical environment name (e.g. ``production``) forwarded to
    ``FabricWorkspace`` for ``parameter.yml`` find/replace resolution.
    Unused unless a ``parameter.yml`` is added to ``workspace/``. Defaults
    to fabric-cicd's own default (``"N/A"``) when unset -- fabric-cicd
    requires a string here and rejects ``None``.
REPOSITORY_DIRECTORY
    Overrides the directory scanned for Fabric items. Defaults to the
    repository's ``workspace/`` folder.
FABRIC_ENABLE_UNPUBLISH_ORPHANS
    Set to ``true`` to additionally delete Fabric items that exist in the
    workspace but are no longer present in ``workspace/``. Defaults to
    ``false`` because this is a destructive, irreversible operation.

Authentication
---------------
Uses ``azure.identity.AzureCliCredential``, i.e. whatever identity the
Azure CLI is currently logged in as. In GitHub Actions this is populated
by the ``azure/login`` action using federated (OIDC) credentials -- no
client secret is ever stored. Locally, run ``az login`` first.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from azure.identity import AzureCliCredential
from fabric_cicd import FabricWorkspace, publish_all_items, unpublish_all_orphan_items
from fabric_items import ITEM_TYPES_IN_SCOPE, WORKSPACE_DIRECTORY


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    workspace_id = os.environ.get("FABRIC_WORKSPACE_ID", "").strip()
    if not workspace_id:
        print(
            "ERROR: FABRIC_WORKSPACE_ID environment variable is required and was not set.",
            file=sys.stderr,
        )
        return 1

    # fabric_cicd.FabricWorkspace.environment must be a string (default "N/A")
    # -- it performs a strict type check and rejects None.
    environment = os.environ.get("FABRIC_ENVIRONMENT", "").strip() or "N/A"
    repository_directory = Path(
        os.environ.get("REPOSITORY_DIRECTORY", "").strip() or WORKSPACE_DIRECTORY
    ).resolve()
    enable_unpublish_orphans = _env_flag("FABRIC_ENABLE_UNPUBLISH_ORPHANS", default=False)

    if not repository_directory.is_dir():
        print(
            f"ERROR: repository_directory does not exist: {repository_directory}",
            file=sys.stderr,
        )
        return 1

    print(f"Fabric workspace id:     {workspace_id}")
    print(f"Environment:             {environment}")
    print(f"Repository directory:    {repository_directory}")
    print(f"Item types in scope:     {ITEM_TYPES_IN_SCOPE}")
    print(f"Unpublish orphan items:  {enable_unpublish_orphans}")

    credential = AzureCliCredential()

    workspace = FabricWorkspace(
        workspace_id=workspace_id,
        environment=environment,
        repository_directory=str(repository_directory),
        item_type_in_scope=ITEM_TYPES_IN_SCOPE,
        token_credential=credential,
    )

    publish_all_items(workspace)

    if enable_unpublish_orphans:
        print("Unpublishing orphaned items (FABRIC_ENABLE_UNPUBLISH_ORPHANS=true)...")
        unpublish_all_orphan_items(workspace)

    print("Deployment to Fabric completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
