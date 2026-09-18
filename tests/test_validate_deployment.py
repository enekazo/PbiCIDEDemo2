"""Unit tests for the pure matching logic in scripts/validate_deployment.py.

Network/auth calls are intentionally not exercised here -- this module
never talks to Azure or Fabric in CI.
"""

from __future__ import annotations

from fabric_items import EXPECTED_ITEMS
from validate_deployment import find_missing_items


def test_find_missing_items_returns_empty_when_all_present() -> None:
    items = [
        {"displayName": "Sales", "type": "SemanticModel"},
        {"displayName": "Sales", "type": "Report"},
        {"displayName": "SomethingElse", "type": "Report"},
    ]

    assert find_missing_items(items, EXPECTED_ITEMS) == []


def test_find_missing_items_flags_absent_item() -> None:
    items = [{"displayName": "Sales", "type": "SemanticModel"}]

    missing = find_missing_items(items, EXPECTED_ITEMS)

    assert missing == [{"name": "Sales", "type": "Report", "folder": "Sales.Report"}]


def test_find_missing_items_flags_everything_when_workspace_empty() -> None:
    missing = find_missing_items([], EXPECTED_ITEMS)

    assert {(m["name"], m["type"]) for m in missing} == {
        ("Sales", "SemanticModel"),
        ("Sales", "Report"),
    }
