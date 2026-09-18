# Deployment guide — PBIP Sales sample to Microsoft Fabric

This document describes how to configure Azure AD, Microsoft Fabric, and
GitHub so that the `deploy-fabric.yml` workflow can publish the
`workspace/Sales.SemanticModel` and `workspace/Sales.Report` items to a real
Fabric workspace. **No Azure or Fabric resources are deployed as part of
building this repository** — the steps below are prerequisites an operator
performs once, outside of this repo, before the first real deployment.

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Microsoft Fabric tenant with Fabric enabled | The tenant admin must have turned on Fabric (or Power BI Premium/Fabric capacity) for the organization. |
| A Fabric workspace | Create an empty workspace and note its **Workspace ID** (Workspace settings → "About" → the GUID in the URL, `.../groups/<workspace-id>/...`). This repository never creates workspaces. |
| Fabric capacity assigned to the workspace | The workspace must be on a Fabric (or Premium) capacity; a "Pro" workspace cannot host Fabric items such as semantic models deployed via the Fabric REST API. |
| Azure subscription (for the app registration only) | Not billed for Fabric usage — only used to host the Entra ID app registration and its federated credential. |
| Owner/Contributor access to the target Fabric workspace | Whichever identity ends up deploying (the Entra app's service principal) must be added to the workspace as at least **Contributor**. |

## 2. Create an Entra ID (Azure AD) app registration

1. Azure Portal → **Microsoft Entra ID** → **App registrations** → **New registration**.
   - Name: e.g. `pbip-fabric-cicd-demo`.
   - Supported account types: single tenant (default) is sufficient.
   - No redirect URI needed.
2. Note the **Application (client) ID** and **Directory (tenant) ID** from the app's Overview page.
3. This app registration does **not** need a client secret — authentication
   to GitHub Actions uses **OIDC federated credentials** (no stored secrets).

### 2.1 Add a federated credential for GitHub OIDC

In the app registration → **Certificates & secrets** → **Federated credentials** → **Add credential**:

- Scenario: **GitHub Actions deploying Azure resources**.
- Organization: your GitHub org/user (e.g. `enekazo`).
- Repository: `PbiCIDEDemo2`.
- Entity type: **Environment**.
- Environment name: `production` (must match the `environment:` used in `deploy-fabric.yml`).
- Name: e.g. `pbip-fabric-cicd-demo-production`.

This lets GitHub Actions runs against the `production` environment mint a
short-lived OIDC token that Entra ID exchanges for an Azure AD access token
— no client secret is ever generated or stored in GitHub.

> If you also want to run PR-time or branch-based validation with Azure
> credentials in the future, add a second federated credential scoped to
> `pull_request` or a specific branch. The current `pr-validation.yml`
> workflow does **not** use Azure credentials at all — it only performs
> local/offline checks — so this is optional.

## 3. Grant the app access to the Fabric workspace

1. Open the target Fabric workspace → **Manage access**.
2. Add the app registration's **service principal** (search by its
   Application ID or display name) with the **Contributor** role.
3. Confirm the tenant setting **"Service principals can use Fabric APIs"**
   is enabled (Fabric Admin portal → Tenant settings → Developer settings).
   Without this, the service principal's REST API calls are rejected even
   with correct workspace permissions.

## 4. Configure the GitHub repository

### 4.1 Create the `production` environment

Repository → **Settings** → **Environments** → **New environment** → name
it `production` (must match `environment: production` in
`.github/workflows/deploy-fabric.yml`).

Add **required reviewers** so that a human must approve every run of the
deploy workflow before it executes — this is the manual gate referenced in
the project constraints; there is no automatic deployment on push/merge.

### 4.2 Environment variables (not secrets — no client secret exists)

Add these as **Environment variables** (Settings → Environments →
`production` → *Environment variables*, not *Secrets*, since there is no
secret value — OIDC federation replaces the client secret):

| Variable | Value |
|---|---|
| `AZURE_CLIENT_ID` | Application (client) ID from step 2 |
| `AZURE_TENANT_ID` | Directory (tenant) ID from step 2 |
| `AZURE_SUBSCRIPTION_ID` | The Azure subscription ID that hosts the app registration (any subscription the identity can see — Fabric billing is independent of this) |
| `FABRIC_WORKSPACE_ID` | GUID of the target Fabric workspace from step 1 |
| `FABRIC_ENVIRONMENT` | *(optional)* logical environment name forwarded to `fabric-cicd`'s `parameter.yml` resolution — leave unset unless you add a `parameter.yml` to `workspace/` |

