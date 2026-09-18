# NOTICE

This repository includes third-party material redistributed under its
original license, per Microsoft's attribution requirements.

## Power BI Project (PBIP) "Sales" sample

- **Upstream repository:** https://github.com/microsoft/Analysis-Services
- **Upstream path:** `pbidevmode/fabricps-pbip/SamplePBIP`
- **Pinned commit:** `e87bb60cd8fd3c979841c01f71b8175e461d6e26`
- **License:** MIT License
- **Copyright:** Copyright (c) 2016 Microsoft
- **License text:** see [`THIRD-PARTY-NOTICES-UPSTREAM-LICENSE.txt`](./THIRD-PARTY-NOTICES-UPSTREAM-LICENSE.txt) (verbatim copy of the upstream `LICENSE` file at the pinned commit)
- **Location in this repository:** [`workspace/Sales.pbip`](./workspace/Sales.pbip), [`workspace/Sales.Report/`](./workspace/Sales.Report/), [`workspace/Sales.SemanticModel/`](./workspace/Sales.SemanticModel/)
- **Consumer:** All Python tooling in [`scripts/`](./scripts/) and the GitHub Actions workflows in [`.github/workflows/`](./.github/workflows/) treat this folder as the Fabric-cicd "repository directory" to validate and deploy.
- **Modifications:** None to the PBIP content itself. The sample was relocated from the repository root into a dedicated `workspace/` subfolder so that the fabric-cicd sync directory contains only Fabric item definitions, per [fabric-cicd's directory-structure guidance](https://microsoft.github.io/fabric-cicd/latest/how_to/getting_started/#directory-structure). No `.pbip`/`.Report`/`.SemanticModel` file content was altered.
- **Sync rule:** This is a point-in-time import pinned to the commit above. To refresh, re-download the same path from a newer upstream commit, update the pinned SHA in this file and in `README.md`, and re-run `python scripts/validate_pbip.py` plus the test suite before committing.

## Third-party Python packages

This repository's Python tooling depends on third-party packages declared
in [`requirements.txt`](./requirements.txt) and
[`requirements-dev.txt`](./requirements-dev.txt) (notably `fabric-cicd`,
`azure-identity`, `requests`, `pytest`, and `ruff`). These are installed
from PyPI at build/test time and are not vendored into this repository;
each package's own license applies and can be reviewed at its respective
PyPI project page.
