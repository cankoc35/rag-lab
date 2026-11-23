# Atlas access policy

- Source ID: LOCAL-ACCESS
- Document version: 1.0
- Document state: atlas-expanded-v1
- Reference date: 2026-11-23
- Data classification: Synthetic; roles and approval procedures are invented local policy.

## Scope and intended roles

This policy defines intended responsibilities for database `atlas_telemetry`
and schema `atlas_app` in **LOCAL-INVENTORY**. The names below are logical
group-role identifiers, not user accounts or connection credentials. No roles
or memberships were created by writing this policy. Actual grants, ownership
and connection settings require a matching database inspection.

| Role | Intended responsibility | Approved target and boundary |
| --- | --- | --- |
| atlas_app_writer | SELECT, INSERT, UPDATE and DELETE for application work | Primary; no schema changes, maintenance or backup administration |
| atlas_report_reader | SELECT on the five named inventory tables for reporting | Reporting replica; read-only sessions, no primary write access |
| atlas_maintenance_operator | Approved routine maintenance and query inspection | Primary, within LOCAL-MAINTENANCE approvals; no independent DDL approval |
| atlas_backup_operator | Run the approved database dump, manage retained archives and coordinate verification | Primary as dump source and approved archive repository; no application writes or primary restore |
| atlas_schema_owner | Intended owner of application schema/objects and approver for controlled DDL | Primary; ownership does not remove change approvals |

The reporting table scope is `atlas_app.device_events`, `atlas_app.orders`,
`atlas_app.devices`, `atlas_app.customers` and `atlas_app.ingest_batches`.
Do not infer access to every one of the 120 application tables from that list.
The backup job instead requires database-wide read coverage for its declared
dump scope, subject to separately verified permissions.

Role responsibilities are not exhaustive PostgreSQL GRANT statements.
Availability of a role name does not establish membership, login capability,
engine privileges or permission to bypass row-level controls. This document
does not define production authentication settings or certify enforcement.

## Access requests and expiry

An access request must record the requester, task, requested role, database,
target identity, ticket ID and requested start/end times. The schema owner
approves application and reporting access. Temporary maintenance or backup
access additionally needs the on-call lead's approval; both approvals are
required before the access begins.

Temporary maintenance and backup memberships expire after **four hours**
or at the approved task end, whichever comes first. A longer task requires
a new approval, not an automatic extension. Standing service memberships
are reviewed every **30 calendar days** by the schema owner. These are review
and expiry requirements, not evidence that any current membership is valid.

## Separation of duties

Application writers and report readers cannot authorize DDL, replica promotion
or restore operations under this policy. The maintenance operator performs
approved work but cannot approve its own outage. **LOCAL-MAINTENANCE** requires
both the schema owner and on-call lead for a VACUUM FULL outage.

The backup operator can verify and supply an archive to the isolated restore
procedure in **LOCAL-BACKUP**. The schema owner approves the restore target and
the identity with the required restore privileges. Being the backup operator
does not itself grant permission to overwrite a running environment.

No role described here has automatic superuser or standby-promotion authority.
Those privileges and any emergency promotion procedure are outside this
document's authorization scope.

## Review and evidence

Record the approver identities, approved scope, expiry, granted membership
reference and eventual revocation in the access record. At expiry or task
completion, revoke temporary access and preserve that record. If inspection
finds a grant outside the approved scope, escalate to the schema owner and
on-call lead for review.

The corpus supplies no live role catalog, membership list, access ticket or
grant/revocation history. It supports questions about intended policy, not
claims about the privileges of a particular current session. Workload isolation
and retry requirements are defined separately in **LOCAL-MAINTENANCE**.