None of these values are secret in the traditional sense (they are IDs, not
credentials), which is why OIDC federation is used instead of a stored
client secret.

## 5. Running the deployment workflow

The `deploy-fabric.yml` workflow is **manual only** (`workflow_dispatch`)
and requires typing `deploy` into the confirmation input, in addition to
environment reviewer approval:

1. Actions tab → **Deploy to Fabric** → **Run workflow**.
2. Enter `deploy` in the confirmation field.
3. Approve the run when prompted (required reviewer gate).
4. The workflow re-validates `workspace/` structurally, authenticates via
   OIDC, publishes `SemanticModel` then `Report` via `fabric-cicd`, and
   finally calls the Fabric REST API to confirm both items exist.

No push, merge, or schedule triggers this workflow — every production
deployment is a deliberate, reviewed, manual action.

## 6. Local operation (development / manual runs)

### 6.1 Python version

`fabric-cicd` requires **Python ≥3.9, <3.14**. If your default Python is
3.14 or newer (as of late 2025 this is the case on newly provisioned
Windows machines), install a compatible version, e.g. with the Python
launcher:

```powershell
py install 3.12
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 6.2 Install dependencies

```powershell
pip install -r requirements-dev.txt   # includes requirements.txt + pytest/ruff
```

### 6.3 Offline validation (no Azure credentials needed)

```powershell
python scripts/validate_pbip.py
python -m pytest tests/ -v
python -m ruff check scripts tests
```

### 6.4 Manual deployment (requires `az login`)

```powershell
az login
az account set --subscription <AZURE_SUBSCRIPTION_ID>

$env:FABRIC_WORKSPACE_ID = "<your-workspace-guid>"
python scripts/deploy_to_fabric.py
python scripts/validate_deployment.py
```

`deploy_to_fabric.py` uses `AzureCliCredential`, so it authenticates as
whatever identity `az login` is currently signed in as — this must be an
identity (user or the service principal, via `az login --service-principal`)
with Contributor access to the target workspace.

### 6.5 Destructive option: deleting orphaned Fabric items

By default, `deploy_to_fabric.py` only **publishes** items — it never
deletes anything from the workspace. Setting
`FABRIC_ENABLE_UNPUBLISH_ORPHANS=true` additionally deletes any Fabric item
in the workspace that is not present in `workspace/`. This is **destructive
and irreversible**; leave it unset (default `false`) unless you specifically
intend the Fabric workspace to be a byte-for-byte mirror of `workspace/`.

## 7. Troubleshooting

### 7.1 `AADSTS700213: No matching federated identity record found`

The `subject` claim GitHub Actions presents in its OIDC token does not
always match the plain `repo:<owner>/<repo>:environment:<name>` format
shown in most examples. Some GitHub organizations (for example, those using
Enterprise Managed Users) present numeric suffixes appended to the owner
and/or repository name instead, e.g.:

```
repo:<owner>@<owner-numeric-id>/<repo>@<repo-numeric-id>:environment:production
```

If the federated credential's **Subject** was configured with the plain
form (or a stale numeric id), Azure AD rejects the token exchange with
`AADSTS700213`, and `azure/login` fails with `Login failed... 'az' failed
with exit code 1`. Fix: check the exact subject GitHub sent (it's printed
in the failed run's error message) and update the federated credential to
match it exactly:

```bash
az ad app federated-credential update \
  --id <AZURE_CLIENT_ID> \
  --federated-credential-id <credential-id> \
  --parameters '{"subject":"<subject string from the error message>"}'
```

### 7.2 `No subscriptions found for ***`

`fabric-cicd` only needs an Azure AD access token for the Fabric REST API
(`https://api.fabric.microsoft.com/.default`) — it never calls Azure
Resource Manager, so the service principal does **not** need any role
assignment on `AZURE_SUBSCRIPTION_ID`. However, `azure/login` by default
also tries to select a subscription context after signing in, and fails
with `No subscriptions found for ***` if the service principal has zero
subscription-scoped role assignments. The `deploy-fabric.yml` workflow sets
`allow-no-subscriptions: true` on the login step to avoid this — if you
copy this workflow elsewhere, keep that flag rather than granting the
service principal an unnecessary subscription role.

## 8. Data refresh

This repository does not configure a data source credential or a refresh
schedule for the semantic model. After a real deployment, an operator must
configure the semantic model's data source credentials in the Fabric portal
(Workspace → semantic model → Settings → Data source credentials) before
any scheduled or on-demand refresh will succeed. No refresh is triggered by
any workflow in this repository.
