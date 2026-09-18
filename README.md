# PBIP → Microsoft Fabric CI/CD demo

A local, commit-ready GitHub Actions CI/CD demonstration that validates and
deploys the official Microsoft PBIP **Sales** sample to a Microsoft Fabric
workspace using [`fabric-cicd`](https://microsoft.github.io/fabric-cicd/).

## Objective

Show a minimal, safe, review-gated path from a Power BI Project (`.pbip`)
checked into source control to a published Fabric semantic model + report,
with:

- **Pull-request validation** — structural checks and unit tests, no Azure
  credentials required, safe to run on every PR.
- **Manual, reviewed production deployment** — a `workflow_dispatch`-only
  workflow gated behind a GitHub Environment with required reviewers.
- **No secrets** — authentication uses GitHub OIDC (`azure/login`) exchanged
  for an Azure AD token via `AzureCliCredential`; no client secret is ever
  stored in the repository.

## Architecture

```
workspace/                      ← fabric-cicd "repository directory" (Fabric items only)
  Sales.pbip
  Sales.Report/                 ← Power BI report definition
  Sales.SemanticModel/          ← Power BI semantic model definition (TMDL)

scripts/
  fabric_items.py               ← shared constants (paths, item types, expected items)
  validate_pbip.py              ← offline structural validation (no Azure creds)
  deploy_to_fabric.py           ← publishes SemanticModel then Report via fabric-cicd
  validate_deployment.py        ← post-deploy check via Fabric REST API

tests/                          ← pytest unit tests for the two scripts above

.github/workflows/
  pr-validation.yml             ← PR trigger: ruff, pytest, validate_pbip.py
  deploy-fabric.yml             ← workflow_dispatch, protected `production` environment

docs/DEPLOYMENT.md              ← Azure AD app registration, Fabric prerequisites,
                                   environment variables, local operation
```

Publishing order is always **SemanticModel before Report**, since the
report's `definition.pbir` references the semantic model by path.

## Prerequisites

- Python **3.9–3.13** (`fabric-cicd` does not yet support 3.14+). This repo
  was developed and tested against Python 3.12.
- For local structural validation and unit tests: no Azure account needed.
- For an actual deployment: an Azure AD app registration with a Fabric
  workspace OIDC federated credential, and a Fabric workspace on Fabric
  capacity — see [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) for full
  setup instructions.

## Quick start (local validation only)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

python scripts/validate_pbip.py     # structural validation of workspace/
python -m pytest tests/ -v          # unit tests
python -m ruff check scripts tests  # lint
```

No Azure credentials, secrets, or network calls to Fabric are required for
any of the above — everything runs entirely offline against the files in
`workspace/`.

## Deploying to Fabric

Deployment is intentionally **manual and reviewed**:

1. Configure Azure AD, Fabric, and the GitHub `production` environment —
   see [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md).
2. Trigger **Actions → Deploy to Fabric → Run workflow**, typing `deploy`
   to confirm.
3. A required reviewer approves the run against the `production`
   environment.
4. The workflow re-validates `workspace/`, authenticates via OIDC, and
   publishes `SemanticModel` then `Report` via `fabric-cicd`, then verifies
   both items exist in the workspace via the Fabric REST API.

No push, merge, or schedule triggers a deployment. See
[`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md) § "Data refresh" for why a
data-source credential must be configured manually in the Fabric portal
before any refresh will succeed.

## 🙏 Built On + Thanks

This project is a CI/CD wrapper around Microsoft's own official sample —
no original Power BI content is included.

- **PBIP Sales sample** — imported verbatim from
  [`microsoft/Analysis-Services`](https://github.com/microsoft/Analysis-Services)
  at commit [`e87bb60c`](https://github.com/microsoft/Analysis-Services/tree/e87bb60cd8fd3c979841c01f71b8175e461d6e26/pbidevmode/fabricps-pbip/SamplePBIP)
  (`pbidevmode/fabricps-pbip/SamplePBIP`), MIT licensed, Copyright (c) 2016
  Microsoft. See [`NOTICE.md`](./NOTICE.md) and
  [`THIRD-PARTY-NOTICES-UPSTREAM-LICENSE.txt`](./THIRD-PARTY-NOTICES-UPSTREAM-LICENSE.txt)
  for the full attribution and license text.
- **[`fabric-cicd`](https://github.com/microsoft/fabric-cicd)** — the
  official Microsoft Python library used for all Fabric item publish/
  unpublish operations in `scripts/deploy_to_fabric.py`.
- **[`azure-identity`](https://github.com/Azure/azure-sdk-for-python)** —
  provides `AzureCliCredential`, used both locally and via `azure/login`
  OIDC in GitHub Actions.

## Constraints honored by this repository

- No Azure or Fabric resources are created or deployed by building/testing
  this repository.
- No GitHub push, pull request, issue, or comment is created by building
  this repository.
- Production deployment is always manual (`workflow_dispatch`) and gated by
  a GitHub Environment with required reviewers.
- No data refresh occurs until data-source credentials are configured
  manually in the Fabric portal, per `docs/DEPLOYMENT.md`.
