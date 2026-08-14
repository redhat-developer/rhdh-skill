# Lifecycle Sources

URLs and extraction guidance for each platform and integration. Load this file during Step 4 of the workflow.

## Platforms

### OCP (OpenShift Container Platform)

**URL:** <https://access.redhat.com/support/policy/updates/openshift>
**What to extract:** Minor version GA dates and end-of-life dates from the life cycle policy table.

### OSD (OpenShift Dedicated)

**URL:** <https://access.redhat.com/product-life-cycles/api/v1/products/?name=Red+Hat+OpenShift+Container+Platform>
**What to extract:** OSD follows OCP version availability. Use OCP GA and EOL dates as a proxy — versions available on OSD typically lag OCP GA by a few weeks. Apply the same add/remove rules as OCP.

**Note:** The OSD-specific lifecycle page (`docs.openshift.com/dedicated`) returns 403 for automated access. The Red Hat lifecycle API has no OSD-specific entry beyond 4.13. OCP lifecycle data is the best available proxy.

### ROSA (Red Hat OpenShift Service on AWS)

**URL:** <https://access.redhat.com/product-life-cycles/api/v1/products/?name=Red+Hat+OpenShift+Container+Platform>
**What to extract:** ROSA follows OCP version availability. Use OCP GA and EOL dates as a proxy. Apply the same add/remove rules as OCP.

**Note:** The ROSA-specific lifecycle page (`docs.openshift.com/rosa`) returns 403 for automated access. The Red Hat lifecycle API has ROSA entries only up to 4.13 (classic architecture). OCP lifecycle data is the best available proxy for current versions.

### ARO (Azure Red Hat OpenShift)

**URL:** <https://learn.microsoft.com/en-us/azure/openshift/support-lifecycle>
**What to extract:** Kubernetes version GA dates and end of support (EOL) dates.

### AKS (Azure Kubernetes Service)

**URL:** <https://learn.microsoft.com/en-us/azure/aks/supported-kubernetes-versions?tabs=azure-cli#aks-kubernetes-release-calendar>
**What to extract:** The AKS Kubernetes release calendar table — GA date and end of life date per minor Kubernetes version.

### EKS (Amazon Elastic Kubernetes Service)

**URL:** <https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html>
**What to extract:** Kubernetes minor version release dates and end of standard support dates for EKS.

### GKE (Google Kubernetes Engine)

**URL:** <https://cloud.google.com/kubernetes-engine/docs/release-schedule>
**What to extract:** GKE release schedule table — GA date and end of life per minor Kubernetes version.

## Integrations

### RHDH PostgreSQL Support Policy (baseline)

**URL:** <https://access.redhat.com/support/policy/updates/developerhub>
**What to extract:** The list of PostgreSQL major versions officially supported by RHDH. This is the **authoritative baseline** — these versions are already confirmed for RHDH support. Use these as the starting point; do not suggest removing versions that are on this list unless they are also EOL across all three providers.

### Backstage PostgreSQL Support Policy (candidate source)

**URL:** <https://backstage.io/docs/overview/versioning-policy/#postgresql-releases>
**What to extract:** The PostgreSQL versions Backstage currently supports (rolling window, typically last 5 major versions). Any version Backstage supports but that is NOT on the RHDH support policy page is a **candidate to suggest adding**, with the following mandatory warning:

> ⚠ Adding a new PostgreSQL version to RHDH requires a dedicated RHDH Jira Feature ticket to formally extend database support. Do not add this version without one.

### Amazon RDS for PostgreSQL

**URL:** <https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-versions.html>
**What to extract:** PostgreSQL major version end of support (EOL) dates on Amazon RDS.

### Azure Database for PostgreSQL

**URL:** <https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-supported-versions>
**What to extract:** PostgreSQL major version support status and end of support dates for Azure Database Flexible Server.

### CloudSQL for PostgreSQL

**URL:** <https://cloud.google.com/sql/postgresql>
**What to extract:** PostgreSQL major version end of support dates for Google CloudSQL. The page may list supported versions in a table or prose — look for "end of support" or "EOL" next to each major version.

### RHBK (Red Hat Build of Keycloak)

**URL:** <https://access.redhat.com/product-life-cycles/api/v1/products/?name=Red+Hat+build+of+Keycloak>
**What to extract:** JSON response — each version entry has a `name` and a `phases` array. Extract dates from the phases array — **not** from a top-level `ga_date` field (there is none).

Phase extraction rules:

- **GA date**: `phases[name == "General availability"].end_date` — this is when the GA phase ended (i.e., when the product became GA). The `start_date` of this phase is always `"N/A"`.
- **EOL date**: the `end_date` of the last phase that has a real date (not `"N/A"`). Typically the last of: Maintenance support, Extended update support Term 2, etc.

Use minor version entries (e.g., `26.0`, `26.2`, `26.4`) to determine which **major versions** are still active — do not list minor versions in the table. A major version is active if at least one of its minor releases is GA on or before `code_freeze` and not EOL before `ga_date`. Report only the major version number (e.g., `26`).

### Quay (Red Hat Quay)

**URL:** <https://access.redhat.com/product-life-cycles/api/v1/products/?name=Red+Hat+Quay>
**What to extract:** JSON response — each version entry has a `name` and a `phases` array. Extract dates from the phases array — **not** from a top-level `ga_date` field (there is none).

Phase extraction rules:

- **GA date**: `phases[name == "General availability"].end_date` — this is when the GA phase ended (i.e., when the product became generally available). The `start_date` of this phase is always `"N/A"`.
- **EOL date**: the `end_date` of the last phase that has a real date (not `"N/A"`).

Identify only the **latest version** with a GA date on or before `code_freeze`. Suggest replacing the current version with that latest version.

## Date Interpretation Rules

When evaluating lifecycle dates against RHDH milestones:

| Rule | Condition | Action |
|------|-----------|--------|
| Add version | Version GA date ≤ RHDH Code Freeze | Suggest adding |
| Remove version | Version EOL date ≤ RHDH GA date | Suggest removing |
| No change | Version in table, not EOL, GA already passed | Leave as-is |
| No change | Version GA date > RHDH Code Freeze | Do not add |

If a lifecycle page provides only a quarter or year (not a precise date), use the **last day of that period** as a conservative estimate and note it in the justification (e.g., "GA estimated end of Q3 2025 → 2025-09-30").
