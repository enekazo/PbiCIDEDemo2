#!/usr/bin/env python3
"""Offline structural validation for the PBIP source in ``workspace/``.

This script performs no network calls and requires no Azure credentials,
so it is safe to run on every pull request. It checks that the Power BI
Project (PBIP) files this repository ships are internally consistent and
match the shape fabric-cicd expects before any deployment is attempted:

* ``workspace/Sales.pbip`` points at the report folder.
* ``Sales.Report`` and ``Sales.SemanticModel`` each have a ``.platform``
  file with the correct ``metadata.type``.
* ``Sales.Report/definition.pbir`` references the semantic model folder.
* ``Sales.SemanticModel/definition.pbism`` exists and is valid JSON.
* The semantic model's TMDL definition folder contains the core files
  (``database.tmdl``, ``model.tmdl``, ``relationships.tmdl``) and at
  least one table definition.
* Every ``.json``/``.pbir``/``.pbism``/``.platform`` file in the workspace
  parses as valid JSON.

Usage::

    python scripts/validate_pbip.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

from fabric_items import WORKSPACE_DIRECTORY

# File extensions (including dotfiles like ``.platform``) that are expected
# to contain JSON and are therefore parsed and validated as such.
_JSON_LIKE_SUFFIXES = {".json", ".pbir", ".pbism", ".platform", ".pbip"}


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_json(path: Path, result: ValidationResult) -> dict | None:
    if not path.exists():
        result.errors.append(f"Missing required file: {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(f"Invalid JSON in {path}: {exc}")
        return None


def _validate_all_json_files(workspace_dir: Path, result: ValidationResult) -> None:
    """Parse every JSON-like file under the workspace to catch corruption."""
    for path in sorted(workspace_dir.rglob("*")):
        if path.is_file() and path.suffix.lower() in _JSON_LIKE_SUFFIXES:
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                result.errors.append(f"Invalid JSON in {path}: {exc}")
            except UnicodeDecodeError as exc:
                result.errors.append(f"Could not read {path} as UTF-8: {exc}")


def _validate_platform_file(path: Path, expected_type: str, result: ValidationResult) -> None:
    data = _load_json(path, result)
    if data is None:
        return
    actual_type = data.get("metadata", {}).get("type")
    if actual_type != expected_type:
        result.errors.append(
            f"{path}: expected metadata.type == '{expected_type}', got '{actual_type}'"
        )


def _validate_pbip_pointer(workspace_dir: Path, report_folder: str, result: ValidationResult) -> None:
    pbip_files = list(workspace_dir.glob("*.pbip"))
    if not pbip_files:
        result.errors.append(f"No .pbip file found in {workspace_dir}")
        return
    if len(pbip_files) > 1:
        result.warnings.append(
            f"Multiple .pbip files found in {workspace_dir}: {[p.name for p in pbip_files]}"
        )
    data = _load_json(pbip_files[0], result)
    if data is None:
        return
    artifacts = data.get("artifacts", [])
    report_paths = [a.get("report", {}).get("path") for a in artifacts if "report" in a]
    if report_folder not in report_paths:
        result.errors.append(
            f"{pbip_files[0]}: expected an artifact report.path == '{report_folder}', "
            f"found {report_paths}"
        )


def _validate_report_definition(report_dir: Path, semantic_model_folder: str, result: ValidationResult) -> None:
    pbir_path = report_dir / "definition.pbir"
    data = _load_json(pbir_path, result)
    if data is None:
        return
    dataset_ref = data.get("datasetReference", {})
    by_path = dataset_ref.get("byPath")
    by_connection = dataset_ref.get("byConnection")
    if by_path is None and by_connection is None:
        result.errors.append(
            f"{pbir_path}: datasetReference has neither byPath nor byConnection"
        )
        return
    if by_path is not None:
        ref_path = by_path.get("path", "")
        # byPath is relative to the report folder, e.g. "../Sales.SemanticModel".
        resolved = (report_dir / ref_path).resolve()
        if resolved.name != semantic_model_folder:
            result.errors.append(
                f"{pbir_path}: datasetReference.byPath ('{ref_path}') does not "
                f"resolve to '{semantic_model_folder}' (resolved: {resolved.name})"
            )
    if not (report_dir / "report.json").exists():
        result.errors.append(f"{report_dir}: missing report.json")


def _validate_semantic_model_definition(model_dir: Path, result: ValidationResult) -> None:
    pbism_path = model_dir / "definition.pbism"
    _load_json(pbism_path, result)

    definition_dir = model_dir / "definition"
    if not definition_dir.is_dir():
        result.errors.append(f"Missing TMDL definition folder: {definition_dir}")
        return

    required_tmdl = ["database.tmdl", "model.tmdl", "relationships.tmdl"]
    for name in required_tmdl:
        if not (definition_dir / name).exists():
            result.errors.append(f"Missing required TMDL file: {definition_dir / name}")

    tables_dir = definition_dir / "tables"
    if not tables_dir.is_dir():
        result.errors.append(f"Missing tables definition folder: {tables_dir}")
    else:
        table_files = list(tables_dir.glob("*.tmdl"))
        if not table_files:
            result.errors.append(f"No .tmdl table definitions found under {tables_dir}")


def validate(workspace_dir: Path = WORKSPACE_DIRECTORY) -> ValidationResult:
    result = ValidationResult()

    if not workspace_dir.is_dir():
        result.errors.append(f"Workspace directory does not exist: {workspace_dir}")
        return result

    report_dir = workspace_dir / "Sales.Report"
    model_dir = workspace_dir / "Sales.SemanticModel"

    _validate_pbip_pointer(workspace_dir, "Sales.Report", result)
    _validate_platform_file(report_dir / ".platform", "Report", result)
    _validate_platform_file(model_dir / ".platform", "SemanticModel", result)
    _validate_report_definition(report_dir, "Sales.SemanticModel", result)
    _validate_semantic_model_definition(model_dir, result)
    _validate_all_json_files(workspace_dir, result)

    return result


def main() -> int:
    result = validate()

    for warning in result.warnings:
        print(f"::warning::{warning}")

    if result.ok:
        print("PBIP structural validation passed: workspace/ is well-formed.")
        return 0

    print("PBIP structural validation FAILED:", file=sys.stderr)
    for error in result.errors:
        print(f"  - {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
