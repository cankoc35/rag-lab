# Atlas maintenance policy

- Source ID: LOCAL-MAINTENANCE
- Document version: 1.0
- Document state: atlas-expanded-v1
- Reference date: 2026-11-23
- Data classification: Synthetic; windows, approvals and workload rules are authored local policy.

## Scope and maintenance window

This policy applies to the fictional Atlas PostgreSQL 18 environment in
**LOCAL-INVENTORY**. The routine maintenance window is **Sunday, 02:00–03:00
UTC**, beginning at 02:00 and ending before 03:00. Planned work must finish
within the window or stop under its approved change plan. These times do
not describe an observed maintenance event.

`atlas_maintenance_operator` performs approved maintenance on
`atlas-primary-01`. The schema owner approves the change ticket; the operator
must verify the required privileges separately. Ordinary application and
reporting identities do not acquire maintenance authority from this document.

Before planned maintenance, obtain a successful backup record no older than
24 hours with a passed archive-integrity check, and a successful restore-drill
record no older than seven days. Their timestamps are assessed at the planned
start. **LOCAL-BACKUP** defines the relevant records. Missing records block
approval until verified; a schedule does not satisfy this prerequisite.

## VACUUM and statistics work

Autovacuum is intended to remain enabled. Confirm the actual setting and
matching table statistics before diagnosing a maintenance problem. Manual
`VACUUM (ANALYZE)` is the approved routine action when a documented need for
cleanup or updated planner statistics exists. Execute it outside an explicit
transaction block and within the approved window.

Routine cleanup aims to make space reusable and keep statistics current.
Do not infer exact reclaimed operating-system bytes, new cardinalities or a
performance improvement without measurements. Consult PostgreSQL's vacuuming
documentation for the behavior and concurrency of each command variant.

`VACUUM FULL` is not part of routine maintenance. It requires a separate
outage plan, approval from both the schema owner and on-call lead, a reviewed
locking impact and a verified capacity assessment. The routine window alone
does not authorize it. Index creation, deletion and other DDL also require
their own approved change; catalog reference SQL is not an execution request.

## Query inspection

Only these query IDs are in the document inspection allowlist:

| Query ID | Source of exact SQL |
| --- | --- |
| Q-ATLAS-CUSTOMER-LOOKUP | LOCAL-QUERY-CATALOG |
| Q-ATLAS-DEVICE-RANGE | LOCAL-QUERY-CATALOG |
| Q-ATLAS-UNBILLED | LOCAL-QUERY-CATALOG |

For initial plan inspection, record the query ID, exact SQL, parameter values,
document state, target identity and PostgreSQL version. Request plain
`EXPLAIN (FORMAT JSON)` for that SELECT. Do not change a query's predicate to
make an index appear usable. An actual inspection implementation is not
provided by this document.

`EXPLAIN ANALYZE` requires separate benchmark approval, an agreed workload
and measurement procedure. Its execution behavior is different from plain
EXPLAIN. Keep estimated costs distinct from observed duration; the existing
documents contain no plan output or exact index-speedup measurement.

## Transaction and retry profiles

| Workload | Intended transaction profile |
| --- | --- |
| Routine single-statement reporting | Read-only, Read Committed |
| Multi-statement reporting export requiring one consistent view | Read-only, Repeatable Read |
| Application order creation | Serializable on the primary |

The reporting profiles belong to `atlas_report_reader`; order creation belongs
to `atlas_app_writer`, as defined in **LOCAL-ACCESS**. These are local workload
requirements, not a claim that every active connection has the stated setting.
The order-creation operation is not one of the three read-only catalog queries.

On SQLSTATE **40001** during the Serializable order-creation transaction,
roll back and retry the **entire transaction**, including its reads and
decisions. Allow at most **two retries after the initial attempt**, for three
attempts in total. If the limit is exhausted, return a failure and record the
incident; do not report a successful order. Other SQLSTATEs require their own
handling and are not automatically retried by this rule.

## Completion and evidence

Record ticket/approver identities, actual start/end times, commands or query
IDs, relevant observation references and outcomes. If a prerequisite or an
operation fails, stop and escalate to the schema owner and on-call lead.
This corpus contains no completed change tickets, active-transaction records,
current autovacuum settings or maintenance outcomes. It cannot establish
current readiness or a causal diagnosis of a slow query.
