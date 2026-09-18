"""Shared constants describing the Fabric items in this repository.

Keeping these in one place means the PR-time structural validation script
and the deployment script agree on what "the Sales sample" is expected to
look like, without duplicating literals.
"""

from __future__ import annotations

from pathlib import Path

#: Directory (relative to the repo root) that fabric-cicd treats as the
#: Fabric Git-integration sync folder. It must contain *only* Fabric item
#: definitions (plus an optional parameter.yml) -- see
#: https://microsoft.github.io/fabric-cicd/latest/how_to/getting_started/#directory-structure
REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_DIRECTORY = REPO_ROOT / "workspace"

#: Fabric item types this repository deploys, in a safe publish order.
#: fabric-cicd resolves cross-item dependencies internally, but semantic
#: models are listed first for clarity since the report depends on it.
ITEM_TYPES_IN_SCOPE = ["SemanticModel", "Report"]

#: The item name shared by both the semantic model and the report, e.g.
#: "Sales.SemanticModel" and "Sales.Report".
ITEM_BASE_NAME = "Sales"

EXPECTED_ITEMS = [
    {"name": ITEM_BASE_NAME, "type": "SemanticModel", "folder": f"{ITEM_BASE_NAME}.SemanticModel"},
    {"name": ITEM_BASE_NAME, "type": "Report", "folder": f"{ITEM_BASE_NAME}.Report"},
]
