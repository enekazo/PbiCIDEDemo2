"""Unit tests for scripts/validate_pbip.py.

These tests build minimal, synthetic PBIP-shaped fixtures on disk (via
pytest's ``tmp_path``) rather than depending on the real ``workspace/``
sample, so they exercise both the happy path and specific failure modes
in isolation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from validate_pbip import validate

REPO_ROOT = Path(__file__).resolve().parent.parent


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _build_valid_workspace(root: Path) -> Path:
    """Create a minimal, structurally-valid workspace/ fixture."""
    workspace = root / "workspace"

    _write_json(
        workspace / "Sales.pbip",
        {
            "version": "1.0",
            "artifacts": [{"report": {"path": "Sales.Report"}}],
        },
    )

    report_dir = workspace / "Sales.Report"
    _write_json(report_dir / ".platform", {"metadata": {"type": "Report"}})
    _write_json(
        report_dir / "definition.pbir",
        {"datasetReference": {"byPath": {"path": "../Sales.SemanticModel"}}},
    )
    (report_dir / "report.json").write_text("{}", encoding="utf-8")

    model_dir = workspace / "Sales.SemanticModel"
    _write_json(model_dir / ".platform", {"metadata": {"type": "SemanticModel"}})
    _write_json(model_dir / "definition.pbism", {"version": "1.0"})

    definition_dir = model_dir / "definition"
    for name in ("database.tmdl", "model.tmdl", "relationships.tmdl"):
        (definition_dir / name).parent.mkdir(parents=True, exist_ok=True)
        (definition_dir / name).write_text("// tmdl\n", encoding="utf-8")
    tables_dir = definition_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    (tables_dir / "Sales.tmdl").write_text("table Sales\n", encoding="utf-8")

    return workspace


def test_validate_passes_on_well_formed_workspace(tmp_path: Path) -> None:
    workspace = _build_valid_workspace(tmp_path)

    result = validate(workspace)

    assert result.ok, result.errors


def test_validate_fails_on_missing_workspace(tmp_path: Path) -> None:
    result = validate(tmp_path / "does-not-exist")

    assert not result.ok
    assert any("does not exist" in e for e in result.errors)


def test_validate_fails_on_invalid_json(tmp_path: Path) -> None:
    workspace = _build_valid_workspace(tmp_path)
    (workspace / "Sales.Report" / "report.json").write_text("{not valid json", encoding="utf-8")

    result = validate(workspace)

    assert not result.ok
    assert any("Invalid JSON" in e for e in result.errors)


def test_validate_fails_on_wrong_platform_type(tmp_path: Path) -> None:
    workspace = _build_valid_workspace(tmp_path)
    _write_json(workspace / "Sales.Report" / ".platform", {"metadata": {"type": "SemanticModel"}})

    result = validate(workspace)

    assert not result.ok
    assert any("metadata.type" in e for e in result.errors)


def test_validate_fails_on_missing_tmdl_table(tmp_path: Path) -> None:
    workspace = _build_valid_workspace(tmp_path)
    tables_dir = workspace / "Sales.SemanticModel" / "definition" / "tables"
    for f in tables_dir.glob("*.tmdl"):
        f.unlink()

    result = validate(workspace)

    assert not result.ok
    assert any("No .tmdl table definitions" in e for e in result.errors)


def test_validate_fails_on_mismatched_dataset_reference(tmp_path: Path) -> None:
    workspace = _build_valid_workspace(tmp_path)
    _write_json(
        workspace / "Sales.Report" / "definition.pbir",
        {"datasetReference": {"byPath": {"path": "../SomeOtherModel"}}},
    )

    result = validate(workspace)

    assert not result.ok
    assert any("datasetReference.byPath" in e for e in result.errors)


@pytest.mark.parametrize(
    "relative_path",
    [
        "Sales.pbip",
        "Sales.Report/.platform",
        "Sales.Report/definition.pbir",
        "Sales.Report/report.json",
        "Sales.SemanticModel/.platform",
        "Sales.SemanticModel/definition.pbism",
        "Sales.SemanticModel/definition/database.tmdl",
        "Sales.SemanticModel/definition/model.tmdl",
        "Sales.SemanticModel/definition/relationships.tmdl",
    ],
)
def test_real_workspace_has_expected_files(relative_path: str) -> None:
    """Guard against accidental deletion/renaming of the imported sample."""
    assert (REPO_ROOT / "workspace" / relative_path).exists()


def test_real_workspace_passes_validation() -> None:
    """The actual imported Sales sample must pass structural validation."""
    result = validate(REPO_ROOT / "workspace")

    assert result.ok, result.errors
